from __future__ import annotations
from pathlib import Path
from decimal import Decimal
import subprocess, hashlib
from shutil import which

class ImageEngine:
    def __init__(self, timeout: int, quality: int):
        self.timeout = timeout
        self.quality = quality
        self.magick, self.convert, self.identify = self._pick_im()

    def _pick_im(self):
        magick = which("magick")
        convert = which("convert")
        identify = which("identify")
        if not (magick or (convert and identify)):
            raise SystemExit("ImageMagick not found. Need either 'magick' or 'convert'+'identify' in PATH.")
        return magick, convert, identify

    def _run(self, argv: list[str]):
        subprocess.run(argv, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       timeout=self.timeout, text=True)

    def auto_orient(self, src: Path, dst: Path):
        if self.magick:
            argv = [self.magick, "convert", str(src), "-auto-orient", str(dst)]
        else:
            argv = [self.convert, str(src), "-auto-orient", str(dst)]
        self._run(argv)

    def identify_size(self, path: Path) -> tuple[int, int]:
        if self.magick:
            argv = [self.magick, "identify", "-format", "%w %h", str(path)]
        else:
            argv = [self.identify, "-format", "%w %h", str(path)]
        cp = subprocess.run(argv, check=True, capture_output=True, text=True, timeout=self.timeout)
        w, h = (int(x) for x in cp.stdout.strip().split())
        return w, h

    def resize_percent(self, src: Path, dst: Path, percent: Decimal) -> str:
        pct_str = f"{percent:.2f}%"
        if self.magick:
            argv = [self.magick, "convert", str(src), "-resize", pct_str, "-quality", str(self.quality), str(dst)]
        else:
            argv = [self.convert, str(src), "-resize", pct_str, "-quality", str(self.quality), str(dst)]
        self._run(argv)
        return f"-resize {pct_str} -quality {self.quality}"

    @staticmethod
    def sha256_file(path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
