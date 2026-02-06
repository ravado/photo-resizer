# Project Overview: Photo Resizer

## 1. Purpose
The **Photo Resizer** is an automated utility designed to process images for a digital photo frame system. Its primary goals are:
- **Resize** high-resolution photos to fit the target display resolution (1280x1024), saving storage space.
- **Auto-orient** images correctly based on EXIF data.
- **Log** all conversions to a SQLite database for tracking, deduplication, and statistics.
- **Deduplicate** processing by checking file hashes against the database to avoid re-converting identical files.

## 2. Architecture & Workflow
The application runs as a CLI tool, typically invoked via a cron job using `run.sh`.

### 2.1. High-Level Flow
1.  **Entry Point**: `run.sh` activates the virtual environment and calls `main.py` with a specific `PROFILE` (e.g., `home`).
2.  **Initialization**: `main.py` initializes the `Planner`, `ImageEngine`, and `Converter`.
3.  **Discovery**: `Planner` scans the `Original` directory for the given profile to find supported image files.
4.  **Processing** (`Converter.run`):
    - Iterates through candidate files.
    - Computes SHA256 hash of the source file.
    - **Check 1 (Already Done)**: Queries DB to see if this hash has already been converted to the target path. If so, skips.
    - **Check 2 (Deduplication)**: Queries DB to see if this hash exists anywhere else. If so, copies the existing converted file instead of reprocessing.
    - **Conversion**:
        - **Auto-Orient**: Fixes rotation.
        - **Resize**: Calculates scaling factor to fit within bounds (default 1280x1024) while maintaining aspect ratio, slightly upscaled (0.01) to ensure coverage. Uses ImageMagick (`magick` or `convert`).
    - **Logging**: Records the result (Success, Skipped, Failed) and metadata (dimensions, size savings, duration) to `photo_conversions.db`.

### 2.2. Directory Structure
The system expects a specific directory layout defined in `config.py`:
- **Base Root**: `/mnt/photo-frame` (or as configured in `BASE`).
- **Profile Folders**: `Home`, `Batanovs`, etc.
    - `Original/`: Source images (read-only).
    - `Resized/`: Processed output images (write).
- **Database**: `photo_conversions.db` at the root.

## 3. Key Components

### `app/main.py`
- Bootstraps the application.
- Configures logging.
- Instantiates core classes.

### `app/converter.py`
- Core logic engine.
- Orchestrates the conversion pipeline: Hash -> Check DB -> Convert/Copy -> Log DB.
- Handles temporary files (`*_auto_oriented*`, `*_resized*`) and cleans them up.

### `app/database_operations.py` (`PhotoDB`)
- SQL interaction layer using `sqlite3`.
- Schema: `conversions` table tracks every attempt.
- **Key optimizations**: WAL mode enabled for concurrency.

### `app/imaging.py` (`ImageEngine`)
- Wrapper around ImageMagick (`magick` or `convert`/`identify` CLI tools).
- Handles external process execution with timeouts.

### `app/planner.py`
- Handles path logic and file discovery.
- Maps location keys (e.g., "home") to physical paths.

### `app/config.py`
- Central configuration:
    - `LOCATIONS`: Mapping of CLI keys to folder names.
    - `RESIZE_WIDTH/HEIGHT`: Target resolution.
    - `EXTS`: Supported extensions (.jpg, .png, .heic, etc.).

## 4. Database Schema
Table `conversions`:
- `status`: SUCCESS, FAILED, SKIPPED_DUP, ALREADY_DONE.
- `src_hash`: SHA256 of original file (critical for dedupe).
- `src_fullpath` / `dst_fullpath`: Tracking paths.
- `saved_mb`, `saved_percent`: Efficiency metrics.

## 5. Known Issues & Considerations
- **Concurrency**: The script may be run multiple times simultaneously (e.g., overlapping cron jobs), causing race conditions and database bloating. *Mitigation planned: File locking.*
- **Dependencies**: Requires `ImageMagick` installed on the host system.
