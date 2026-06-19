# -----------------------------------------------------------------------------
# Conversation and chat persistence layer.
# This module stores temporary session history and long-term chat threads in
# SQLite so the server can retrieve them across requests.
# -----------------------------------------------------------------------------

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "database.db"
CHINA_TZ = timezone(timedelta(hours=8))

# The memory module stores two kinds of data:
# 1. Temporary session history for quick browser chats.
# 2. Persistent chat threads and message history for logged-in users.
#
# This is a useful learning example because it shows how a simple web app can
# keep chat context even after the browser sends new requests. The data is
# stored in SQLite files, which makes it easy to read and debug.


def get_china_timestamp() -> str:
    """Return the current time in China's UTC+8 time zone."""
    return datetime.now(CHINA_TZ).astimezone(CHINA_TZ).isoformat(timespec="seconds")


def init_db():
    """Create the SQLite tables used for temporary session memory and chat threads.

    The schema contains three tables:
    - conversations: stores temporary session-based chat messages
    - chats: stores each user-owned chat thread and its title
    - messages: stores the full text of each saved chat conversation

    Think of this as the project’s small database layer.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            session_id TEXT,
            role TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL DEFAULT 'New Chat',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            mode TEXT DEFAULT 'normal',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    
    # Add mode column to existing messages table if it doesn't exist
    try:
        cursor.execute("ALTER TABLE messages ADD COLUMN mode TEXT DEFAULT 'normal'")
    except sqlite3.OperationalError:
        # Column already exists
        pass
    
    conn.commit()
    conn.close()


def add_message(session_id: str, role: str, content: str):
    """Store a single message in the temporary session conversation table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO conversations (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
        (session_id, role, content, get_china_timestamp()),
    )
    conn.commit()
    conn.close()


def get_conversation(session_id: str) -> list:
    """Return all messages for a session in the order they were created."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, content FROM conversations WHERE session_id = ? ORDER BY created_at ASC",
        (session_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"role": row[0], "content": row[1]} for row in rows]


def clear_conversation(session_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM conversations WHERE session_id = ?",
        (session_id,),
    )
    conn.commit()
    conn.close()


def create_chat(user_id: int, title: str = "New Chat") -> int:
    """Create a new chat thread for a logged-in user and return its ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO chats (user_id, title, created_at) VALUES (?, ?, ?)",
        (user_id, title, get_china_timestamp()),
    )
    chat_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return chat_id


def add_chat_message(chat_id: int, role: str, content: str, mode: str = 'normal'):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (chat_id, role, content, mode, created_at) VALUES (?, ?, ?, ?, ?)",
        (chat_id, role, content, mode, get_china_timestamp()),
    )
    conn.commit()
    conn.close()


def get_chat_messages(chat_id: int) -> list:
    """Load all messages belonging to one saved chat conversation."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, content, created_at, mode FROM messages WHERE chat_id = ? ORDER BY created_at ASC, id ASC",
        (chat_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"role": row[0], "content": row[1], "created_at": row[2], "mode": row[3]} for row in rows]


def get_chats(user_id: int) -> list:
    """List all chat threads owned by the current user, newest first."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, title, created_at FROM chats WHERE user_id = ? ORDER BY created_at DESC, id DESC",
        (user_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"id": row[0], "title": row[1], "created_at": row[2]} for row in rows]


def search_chats(user_id: int, query: str) -> list:
    """Search chat titles and message content for the current user."""
    term = (query or '').strip().lower()
    if not term:
        return []

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT DISTINCT c.id, c.title, c.created_at,
               m.content AS preview
        FROM chats c
        LEFT JOIN messages m ON m.chat_id = c.id
        WHERE c.user_id = ?
          AND (
                LOWER(c.title) LIKE ?
                OR LOWER(m.content) LIKE ?
          )
        ORDER BY c.created_at DESC, c.id DESC
        """,
        (user_id, f'%{term}%', f'%{term}%'),
    )
    rows = cursor.fetchall()
    conn.close()

    results = []
    seen = set()
    for row in rows:
        chat_id = row['id']
        if chat_id in seen:
            continue
        seen.add(chat_id)

        preview = (row['preview'] or '').strip().replace('\n', ' ')
        preview = ' '.join(preview.split())
        if not preview:
            preview = 'Open this conversation to view the saved discussion.'
        results.append({
            'id': chat_id,
            'title': row['title'],
            'created_at': row['created_at'],
            'preview': preview[:140],
        })

    return results


def rename_chat(chat_id: int, title: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE chats SET title = ? WHERE id = ?",
        (title, chat_id),
    )
    conn.commit()
    conn.close()


def clear_chat_messages(chat_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
    conn.commit()
    conn.close()


def delete_chat(chat_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
    cursor.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
    conn.commit()
    conn.close()

