from __future__ import annotations
import os
from pathlib import Path
from typing import Tuple, List

class Planner:
    def __init__(self, base: Path, locations: dict[str, str], exts: set[str]):
        self.base = base
        self.locations = locations
        self.exts = exts

    def dirs_for_location(self, key: str) -> tuple[Path, Path]:
        loc_cap = self.locations[key]
        watch = self.base / loc_cap / "Original"
        out = self.base / loc_cap / "Resized"
        out.mkdir(parents=True, exist_ok=True)
        return watch, out

    def list_candidates(self, root: Path) -> list[Path]:
        out: list[Path] = []
        for r, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for fn in files:
                # skip our temp artifacts outright
                if "_auto_oriented" in fn or "_resized" in fn:
                    continue
                p = Path(r) / fn
                if p.suffix.lower() in self.exts:
                    out.append(p)
        return sorted(out)

    @staticmethod
    def mapped_ext(original_ext: str) -> str:
        lower = original_ext.lower()
        if lower in {".heic", ".tif", ".tiff"}:
            return ".JPG" if any(ch.isupper() for ch in original_ext) else ".jpg"
        return original_ext

    @staticmethod
    def expected_paths(src: Path, watch_dir: Path, out_dir: Path, out_ext: str) -> tuple[Path, Path, Path]:
        resized = watch_dir / f"{src.stem}_resized{out_ext}"
        out = out_dir / f"{src.stem}{out_ext}"
        auto = watch_dir / f"{src.stem}_auto_oriented{out_ext}"
        return resized, out, auto
