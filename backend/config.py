import os
import yaml
from pathlib import Path

class Config:
    def __init__(self):
        self.config_path = Path.home() / ".prism" / "config.yaml"
        self.data_dir = Path.home() / ".prism"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Defaults
        self.settings = {
            "license_key": None,
            "max_free_images": 5000,
            "backend_port": 50051,
            "default_db": str(self.data_dir / "prism.db"),
            "device": "auto",  # auto, cuda, mps, cpu
            "developer_mode": False,  # Enable advanced diagnostics (benchmarks)
            "models": {
                "yolo": "yolov8m.pt",
                "siglip": "google/siglip-so400m-patch14-384"
            }
        }
        
        self.load()

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
    def is_pro(self):
        # Logic to validate license key
        key = self.settings.get("license_key")
        if not key:
            return False
        # In a real app, this would ping a server or check a signature
        return key.startswith("PRISM-PRO-")

config = Config()
