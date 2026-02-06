# AI / Developer Guidelines & Recommendations

## Recommended Comments & Intelligence
When analyzing or modifying this codebase, consider the following context which might not be immediately obvious from the code alone.

### 1. The "Bloat" Issue (Concurrency)
- **Problem**: Cron jobs often overlap if processing takes longer than the interval.
- **Symptom**: The database fills with duplicate entries for the same file processing, faster than the logic can dedupe them (race condition between checking DB and writing to DB).
- **Solution Strategy**: Implement `fcntl.flock` in `main.py` to ensure exclusivity per profile.

### 2. ImageMagick Wrapper (`app/imaging.py`)
- **Dual Support**: The code supports both v6 (`convert`, `identify`) and v7 (`magick`) CLIs. Always prefer `magick` if available.
- **Performance**: `subprocess.run` is used for every single image. This is robust but has overhead.

### 3. Database Strategy (`app/database_operations.py`)
- **WAL Mode**: `PRAGMA journal_mode=WAL` is essential for performance and concurrent reading.
- **Indexing**: Indices on `src_hash` are critical for the deduplication logic.

### 4. File Handling
- **Temporary Files**: The `Converter` creates `_auto_oriented` and `_resized` temp files in the *source* directory (or watch dir). Logic exists to clean them up, but a crash could leave them.
- **Atomic Moves**: `shutil.move` is used to put the final file in `Resized/`.

### 5. Future Improvements
- **AsyncIO**: Moving to `asyncio` could allow processing multiple images in parallel (limited by CPU/IO), but `subprocess` calls block the event loop unless handled carefully.
- **Python-native Imaging**: Replacing ImageMagick with `Pillow` or `wand` could remove the external dependency and process spawning overhead.

## Plan Storage
- **Location**: `.ai/plans/`
- **Convention**: Store implementation plans here before execution. Use the naming convention `YYYY-MM-DD-feature-name.md`.
- **Requirement**: Every plan in planning mode MUST be saved into an actual file when approved.
