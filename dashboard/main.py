from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pathlib import Path
import sqlite3
from typing import List, Dict, Any

from app.config import DB_PATH
from app.database_operations import PhotoDB

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from pathlib import Path
import sqlite3
from typing import List, Dict, Any, Optional
import mimetypes

from app.config import DB_PATH, LOCATIONS, BASE, EXTS
from app.database_operations import PhotoDB

app = FastAPI(title="Photo Resizer Dashboard", docs_url=None, redoc_url=None)

# Setup Templates
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

def get_locations_config() -> Dict[str, str]:
    """Return available locations from config."""
    return LOCATIONS

def get_stats(location: Optional[str] = None) -> Dict[str, Any]:
    """Fetch aggregate statistics, optionally filtered by location."""
    stats = {
        "total_files": 0,
        "total_saved_mb": 0.0,
        "success_rate": 0.0,
        "compression_ratio": 0.0,
        "last_run": "Never"
    }
    
    with PhotoDB(DB_PATH, read_only=True) as db:
        if not db.conn:
            return stats
        
        # Base query parts
        where_clauses = ["status='SUCCESS'"]
        params = []
        
        if location and location in LOCATIONS:
            # Filter by path containing the folder name
            folder_name = LOCATIONS[location]
            where_clauses.append("src_fullpath LIKE ?")
            params.append(f"%/{folder_name}/%")

        where_sql = " AND ".join(where_clauses)
        
        # 1. Counts and Size Savings
        query = f"""
            SELECT COUNT(*), SUM(saved_mb), SUM(src_size), SUM(out_size_bytes) 
            FROM conversions 
            WHERE {where_sql}
        """
        cur = db.conn.execute(query, params)
        row = cur.fetchone()
        
        if row:
            stats["total_files"] = row[0]
            stats["total_saved_mb"] = round(row[1], 2) if row[1] else 0.0
            total_src = row[2] or 0
            total_out = row[3] or 0
            
            # Compression Ratio: e.g. 5.0 means original was 5x larger
            if total_out > 0:
                stats["compression_ratio"] = round(total_src / total_out, 1)
            else:
                 stats["compression_ratio"] = 0.0

        # 2. Success Rate (Last 100 relevant to filter)
        # We need a fresh where clause without status='SUCCESS' for the rate
        rate_where = ["1=1"]
        rate_params = []
        if location and location in LOCATIONS:
            folder_name = LOCATIONS[location]
            rate_where.append("src_fullpath LIKE ?")
            rate_params.append(f"%/{folder_name}/%")
            
        rate_sql = " AND ".join(rate_where)
        
        query_rate = f"SELECT status FROM conversions WHERE {rate_sql} ORDER BY converted_at DESC LIMIT 100"
        cur = db.conn.execute(query_rate, rate_params)
        rows = cur.fetchall()
        if rows:
            successes = sum(1 for r in rows if r[0] == 'SUCCESS')
            stats["success_rate"] = round((successes / len(rows)) * 100, 1)

        # 3. Last Run
        query_last = f"SELECT converted_at FROM conversions WHERE {rate_sql} ORDER BY converted_at DESC LIMIT 1"
        cur = db.conn.execute(query_last, rate_params)
        row = cur.fetchone()
        if row:
            stats["last_run"] = row[0]

    return stats

def get_history(limit: int = 50, location: Optional[str] = None, only_failures: bool = False, page: int = 1, per_page: int = 25) -> List[Dict[str, Any]]:
    """Fetch recent conversion history with filtering and pagination."""
    where_clauses = ["1=1"]
    params = []

    if location and location in LOCATIONS:
        folder_name = LOCATIONS[location]
        # Use table alias 'c'
        where_clauses.append("c.src_fullpath LIKE ?")
        params.append(f"%/{folder_name}/%")

    if only_failures:
        where_clauses.append("c.status != 'SUCCESS' AND c.status != 'SKIPPED_DUP' AND c.status != 'ALREADY_DONE'")

    where_sql = " AND ".join(where_clauses)
    
    # Calculate offset for pagination
    offset = (page - 1) * per_page

    # Join with a subquery of unique successful conversions to get dimensions for duplicates
    query = f"""
    SELECT 
        c.converted_at, c.src_name, 
        COALESCE(c.orig_width, s.orig_width) as orig_width,
        COALESCE(c.orig_height, s.orig_height) as orig_height,
        COALESCE(c.new_width, s.new_width) as new_width,
        COALESCE(c.new_height, s.new_height) as new_height,
        c.status, c.saved_mb, c.duration_ms, c.error, c.src_fullpath, c.dst_fullpath,
        c.src_size, c.out_size_bytes, s.src_fullpath as copied_from
    FROM conversions c
    LEFT JOIN (
        SELECT src_hash, orig_width, orig_height, new_width, new_height, src_fullpath
        FROM conversions
        WHERE status = 'SUCCESS'
        GROUP BY src_hash
    ) s ON c.src_hash = s.src_hash
    WHERE {where_sql}
    ORDER BY c.converted_at DESC 
    LIMIT ? OFFSET ?
    """
    params.extend([per_page, offset])

    history = []
    with PhotoDB(DB_PATH, read_only=True) as db:
        if not db.conn:
            return []
        cur = db.conn.execute(query, params)
        for row in cur.fetchall():
            history.append({
                "timestamp": row[0],
                "filename": row[1],
                "original_size": f"{row[2]}x{row[3]}" if row[2] else "?",
                "new_size": f"{row[4]}x{row[5]}" if row[4] else "?",
                "orig_width": row[2],
                "orig_height": row[3],
                "new_width": row[4],
                "new_height": row[5],
                "status": row[6],
                "saved_mb": row[7] if row[7] else 0.0,
                "duration_ms": row[8],
                "error": row[9],
                "src_fullpath": row[10],
                "dst_fullpath": row[11],
                "src_size_bytes": row[12],
                "out_size_bytes": row[13],
                "copied_from": row[14]
            })
    return history

