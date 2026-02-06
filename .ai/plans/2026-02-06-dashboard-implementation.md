# Implementation Plan: Dashboard Implementation

## Goal
Create a visual dashboard to display photo conversion metrics using FastAPI, Tailwind CSS, and Jinja2. This includes a system service for auto-start on Debian/Ubuntu systems.

## User Review Required
> [!NOTE]
> This requires adding `fastapi`, `uvicorn`, `jinja2`, and `python-multipart` to project dependencies.
> The dashboard runs as a root service on Port 80 for the target deployment.

## Proposed Changes

### Dependencies
#### [MODIFY] [requirements.txt](file:///Users/ivan.cherednychok/Projects/photo-resizer/requirements.txt)
- Add `fastapi`
- Add `uvicorn`
- Add `jinja2`
- Add `python-multipart`

### Database Updates
#### [MODIFY] [app/database_operations.py](file:///Users/ivan.cherednychok/Projects/photo-resizer/app/database_operations.py)
- Update `PhotoDB` to accept `read_only` parameter.
- Implement read-only connection logic (`file:...?mode=ro`) to allow safe root access.

### Dashboard Module
#### [NEW] [dashboard/__init__.py](file:///Users/ivan.cherednychok/Projects/photo-resizer/dashboard/__init__.py)
- Empty package file.

#### [NEW] [dashboard/main.py](file:///Users/ivan.cherednychok/Projects/photo-resizer/dashboard/main.py)
- **FastAPI App Instance**:
    - Initialize `PhotoDB(read_only=True)`.
    - Mounts static/templates.
- **Routes**:
    - `GET /`: Renders `index.html`.
    - `GET /api/stats`: Returns JSON.
    - `GET /api/history`: Returns JSON.

#### [NEW] [dashboard/templates/index.html](file:///Users/ivan.cherednychok/Projects/photo-resizer/dashboard/templates/index.html)
- Clean, dark-mode/light-mode implementation using **Tailwind CSS (CDN)**.
- **Visuals**:
    - "System Status" indicator.
    - Summary Cards (Processed, Saved, Last Run).
    - Activity Feed table.

### Startup & Automation (Linux/Debian)
#### [NEW] [scripts/start_dashboard.sh](file:///Users/ivan.cherednychok/Projects/photo-resizer/scripts/start_dashboard.sh)
- `uvicorn dashboard.main:app --host 0.0.0.0 --port 80`

#### [NEW] [scripts/photo-resizer-dashboard.service](file:///Users/ivan.cherednychok/Projects/photo-resizer/scripts/photo-resizer-dashboard.service)
- Systemd Unit file.
- User: `root` (for Port 80 binding).

#### [NEW] [scripts/install_service.sh](file:///Users/ivan.cherednychok/Projects/photo-resizer/scripts/install_service.sh)
- Automates copying the `.service` file and reloading systemd.

### Documentation
#### [NEW] [DASHBOARD.md](file:///Users/ivan.cherednychok/Projects/photo-resizer/DASHBOARD.md)
- Installation and usage instructions.

## Verification

### Manual Verification
- [x] Run `python app.py` (main logic) while dashboard is running to ensure DB concurrency safety.
- [x] Run `uvicorn` locally to verify UI rendering.
- [x] Verify scripts generation.
