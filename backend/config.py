import yaml
import json
import time
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class Config:
    def __init__(self):
        self.config_path = Path.home() / ".prism" / "config.yaml"
        self.data_dir = Path.home() / ".prism"
        self.cache_path = self.data_dir / "license_cache.json"
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
        self._load_license_cache()

    def load(self):
        if self.config_path.exists():
            with open(self.config_path, "r") as f:
                user_settings = yaml.safe_load(f)
                if user_settings:
                    self.settings.update(user_settings)

    def save(self):
        with open(self.config_path, "w") as f:
            yaml.safe_dump(self.settings, f)

    def _load_license_cache(self):
        """Load cached license validation result."""
        if self.cache_path.exists():
            try:
                with open(self.cache_path, "r") as f:
                    self._license_cache = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load license cache: {e}")
                self._license_cache = None

    def _save_license_cache(self, cache_data: dict):
        """Save license validation result to cache."""
        try:
            with open(self.cache_path, "w") as f:
                json.dump(cache_data, f)
            self._license_cache = cache_data
        except Exception as e:
            logger.warning(f"Failed to save license cache: {e}")

    def _validate_license_api(self, key: str) -> dict:
        """Validate license key against the API. Returns full license data."""
        api_url = self.settings.get("license_api")
        
        if not api_url:
            # No API configured, fall back to local validation
            logger.debug("No license API configured, using local validation")
            valid = key.startswith("PRISM-PRO-") or key.startswith("PRISM-ENTERPRISE-")
            return {"valid": valid, "email": "", "expires_at": ""}
        
        try:
            import requests
            response = requests.get(
                f"{api_url}/validate",
                params={"key": key},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "valid": data.get("valid", False),
                    "email": data.get("email", ""),
                    "expires_at": data.get("expires_at", ""),
                    "tier": data.get("tier", "")
                }
            else:
                logger.warning(f"License API returned status {response.status_code}")
                return {"valid": False, "email": "", "expires_at": ""}
                
        except ImportError:
            logger.warning("requests library not available, using local validation")
            valid = key.startswith("PRISM-PRO-") or key.startswith("PRISM-ENTERPRISE-")
            return {"valid": valid, "email": "", "expires_at": ""}
        except Exception as e:
            logger.warning(f"License API request failed: {e}")
            # On network failure, check cache for last known valid state
            if self._license_cache and self._license_cache.get("key") == key:
                logger.info("Using cached license validation result")
                return {
                    "valid": self._license_cache.get("valid", False),
                    "email": self._license_cache.get("email", ""),
                    "expires_at": self._license_cache.get("expires_at", "")
                }
            return {"valid": False, "email": "", "expires_at": ""}

    def _get_license_info(self) -> dict:
        """Get license info, using cache if valid."""
        key = self.settings.get("license_key")
        if not key:
            return {"valid": False, "email": "", "expires_at": ""}
        
        # Basic format check first
        if not (key.startswith("PRISM-PRO-") or key.startswith("PRISM-ENTERPRISE-")):
            return {"valid": False, "email": "", "expires_at": ""}
        
        # Check cache
        if self._license_cache:
            cache_key = self._license_cache.get("key")
            cache_time = self._license_cache.get("validated_at", 0)
            
            # Ensure cache has new fields (email), otherwise force refresh
            has_email = "email" in self._license_cache
            
            # Use cache if same key, not expired, AND has new fields
            if cache_key == key and (time.time() - cache_time) < self._cache_ttl and has_email:
                return self._license_cache
        
        # Validate against API
        result = self._validate_license_api(key)
        
        # Update cache
        cache_data = {
            "key": key,
            "valid": result.get("valid", False),
            "email": result.get("email", ""),
            "expires_at": result.get("expires_at", ""),
            "validated_at": time.time()
        }
        self._save_license_cache(cache_data)
        
        return cache_data


    @property
    def is_pro(self) -> bool:
        """Check if user has a valid Pro license."""
        return self._get_license_info().get("valid", False)

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


