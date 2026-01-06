import yaml
import json
import time
import logging
import hashlib
import hmac
from pathlib import Path
from typing import Optional
import base64
from datetime import datetime
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
import os  # Added for os.chmod

# --- CRYPTO CONFIG ---
PUBLIC_KEY_PEM = """
-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA4CE9neZ+fuodKZ4570P1
IGjTpYBN4tVBxObmkCYju7qfbZ/ovWNRzbIeOXJ/YMNUla7iRU5RqGhYKPTmqMuL
jyD8om8f9w6FfRb4OI98/fm2Tgv/2lEHvKaFUUAT5ah6Ja4LOgnKtOVwjJ/4EjKH
AjpegBODF1TXThygEYkb7Kr8CEn/wNFYTtP5D3VE/1bRXdEpmsjexlBJqvK6R5wt
UAzY1i/hPqmtvx1Lf2HBJ0bk6mZisc82EkGp4kVi13+FqwCWieD4jU3ge3yty9NU
AgciI0brp/SlTVEDJ/oMEGseZ3N7gEJ+RB3GkyK1KazDC/09knqnzeLF6Ekijhxj
lwIDAQAB
-----END PUBLIC KEY-----
"""

logger = logging.getLogger("PrismConfig")

class Config:
    def __init__(self):
        self.config_path = Path.home() / ".prism" / "config.yaml"
        self.data_dir = Path.home() / ".prism"
        self.cache_path = self.data_dir / "license_cache.json" # This will be replaced by self.config_dir / "license.cache" in _load_license_cache
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # License cache (1 hour TTL)
        self._license_cache: Optional[dict] = None
        self._cache_ttl = 3600  # 1 hour
        
        # Defaults
        self.settings = {
            "license_key": None,
            "license_api": None,  # e.g., "https://prism-licensing.your-subdomain.workers.dev"
            "max_free_images": 5000,
            "backend_port": 50051,
            "default_db": str(self.data_dir / "prism.db"),
            "device": "auto",  # auto, cuda, mps, cpu
            "developer_mode": False,  # Enable advanced diagnostics (benchmarks)
            "video": {
                "enabled": True,
                "frames_per_second": 1.0,
                "max_frames_per_video": 300
            },
            "models": {
                "yolo": "yolov8m.pt",
                "siglip": "google/siglip-so400m-patch14-384"
            }
        }
        
        self.load()
        self._license_cache = self._load_license_cache() # Changed to assign the result of the new _load_license_cache

    def load(self):
        if self.config_path.exists():
            with open(self.config_path, "r") as f:
                user_settings = yaml.safe_load(f)
                if user_settings:
                    self.settings.update(user_settings)

    def save(self):
        with open(self.config_path, "w") as f:
            yaml.safe_dump(self.settings, f)

    @property
    def config_dir(self) -> Path: # Added config_dir property for consistency with credentials path
        return self.data_dir

    def load_credentials(self) -> dict:
        """Load credentials from separate secure file."""
        creds_path = self.config_dir / "credentials.yaml"
        if not creds_path.exists():
            return {}
        try:
            with open(creds_path, "r") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
            return {}

    def save_credentials(self, creds: dict):
        """Save credentials securely."""
        creds_path = self.config_dir / "credentials.yaml"
        try:
            # Ensure file exists first to set permissions
            if not creds_path.exists():
                creds_path.touch()
                os.chmod(creds_path, 0o600)
            
            with open(creds_path, "w") as f:
                yaml.safe_dump(creds, f)
            
            # Update permissions again just in case
            os.chmod(creds_path, 0o600)
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")

    @property
    def aws_creds(self) -> dict:
        return self.load_credentials().get("aws", {})

    @property
    def azure_creds(self) -> dict:
        return self.load_credentials().get("azure", {})

    def _compute_cache_integrity(self, data: dict) -> str:
        """Compute HMAC integrity hash for cache file to detect tampering."""
        # Create deterministic message from license data
        message = f"{data.get('key', '')}:{data.get('expires_at', '')}:{data.get('tier', '')}"
        # Use a static secret - this isn't for security, just integrity
        return hmac.new(b"prism-cache-integrity-v1", message.encode(), hashlib.sha256).hexdigest()

    def _verify_cache_integrity(self, data: dict) -> bool:
        """Verify the cache file hasn't been tampered with."""
        stored_integrity = data.get("_integrity", "")
        if not stored_integrity:
            return False
        computed = self._compute_cache_integrity(data)
        return hmac.compare_digest(stored_integrity, computed)

    def _save_license_cache(self, cache_data: dict):
        """Save license validation result to cache."""
        try:
            path = self.config_dir / "license.cache"
            with open(path, "w") as f:
                json.dump(cache_data, f)
            self._license_cache = cache_data
        except Exception as e:
            logger.warning(f"Failed to save license cache: {e}")

    def _verify_signature(self, data: dict) -> bool:
        """Verify the cryptographic signature of the license data."""
        try:
            signature_b64 = data.get("signature", "")
            if not signature_b64:
                return False
                
            signature = base64.b64decode(signature_b64)
            
            # Message format: "{key}|{expires_at}|{tier}" - must match worker signing
            message = f"{data.get('key', '')}|{data.get('expires_at', '')}|{data.get('tier', '')}".encode('utf-8')
            
            public_key = serialization.load_pem_public_key(PUBLIC_KEY_PEM.encode())
            public_key.verify(
                signature,
                message,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            return True
        except Exception as e:
            logger.warning(f"Signature verification failed: {e}")
            return False

    def _validate_license_api(self, key: str) -> dict:
        """Validate license key against the API with secure signature verification."""
        api_url = self.settings.get("license_api")
        
        # REQUIRE API_URL - No insecure fallback
        if not api_url:
            logger.error("No license API configured. Cannot validate license securely.")
            return {"valid": False}
        
        try:
            import requests
            response = requests.get(
                f"{api_url}/validate",
                params={"key": key},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Verify Signature First
                if not data.get("valid", False):
                    return {"valid": False}
                    
                # Add the key to the data for verification context if not present (likely is)
                if "key" not in data:
                    data["key"] = key
                
                # Check for signature
                has_signature = bool(data.get("signature"))
                    
                if has_signature and self._verify_signature(data):
                    logger.info("License signature verified successfully.")
                    
                    # Cache the signed response with integrity
                    data["_integrity"] = self._compute_cache_integrity(data)
                    self._save_license_cache(data)
                    
                    return {
                        "valid": True,
                        "email": data.get("email", ""),
                        "expires_at": data.get("expires_at", ""),
                        "tier": data.get("tier", "pro")
                    }
                else:
                    # No signature or invalid signature - require online validation
                    logger.error("License signature missing or INVALID. Rejecting.")
                    return {"valid": False, "error": "Invalid or missing signature"}
            else:
                logger.warning(f"License API returned status {response.status_code}")
                return {"valid": False}
                
        except Exception as e:
            logger.warning(f"License API request failed: {e}")
            return {"valid": False, "email": "", "expires_at": ""}

    def _load_license_cache(self) -> dict:
        """Load and verify signed license from cache."""
        # Use config_dir instead of cache_path to avoid confusion if cache_path was misconfigured
        cache_path = self.config_dir / "license.cache"
        if not cache_path.exists():
            return {}
            
        try:
            with open(cache_path, "r") as f:
                data = json.load(f)
                
            # Verify Signature AND Integrity for double protection
            if not self._verify_signature(data):
                logger.warning("Cached license signature invalid. Ignoring.")
                return {}
            
            if not self._verify_cache_integrity(data):
                logger.warning("Cached license integrity check failed. Possible tampering.")
                return {}
            
            # Check if expired
            expires_at = data.get("expires_at", "")
            if expires_at:
                try:
                    # Handle both Z and +00:00 formats
                    dt_str = expires_at.replace("Z", "+00:00")
                    # Skip invalid/far-future dates (year > 9999)
                    if dt_str.startswith("+") or len(dt_str.split("-")[0]) > 4:
                        logger.info("License has far-future expiration, treating as valid.")
                    else:
                        dt = datetime.fromisoformat(dt_str)
                        if datetime.now(dt.tzinfo) > dt:
                             logger.warning("Cached license expired.")
                             return {}
                except ValueError as e:
                    logger.warning(f"Date parse error, treating license as valid: {e}")
                    pass  # Treat parse errors as valid
             
            return data
                
        except Exception as e:
            logger.error(f"Failed to load/verify license cache: {e}")
            return {}

    def _get_license_info(self) -> dict:
        """Get license info, using offline cache if valid."""
        key = self.settings.get("license_key")
        if not key:
            return {"valid": False}
        
        # Trim whitespace from key
        key = key.strip()
            
        # 1. Try In-Memory Cache (Fastest)
        if self._license_cache and self._license_cache.get("key") == key:
            # Check validation TTL (e.g. 1 hour since last online check)
            last_checked = self._license_cache.get("validated_at", 0)
            if (time.time() - last_checked) < self._cache_ttl:
                return self._license_cache

        # 2. Try Online Validation
        online_result = self._validate_license_api(key)
        if online_result.get("valid"):
            # Update cache info
            online_result["key"] = key
            online_result["validated_at"] = time.time()
            self._save_license_cache(online_result)
            return online_result
            
        # 3. Offline Fallback (Network Failed?)
        # If we have a valid signed cache for this key, verify it hasn't expired
        if self._license_cache and self._license_cache.get("key") == key:
            # We already verified signature on load. Just check expiry.
            expires = self._license_cache.get("expires_at")
            if expires:
                try:
                    dt_str = expires.replace("Z", "+00:00")
                    dt = datetime.fromisoformat(dt_str)
                    if datetime.now(dt.tzinfo) < dt:
                        logger.info("Using valid offline license.")
                        return self._license_cache
                except Exception:
                    pass
            else:
                # No expiry = lifetime
                logger.info("Using valid offline license (lifetime).")
                return self._license_cache
        
        return {"valid": False}


    @property
    def is_pro(self) -> bool:
        """Legacy property for compatibility. All features now free."""
        return True  # Everything is free now
    
    @property
    def has_secret_features(self) -> bool:
        """Check if user has unlocked secret features via license key."""
        info = self._get_license_info()
        if not info.get("valid", False):
            return False
        tier = info.get("tier", "")
        return tier in ["pro", "enterprise", "secret"]

    @property
    def license_email(self) -> str:
        """Get the email associated with the license."""
        return self._get_license_info().get("email", "")

    @property
    def license_expires(self) -> str:
        """Get the expiration date of the license."""
        expires = self._get_license_info().get("expires_at", "")
        if expires:
            # Format: 2027-01-05T15:32:39.942Z -> 2027-01-05
            return expires[:10]
        return ""

config = Config()


