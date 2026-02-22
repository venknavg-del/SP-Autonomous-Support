import os
import time
import asyncio
import logging
import shutil
from pathlib import Path
from src.mcp.email_parser import parse_email
from src.schemas.api import IncidentRequest
import sqlite3

logger = logging.getLogger(__name__)

# Constants
EMAILS_DIR = Path("data/emails")
PROCESSED_DIR = EMAILS_DIR / "processed"
DB_PATH = "data/sp_support.db"
POLL_INTERVAL = int(os.getenv("EMAIL_POLL_INTERVAL_SECONDS", 5))

def setup_directories():
    EMAILS_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

def setup_db():
    """Ensure the processed emails tracking table exists."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS SP_PROCESSED_EMAILS (
            filename TEXT PRIMARY KEY,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def is_processed(filename: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM SP_PROCESSED_EMAILS WHERE filename = ?", (filename,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def mark_processed(filename: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO SP_PROCESSED_EMAILS (filename) VALUES (?)", (filename,))
    conn.commit()
    conn.close()

async def process_email(filepath: Path):
    """Parses an email and submits it to the orchestrator."""
    filename = filepath.name
    
    # Check DB first
    if is_processed(filename):
        # Already processed in a past run, but file is still here? Move it.
        try:
            shutil.move(str(filepath), str(PROCESSED_DIR / filename))
        except Exception:
            pass
        return
        
    logger.info(f"[Email Poller] Processing new email: {filename}")
    
    try:
        # Parse email via existing parser
        email_data = parse_email(str(filepath))
        subject = email_data.get("subject", "No Subject")
        body = email_data.get("body", "")
        
        # Construct raw description (subject + body)
        raw_description = f"Subject: {subject}\n\n{body}".strip()
        
        # Generate a unique incident ID based on timestamp
        incident_id = f"INC-{int(time.time())}"
        
        req = IncidentRequest(
            source="email",
            raw_description=raw_description
        )
        
        # Fire off the orchestrator
        # We don't await the full orchestrator to avoid blocking the poller
        from src.main import run_orchestrator
        asyncio.create_task(run_orchestrator(incident_id, req))
        
        # Mark as processed in DB
        mark_processed(filename)
        
        # Move file to processed folder
        try:
            shutil.move(str(filepath), str(PROCESSED_DIR / filename))
            logger.info(f"[Email Poller] Moved {filename} to processed folder.")
        except Exception as move_err:
            logger.error(f"[Email Poller] Failed to move file {filename}: {move_err}")
            
    except Exception as e:
        logger.error(f"[Email Poller] Failed to process {filename}: {e}")

async def watch_emails_folder():
    """Continuously polls the emails directory for new files."""
    logger.info(f"[Email Poller] Started watching {EMAILS_DIR} (interval: {POLL_INTERVAL}s)")
    setup_directories()
    setup_db()
    
    while True:
        try:
            if EMAILS_DIR.exists():
                for file_path in EMAILS_DIR.iterdir():
                    if file_path.is_file() and file_path.suffix.lower() in ['.eml', '.msg', '.txt']:
                        await process_email(file_path)
        except Exception as e:
            logger.error(f"[Email Poller] Error during poll cycle: {e}")
            
        await asyncio.sleep(POLL_INTERVAL)

def start_poller_background_task():
    """Helper to start the poller in the FastAPI lifecycle."""
    asyncio.create_task(watch_emails_folder())
