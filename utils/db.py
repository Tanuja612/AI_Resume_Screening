import sqlite3
import threading
import os
from datetime import datetime

# Database path may be overridden by environment variable for production
DB_PATH = os.environ.get('DATABASE_URL') or os.path.join(os.getcwd(), "instance", "app.db")
# Note: in a production environment you should use a full RDBMS such as
# PostgreSQL or MySQL instead of sqlite3. DATABASE_URL can point to the
# appropriate connection string (e.g. "postgresql://user:pass@host/db").

_lock = threading.Lock()
_conn = None

def get_db():
    """Return a sqlite3 connection and ensure required tables exist."""
    global _conn
    with _lock:
        if _conn is None:
            os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
            _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            _conn.row_factory = sqlite3.Row
            _ensure_tables(_conn)
        return _conn

def _ensure_tables(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT,
            email TEXT,
            phone_number TEXT,
            created_at TEXT,
            last_login TEXT
        )
        """
    )
    
    # Check if last_login column exists, if not add it
    cursor = conn.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in cursor.fetchall()]
    if 'last_login' not in columns:
        try:
            conn.execute("ALTER TABLE users ADD COLUMN last_login TEXT")
            conn.commit()
        except Exception:
            pass
    
    if 'name' not in columns:
        try:
            conn.execute("ALTER TABLE users ADD COLUMN name TEXT")
            conn.commit()
        except Exception:
            pass
    
    if 'email' not in columns:
        try:
            conn.execute("ALTER TABLE users ADD COLUMN email TEXT")
            conn.commit()
        except Exception:
            pass
    
    if 'phone_number' not in columns:
        try:
            conn.execute("ALTER TABLE users ADD COLUMN phone_number TEXT")
            conn.commit()
        except Exception:
            pass
    
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS resumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            filename TEXT,
            score REAL,
            details TEXT,
            created_at TEXT,
            final_score REAL,
            selection_status TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )
    
    # Add new columns if they don't exist
    cursor = conn.execute("PRAGMA table_info(resumes)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'final_score' not in columns:
        try:
            conn.execute("ALTER TABLE resumes ADD COLUMN final_score REAL")
            conn.commit()
        except Exception:
            pass
    
    if 'selection_status' not in columns:
        try:
            conn.execute("ALTER TABLE resumes ADD COLUMN selection_status TEXT DEFAULT 'pending'")
            conn.commit()
        except Exception:
            pass
    
    conn.commit()