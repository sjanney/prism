"""
Prism Error Codes

All error codes follow the format: PSM-XXXX
See docs/error-codes.md for full documentation.
"""

class PrismError(Exception):
    """Base class for Prism errors with error codes."""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")

# Connection Errors (PSM-1XXX)
class BackendConnectionError(PrismError):
    def __init__(self, details: str = ""):
        super().__init__("PSM-1001", f"Backend connection failed. {details}")

class BackendTimeoutError(PrismError):
    def __init__(self, operation: str = "Request"):
        super().__init__("PSM-1002", f"{operation} timed out. Model may be loading.")

# Model Errors (PSM-2XXX)
class ModelLoadingError(PrismError):
    def __init__(self, model_name: str, details: str = ""):
        super().__init__("PSM-2001", f"Failed to load {model_name}. {details}")

class CudaOutOfMemoryError(PrismError):
    def __init__(self):
        super().__init__("PSM-2002", "CUDA out of memory. Try closing other GPU apps or use CPU.")

# Database Errors (PSM-3XXX)
class DimensionMismatchError(PrismError):
    def __init__(self, expected: int, actual: int):
        super().__init__(
            "PSM-3001", 
            f"Dimension mismatch. Model uses {expected}d vectors, but database has {actual}d. "
            "Delete prism.db and re-index."
        )

class DatabaseLockedError(PrismError):
    def __init__(self):
        super().__init__("PSM-3002", "Database is locked. Close other Prism instances.")

class DatabaseNotFoundError(PrismError):
    def __init__(self, path: str):
        super().__init__("PSM-3003", f"Database not found: {path}. Index some data first.")

# File System Errors (PSM-4XXX)
class PathNotFoundError(PrismError):
    def __init__(self, path: str):
        super().__init__("PSM-4001", f"Path not found: {path}")

class NoImagesFoundError(PrismError):
    def __init__(self, path: str):
        super().__init__("PSM-4002", f"No images found in: {path}")

class PermissionDeniedError(PrismError):
    def __init__(self, path: str):
        super().__init__("PSM-4003", f"Permission denied: {path}")

# License Errors (PSM-5XXX)
class InvalidLicenseError(PrismError):
    def __init__(self):
        super().__init__("PSM-5001", "Invalid license key. Keys start with 'PRISM-PRO-'.")

class FreeLimitReachedError(PrismError):
    def __init__(self, limit: int):
        super().__init__("PSM-5002", f"Free version limit ({limit} images). Upgrade to Pro.")