def get_history_count(location: Optional[str] = None, only_failures: bool = False) -> int:
    """Get total count of history records for pagination."""
    where_clauses = ["1=1"]
    params = []

    if location and location in LOCATIONS:
        folder_name = LOCATIONS[location]
        where_clauses.append("src_fullpath LIKE ?")
        params.append(f"%/{folder_name}/%")

    if only_failures:
        where_clauses.append("status != 'SUCCESS' AND status != 'SKIPPED_DUP' AND status != 'ALREADY_DONE'")

    where_sql = " AND ".join(where_clauses)

    query = f"SELECT COUNT(*) FROM conversions WHERE {where_sql}"
    
    with PhotoDB(DB_PATH, read_only=True) as db:
        if not db.conn:
            return 0
        cur = db.conn.execute(query, params)
        row = cur.fetchone()
        return row[0] if row else 0

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "locations": LOCATIONS
    })

@app.get("/api/data")
async def api_data(loc: str = None, failures: bool = False, page: int = 1, per_page: int = 25):
    """
    API Query Params:
    - loc: Location slug (e.g., 'home')
    - failures: 'true' to show only failures/issues
    - page: Page number (1-based)
    - per_page: Items per page
    """
    # Convert 'null' or empty string to None
    location = loc if loc and loc != "null" else None
    
    total_records = get_history_count(location=location, only_failures=failures)
    total_pages = (total_records + per_page - 1) // per_page
    
    return {
        "stats": get_stats(location=location),
        "history": get_history(location=location, only_failures=failures, page=page, per_page=per_page),
        "pagination": {
            "current_page": page,
            "per_page": per_page,
            "total_records": total_records,
            "total_pages": total_pages
        }
    }

@app.get("/api/image")
async def serve_image(path: str):
    """
    Serve an image file securely.
    Only serves files within the BASE directory with valid image extensions.
    """
    try:
        file_path = Path(path).resolve()
        
        # Security: Ensure path is under BASE directory
        try:
            file_path.relative_to(BASE)
        except ValueError:
            return JSONResponse(
                status_code=403,
                content={"error": "Access denied: path outside allowed directory"}
            )
        
        # Validate extension
        if file_path.suffix.lower() not in EXTS:
            return JSONResponse(
                status_code=400,
                content={"error": f"Invalid file type: {file_path.suffix}"}
            )
        
        # Check file exists
        if not file_path.exists():
            return JSONResponse(
                status_code=404,
                content={"error": "File not found"}
            )
        
        # Determine MIME type
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            mime_type = "application/octet-stream"
        
        return FileResponse(
            path=str(file_path),
            media_type=mime_type,
            filename=file_path.name
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.post("/api/retry")
async def retry_conversion(request: Request):
    """
    Retry a failed conversion.
    Expects JSON: {"file_path": "/full/path/to/image.jpg"}
    """
    import time
    from app.config import BASE, EXTS, RESIZE_WIDTH, RESIZE_HEIGHT, IM_QUALITY, TIMEOUT_SECS
    from app.planner import Planner
    from app.imaging import ImageEngine
    from app.converter import Converter
    from app.logging_setup import configure_logging
    
    try:
        body = await request.json()
        file_path_str = body.get("file_path")
        
        if not file_path_str:
            return {"success": False, "message": "Missing file_path parameter"}
        
        file_path = Path(file_path_str)
        
        # Validation
        if not file_path.exists():
            return {"success": False, "message": f"File not found: {file_path_str}"}
        
        if file_path.suffix.lower() not in EXTS:
            return {"success": False, "message": f"Invalid file type: {file_path.suffix}"}
        
        # Determine location from path
        location_key = None
        for key, name in LOCATIONS.items():
            if f"/{name}/" in str(file_path):
                location_key = key
                break
        
        if not location_key:
            return {"success": False, "message": "Could not determine location from path"}
        
        # Setup converter (same as main.py)
        make_logger = configure_logging(
            level="INFO",
            service_name="photo-resizer-retry",
            to_stderr=False,
            to_journal=False,
        )
        
        planner = Planner(BASE, LOCATIONS, EXTS)
        engine = ImageEngine(timeout=TIMEOUT_SECS, quality=IM_QUALITY)
        converter = Converter(planner, engine, DB_PATH, make_logger=make_logger)
        
        # Get paths using dirs_for_location
        watch_dir, out_dir = planner.dirs_for_location(location_key)
        
        # Open DB for writing
        with PhotoDB(DB_PATH, read_only=False) as db:
            # Run conversion
            duration = converter.process_one(
                db=db,
                idx=1,
                total=1,
                full_path=file_path,
                watch_dir=watch_dir,
                out_dir=out_dir
            )
        
        return {
            "success": True,
            "message": f"Conversion completed in {duration}s",
            "duration": duration
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Retry failed: {str(e)}"
        }
