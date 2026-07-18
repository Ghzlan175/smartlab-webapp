import sqlite3
from datetime import datetime

DB_PATH = "smartlab.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            filename TEXT,
            title TEXT,
            raw_text TEXT,
            analysis TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    # Migration: add the "title" column for databases created before this feature existed
    cur.execute("PRAGMA table_info(reports)")
    columns = [row[1] for row in cur.fetchall()]
    if "title" not in columns:
        cur.execute("ALTER TABLE reports ADD COLUMN title TEXT")
    conn.commit()
    conn.close()


def create_user(name, email, password_hash):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
        (name, email, password_hash, datetime.utcnow().isoformat()),
    )
    conn.commit()
    user_id = cur.lastrowid
    conn.close()
    return user_id


def get_user_by_email(email):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = cur.fetchone()
    conn.close()
    return row


def get_user_by_id(user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row


def save_report(user_id, filename, title, raw_text, analysis):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO reports (user_id, filename, title, raw_text, analysis, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, filename, title, raw_text, analysis, datetime.utcnow().isoformat()),
    )
    conn.commit()
    report_id = cur.lastrowid
    conn.close()
    return report_id


def get_reports_for_user(user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM reports WHERE user_id = ? ORDER BY created_at DESC", (user_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_report_by_id(report_id, user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM reports WHERE id = ? AND user_id = ?", (report_id, user_id)
    )
    row = cur.fetchone()
    conn.close()
    return row
