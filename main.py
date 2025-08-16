from __future__ import annotations
import argparse
from config import LOCATIONS, BASE, EXTS, RESIZE_WIDTH, RESIZE_HEIGHT, IM_QUALITY, DB_PATH, TIMEOUT_SECS
from planner import Planner
from imaging import ImageEngine
from converter import Converter

def parse_args():
    ap = argparse.ArgumentParser(description="Convert (or skip by hash) + log to SQLite.")
    ap.add_argument("location", choices=list(LOCATIONS.keys()), nargs="?", default="home")
    return ap.parse_args()

def main():
    args = parse_args()
    planner = Planner(BASE, LOCATIONS, EXTS)
    engine = ImageEngine(timeout=TIMEOUT_SECS, quality=IM_QUALITY)
    Converter(planner, engine, DB_PATH).run(args.location)

if __name__ == "__main__":
    main()
