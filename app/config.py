from __future__ import annotations
from pathlib import Path

# Locations + base path
LOCATIONS = {"home": "Home", "batanovs": "Batanovs", "cherednychoks": "Cherednychoks"}
# BASE = Path("/mnt/photo-frame")  # tip for mac: Path.home() / "photo-frame"
BASE = Path("/Volumes/Photo-Frames")  # tip for mac: Path.home() / "photo-frame"

# Formats / sizes
EXTS = {".jpg", ".jpeg", ".png", ".heic", ".tif", ".tiff"}
RESIZE_WIDTH = 1280
RESIZE_HEIGHT = 1024
IM_QUALITY = 95
TIMEOUT_SECS = 600
IM_MODE = "convert"

# Database
DB_PATH = Path("/Volumes/Photo-Frames/photo_conversions_mac.db")
