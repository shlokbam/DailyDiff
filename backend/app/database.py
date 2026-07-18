import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.config import DB_PATH, HISTORY_FILE_PATH

def init_db():
    """Initialize the SQLite subscribers database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def add_subscriber(email: str) -> bool:
    """Add a new subscriber. Returns True if successful, False if already exists."""
    email_clean = email.strip().lower()
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO subscribers (email) VALUES (?)", (email_clean,))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def remove_subscriber(email: str) -> bool:
    """Remove a subscriber. Returns True if found and removed."""
    email_clean = email.strip().lower()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM subscribers WHERE email = ?", (email_clean,))
    rows_affected = cursor.rowcount
    conn.commit()
    conn.close()
    return rows_affected > 0

def get_subscribers() -> List[str]:
    """Retrieve all active subscriber email addresses."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM subscribers")
    emails = [row[0] for row in cursor.fetchall()]
    conn.close()
    return emails

# Git-Based Memory (history.json) Management

def init_history_file():
    """Ensure history.json exists and is initialized as an empty list."""
    if not HISTORY_FILE_PATH.exists():
        HISTORY_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(HISTORY_FILE_PATH, "w") as f:
            json.dump([], f, indent=2)

def read_history() -> List[Dict[str, Any]]:
    """Read all historical briefs."""
    init_history_file()
    try:
        with open(HISTORY_FILE_PATH, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def save_history(history_data: List[Dict[str, Any]]):
    """Overwrite the history file with updated records."""
    HISTORY_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE_PATH, "w") as f:
        json.dump(history_data, f, indent=2)

def append_to_history(briefs: List[Dict[str, Any]], date_str: str) -> Dict[str, Any]:
    """
    Append a new list of daily briefs to the history index.
    A daily brief record represents a group of briefs for a single day.
    """
    history = read_history()
    
    # Check if we already have a record for this date
    existing_index = next((i for i, item in enumerate(history) if item.get("date") == date_str), None)
    
    new_entry = {
        "date": date_str,
        "published_at": datetime.utcnow().isoformat() + "Z",
        "briefs": briefs
    }
    
    if existing_index is not None:
        history[existing_index] = new_entry
    else:
        history.append(new_entry)
        
    save_history(history)
    return new_entry
