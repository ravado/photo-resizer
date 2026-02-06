from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pathlib import Path
import sqlite3
from typing import List, Dict, Any

from app.config import DB_PATH
from app.database_operations import PhotoDB

app = FastAPI(title="Photo Resizer Dashboard", docs_url=None, redoc_url=None)

# Setup Templates
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

def get_stats() -> Dict[str, Any]:
    """Fetch aggregate statistics from the database."""
    stats = {
        "total_files": 0,
        "total_saved_mb": 0.0,
        "success_rate": 0.0,
        "last_run": "Never"
    }
    
    with PhotoDB(DB_PATH, read_only=True) as db:
        if not db.conn:
            return stats
            
        # Total converted (SUCCESS)
        cur = db.conn.execute("SELECT COUNT(*) FROM conversions WHERE status='SUCCESS'")
        stats["total_files"] = cur.fetchone()[0]
        
        # Total saved MB
        cur = db.conn.execute("SELECT SUM(saved_mb) FROM conversions WHERE status='SUCCESS'")
        saved = cur.fetchone()[0]
        stats["total_saved_mb"] = round(saved, 2) if saved else 0.0
        
        # Success Rate (last 100 attempts to be relevant)
        cur = db.conn.execute("SELECT status FROM conversions ORDER BY converted_at DESC LIMIT 100")
        rows = cur.fetchall()
        if rows:
            successes = sum(1 for r in rows if r[0] == 'SUCCESS')
            stats["success_rate"] = round((successes / len(rows)) * 100, 1)
            
        # Last Run
        cur = db.conn.execute("SELECT converted_at FROM conversions ORDER BY converted_at DESC LIMIT 1")
        row = cur.fetchone()
        if row:
            # Simple timestamp (can be formatted in JS)
            stats["last_run"] = row[0] 

    return stats

def get_history(limit: int = 50) -> List[Dict[str, Any]]:
    """Fetch recent conversion history."""
    query = """
    SELECT converted_at, src_name, orig_width, orig_height, new_width, new_height, 
           status, saved_mb, duration_ms 
    FROM conversions 
    ORDER BY converted_at DESC 
    LIMIT ?
    """
    history = []
    with PhotoDB(DB_PATH, read_only=True) as db:
        if not db.conn:
            return []
        cur = db.conn.execute(query, (limit,))
        for row in cur.fetchall():
            history.append({
                "timestamp": row[0],
                "filename": row[1],
                "original_size": f"{row[2]}x{row[3]}" if row[2] else "?",
                "new_size": f"{row[4]}x{row[5]}" if row[4] else "?",
                "status": row[6],
                "saved_mb": row[7] if row[7] else 0.0,
                "duration_ms": row[8]
            })
    return history

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/data")
async def api_data():
    return {
        "stats": get_stats(),
        "history": get_history()
    }
