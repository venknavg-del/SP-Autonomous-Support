"""
Database Connection Layer — Dual-mode: Oracle DB (production) or SQLite (development).

Mode is auto-detected from environment:
  - If ORACLE_DSN or ORACLE_HOST is set → Oracle
  - Otherwise → SQLite (data/sp_support.db)

Oracle requires: pip install oracledb
SQLite uses: built-in sqlite3 + aiosqlite for async
"""

import os
import logging
import sqlite3
from typing import Optional, Any, List, Dict
from contextlib import contextmanager

logger = logging.getLogger("db")

# ── Auto-detect mode ──────────────────────────────────────────────
DB_MODE = "oracle" if os.getenv("ORACLE_DSN") or os.getenv("ORACLE_HOST") else "sqlite"

# ── Oracle connection pool (lazy init) ────────────────────────────
_oracle_pool = None

def _get_oracle_pool():
    global _oracle_pool
    if _oracle_pool is None:
        import oracledb
        
        dsn = os.getenv("ORACLE_DSN", "")
        if not dsn:
            host = os.getenv("ORACLE_HOST", "localhost")
            port = int(os.getenv("ORACLE_PORT", "1521"))
            service = os.getenv("ORACLE_SERVICE_NAME", "XEPDB1")
            dsn = oracledb.makedsn(host, port, service_name=service)
        
        wallet_location = os.getenv("ORACLE_WALLET_LOCATION", "")
        
        pool_params = {
            "user": os.getenv("ORACLE_USER", "system"),
            "password": os.getenv("ORACLE_PASSWORD", ""),
            "dsn": dsn,
            "min": 2,
            "max": 10,
            "increment": 1,
        }
        
        if wallet_location:
            pool_params["config_dir"] = wallet_location
            pool_params["wallet_location"] = wallet_location
            pool_params["wallet_password"] = os.getenv("ORACLE_WALLET_PASSWORD", "")
        
        _oracle_pool = oracledb.create_pool(**pool_params)
        logger.info(f"Oracle connection pool created: {dsn}")
    
    return _oracle_pool


# ── SQLite path ───────────────────────────────────────────────────
SQLITE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "sp_support.db")


# ── Unified DB interface ──────────────────────────────────────────

@contextmanager
def get_connection():
    """Get a database connection (Oracle or SQLite)."""
    if DB_MODE == "oracle":
        pool = _get_oracle_pool()
        conn = pool.acquire()
        try:
            yield conn
        finally:
            pool.release(conn)
    else:
        os.makedirs(os.path.dirname(SQLITE_PATH), exist_ok=True)
        conn = sqlite3.connect(SQLITE_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()


def execute(sql: str, params: dict = None, commit: bool = True) -> Optional[Any]:
    """Execute a SQL statement."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if DB_MODE == "oracle":
            cursor.execute(sql, params or {})
        else:
            # Convert Oracle-style :name params to SQLite-style :name params
            cursor.execute(sql, params or {})
        if commit:
            conn.commit()
        return cursor


def fetch_one(sql: str, params: dict = None) -> Optional[Dict]:
    """Fetch a single row as dict."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params or {})
        row = cursor.fetchone()
        if row is None:
            return None
        if DB_MODE == "oracle":
            columns = [col[0].lower() for col in cursor.description]
            return dict(zip(columns, row))
        else:
            return dict(row)


def fetch_all(sql: str, params: dict = None) -> List[Dict]:
    """Fetch all rows as list of dicts."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params or {})
        rows = cursor.fetchall()
        if DB_MODE == "oracle":
            columns = [col[0].lower() for col in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
        else:
            return [dict(row) for row in rows]


# ── Schema Migration ─────────────────────────────────────────────

def run_migration():
    """Create tables if they don't exist."""
    logger.info(f"Running DB migration (mode: {DB_MODE})...")
    
    if DB_MODE == "oracle":
        _migrate_oracle()
    else:
        _migrate_sqlite()
    
    logger.info("DB migration complete.")


def _migrate_oracle():
    """Create Oracle tables."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("""
            SELECT COUNT(*) FROM user_tables WHERE table_name = 'SP_INCIDENTS'
        """)
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                CREATE TABLE SP_INCIDENTS (
                    incident_id        VARCHAR2(50)  PRIMARY KEY,
                    scenario_id        VARCHAR2(100),
                    source             VARCHAR2(100),
                    raw_description    CLOB,
                    status             VARCHAR2(50)  DEFAULT 'Processing',
                    severity           VARCHAR2(10),
                    issue_type         VARCHAR2(50),
                    root_cause_analysis CLOB,
                    suggested_resolution CLOB,
                    confidence_score   NUMBER(5,4)   DEFAULT 0,
                    requires_human_approval NUMBER(1) DEFAULT 0,
                    human_approved     NUMBER(1),
                    jira_ticket_key    VARCHAR2(50),
                    jira_context       CLOB,
                    workaround         CLOB,
                    recommended_runbook CLOB,
                    errors             CLOB,
                    created_at         TIMESTAMP     DEFAULT SYSTIMESTAMP,
                    resolved_at        TIMESTAMP
                )
            """)
            logger.info("Created table: SP_INCIDENTS")
        
        cursor.execute("""
            SELECT COUNT(*) FROM user_tables WHERE table_name = 'SP_AGENT_EVENTS'
        """)
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                CREATE TABLE SP_AGENT_EVENTS (
                    event_id           NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                    incident_id        VARCHAR2(50)  NOT NULL,
                    agent              VARCHAR2(100) NOT NULL,
                    action             CLOB,
                    source             VARCHAR2(100),
                    created_at         TIMESTAMP     DEFAULT SYSTIMESTAMP,
                    CONSTRAINT fk_incident FOREIGN KEY (incident_id) REFERENCES SP_INCIDENTS(incident_id)
                )
            """)
            logger.info("Created table: SP_AGENT_EVENTS")
        
        conn.commit()


def _migrate_sqlite():
    """Create SQLite tables."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS SP_INCIDENTS (
                incident_id        TEXT PRIMARY KEY,
                scenario_id        TEXT,
                source             TEXT,
                raw_description    TEXT,
                status             TEXT DEFAULT 'Processing',
                severity           TEXT,
                issue_type         TEXT,
                root_cause_analysis TEXT,
                suggested_resolution TEXT,
                confidence_score   REAL DEFAULT 0,
                requires_human_approval INTEGER DEFAULT 0,
                human_approved     INTEGER,
                jira_ticket_key    TEXT,
                jira_context       TEXT,
                workaround         TEXT,
                recommended_runbook TEXT,
                errors             TEXT,
                created_at         TEXT,
                resolved_at        TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS SP_AGENT_EVENTS (
                event_id           INTEGER PRIMARY KEY AUTOINCREMENT,
                incident_id        TEXT NOT NULL,
                agent              TEXT NOT NULL,
                action             TEXT,
                source             TEXT,
                created_at         TEXT,
                FOREIGN KEY (incident_id) REFERENCES SP_INCIDENTS(incident_id)
            )
        """)
        
        conn.commit()
        logger.info("SQLite tables created/verified.")
