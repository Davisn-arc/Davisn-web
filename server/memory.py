
import os
import sqlite3
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE = DATA_DIR / "davisn_memory.db"


@contextmanager
def get_connection():
    if DATABASE_URL:
        import psycopg
        from psycopg.rows import dict_row

        connection = psycopg.connect(
            DATABASE_URL,
            row_factory=dict_row
        )
    else:
        connection = sqlite3.connect(DATABASE)
        connection.row_factory = sqlite3.Row

    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def placeholder():
    return "%s" if DATABASE_URL else "?"


def initialize_memory():
    with get_connection() as connection:
        if DATABASE_URL:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id BIGSERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)

            connection.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id BIGSERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT 'general',
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    UNIQUE(user_id, key)
                )
            """)
        else:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)

            connection.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT 'general',
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    UNIQUE(user_id, key)
                )
            """)


def save_message(user_id, role, message):
    if not message:
        return

    p = placeholder()

    with get_connection() as connection:
        connection.execute(f"""
            INSERT INTO conversations
            (user_id, role, message, timestamp)
            VALUES ({p}, {p}, {p}, {p})
        """, (user_id, role, str(message), datetime.now().isoformat()))


def get_history(user_id, limit=30):
    p = placeholder()

    with get_connection() as connection:
        rows = connection.execute(f"""
            SELECT role, message, timestamp
            FROM conversations
            WHERE user_id = {p}
            ORDER BY id DESC
            LIMIT {p}
        """, (user_id, limit)).fetchall()

    return [
        {
            "role": row["role"],
            "message": row["message"],
            "content": row["message"],
            "timestamp": row["timestamp"]
        }
        for row in reversed(rows)
    ]


def save_memory(user_id, key, value, category="general"):
    if not key or not value:
        return False

    p = placeholder()

    with get_connection() as connection:
        connection.execute(f"""
            INSERT INTO memories
            (user_id, category, key, value, timestamp)
            VALUES ({p}, {p}, {p}, {p}, {p})
            ON CONFLICT(user_id, key)
            DO UPDATE SET
                category = excluded.category,
                value = excluded.value,
                timestamp = excluded.timestamp
        """, (
            user_id,
            category,
            key,
            str(value),
            datetime.now().isoformat()
        ))

    return True


def get_memories(user_id, limit=50):
    p = placeholder()

    with get_connection() as connection:
        rows = connection.execute(f"""
            SELECT category, key, value, timestamp
            FROM memories
            WHERE user_id = {p}
            ORDER BY id DESC
            LIMIT {p}
        """, (user_id, limit)).fetchall()

    return [dict(row) for row in rows]


def build_memory_context(user_id, limit=50):
    memories = get_memories(user_id, limit)

    return "\n".join(
        f"- {item['key']}: {item['value']}"
        for item in memories
    )


def remember_from_message(user_id, message):
    text = str(message or "").strip()
    lower = text.lower()

    rules = [
        ("remember that ", "fact", "fact"),
        ("remember ", "fact", "fact"),
        ("my name is ", "personal", "name"),
        ("i like ", "preference", "likes"),
        ("i love ", "preference", "loves"),
        ("i prefer ", "preference", "preference"),
        ("i'm working on ", "project", "current_project"),
        ("i am working on ", "project", "current_project")
    ]

    for prefix, category, key_prefix in rules:
        if lower.startswith(prefix):
            value = text[len(prefix):].strip()

            if not value:
                return []

            key = (
                key_prefix if key_prefix in
                ("name", "current_project")
                else f"{key_prefix}:{value[:80].lower()}"
            )

            save_memory(user_id, key, value, category)
            return [value]

    return []


def clear_memory(user_id):
    p = placeholder()

    with get_connection() as connection:
        connection.execute(
            f"DELETE FROM conversations WHERE user_id = {p}",
            (user_id,)
        )

        connection.execute(
            f"DELETE FROM memories WHERE user_id = {p}",
            (user_id,)
        )


def memory_count(user_id):
    p = placeholder()

    with get_connection() as connection:
        conversations = connection.execute(
            f"SELECT COUNT(*) AS count FROM conversations WHERE user_id = {p}",
            (user_id,)
        ).fetchone()["count"]

        memories = connection.execute(
            f"SELECT COUNT(*) AS count FROM memories WHERE user_id = {p}",
            (user_id,)
        ).fetchone()["count"]

    return {
        "conversations": conversations,
        "memories": memories,
        "total": conversations + memories
    }


initialize_memory()
