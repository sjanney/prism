"""
Tests for config.py - License validation and configuration management.
"""
import pytest
import sys
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestConfigBasics:
    """Test basic config functionality."""
    
    def test_config_loads(self):
        """Config module should load without errors."""
        from config import config
        assert config is not None
        assert hasattr(config, 'settings')
    
    def test_config_has_defaults(self):
        """Config should have default settings."""
        from config import config
        assert 'backend_port' in config.settings
        assert 'max_free_images' in config.settings
        assert config.settings['max_free_images'] == 5000
    
    def test_config_dir_exists(self):
        """Config directory should be created."""
        from config import config
        assert config.config_dir.exists()


class TestLicenseValidation:
    """Test license validation logic."""
    
    def test_is_pro_returns_bool(self):
        """is_pro should return a boolean."""
        from config import config
        result = config.is_pro
        assert isinstance(result, bool)
    
    def test_license_email_returns_string(self):
        """license_email should return a string."""
        from config import config
        result = config.license_email
        assert isinstance(result, str)
    
    def test_license_expires_returns_string(self):
        """license_expires should return a string."""
        from config import config
        result = config.license_expires
        assert isinstance(result, str)


class TestCacheIntegrity:
    """Test cache integrity functionality."""
    
    def test_compute_cache_integrity_deterministic(self):
        """Cache integrity should be deterministic."""
        from config import config
        data = {"key": "test-key", "expires_at": "2027-01-01", "tier": "pro"}
        hash1 = config._compute_cache_integrity(data)
        hash2 = config._compute_cache_integrity(data)
        assert hash1 == hash2
    
    def test_compute_cache_integrity_changes_with_data(self):
        """Different data should produce different hashes."""
        from config import config
        data1 = {"key": "test-key", "expires_at": "2027-01-01", "tier": "pro"}
        data2 = {"key": "other-key", "expires_at": "2027-01-01", "tier": "pro"}
        hash1 = config._compute_cache_integrity(data1)
        hash2 = config._compute_cache_integrity(data2)
        assert hash1 != hash2
    
    def test_verify_cache_integrity_valid(self):
        """Valid integrity should pass verification."""
        from config import config
        data = {"key": "test-key", "expires_at": "2027-01-01", "tier": "pro"}
        data["_integrity"] = config._compute_cache_integrity(data)
        assert config._verify_cache_integrity(data) is True
    
    def test_verify_cache_integrity_tampered(self):
        """Tampered data should fail verification."""
        from config import config
        data = {"key": "test-key", "expires_at": "2027-01-01", "tier": "pro"}
        data["_integrity"] = config._compute_cache_integrity(data)
        data["tier"] = "enterprise"  # Tamper with data
        assert config._verify_cache_integrity(data) is False
    
    def test_verify_cache_integrity_missing(self):
        """Missing integrity should fail verification."""
        from config import config
        data = {"key": "test-key", "expires_at": "2027-01-01", "tier": "pro"}
        assert config._verify_cache_integrity(data) is False


class TestCredentialsManagement:
    """Test credentials loading and saving."""
    
    def test_aws_creds_returns_dict(self):
        """aws_creds should return a dict."""
        from config import config
        result = config.aws_creds
        assert isinstance(result, dict)
    
    def test_azure_creds_returns_dict(self):
        """azure_creds should return a dict."""
        from config import config
        result = config.azure_creds
        assert isinstance(result, dict)


class TestSignatureVerification:
    """Test RSA signature verification."""
    
    def test_verify_signature_rejects_missing(self):
        """Missing signature should be rejected."""
        from config import config
        data = {"valid": True, "key": "test", "expires_at": "2027-01-01", "tier": "pro"}
        result = config._verify_signature(data)
        assert result is False
    
    def test_verify_signature_rejects_invalid(self):
        """Invalid signature should be rejected."""
        from config import config
        data = {
            "valid": True, 
            "key": "test", 
            "expires_at": "2027-01-01", 
            "tier": "pro",
            "signature": "invalid-base64-signature"
        }
        result = config._verify_signature(data)
        assert result is False
