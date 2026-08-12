# -*- coding: utf-8 -*-
"""建立 SQLite 資料庫與資料表"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "sportmeet.db"


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS students (
        student_id   TEXT PRIMARY KEY,
        name         TEXT NOT NULL,
        grade        INTEGER NOT NULL,
        class_no     INTEGER NOT NULL,
        seat_no      INTEGER,
        gender       TEXT CHECK(gender IN ('M','F')) NOT NULL,
        bib_number   TEXT UNIQUE
    );

    CREATE TABLE IF NOT EXISTS events (
        event_id     INTEGER PRIMARY KEY AUTOINCREMENT,
        code         TEXT UNIQUE NOT NULL,
        name         TEXT NOT NULL,
        category     TEXT CHECK(category IN ('track','field','relay','ball')) NOT NULL,
        gender       TEXT CHECK(gender IN ('M','F','MIX')) NOT NULL,
        grade_limit  TEXT,
        record_value REAL,
        record_holder TEXT,
        record_year  INTEGER,
        unit         TEXT
    );

    CREATE TABLE IF NOT EXISTS registrations (
        reg_id       INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id   TEXT NOT NULL,
        event_id     INTEGER NOT NULL,
        team_code    TEXT,
        reg_time     TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(student_id, event_id),
        FOREIGN KEY(student_id) REFERENCES students(student_id),
        FOREIGN KEY(event_id) REFERENCES events(event_id)
    );

    CREATE TABLE IF NOT EXISTS teams (
        team_id      INTEGER PRIMARY KEY AUTOINCREMENT,
        team_code    TEXT NOT NULL,
        event_id     INTEGER NOT NULL,
        grade        INTEGER,
        class_no     INTEGER,
        captain_id   TEXT,
        UNIQUE(team_code, event_id),
        FOREIGN KEY(event_id) REFERENCES events(event_id)
    );

    CREATE TABLE IF NOT EXISTS heats (
        heat_id      INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id     INTEGER NOT NULL,
        heat_no      INTEGER NOT NULL,
        round        TEXT DEFAULT '預賽',
        FOREIGN KEY(event_id) REFERENCES events(event_id)
    );

    CREATE TABLE IF NOT EXISTS heat_assignments (
        heat_id      INTEGER NOT NULL,
        lane         INTEGER,
        student_id   TEXT,
        team_code    TEXT,
        PRIMARY KEY(heat_id, lane),
        FOREIGN KEY(heat_id) REFERENCES heats(heat_id)
    );

    CREATE TABLE IF NOT EXISTS results (
        result_id    INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id     INTEGER NOT NULL,
        student_id   TEXT,
        team_code    TEXT,
        performance  REAL,
        rank         INTEGER,
        broke_record INTEGER DEFAULT 0,
        points       REAL DEFAULT 0,
        note         TEXT,
        FOREIGN KEY(event_id) REFERENCES events(event_id)
    );

    CREATE TABLE IF NOT EXISTS ball_matches (
        match_id     INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id     INTEGER NOT NULL,
        round        TEXT,
        team_a       TEXT,
        team_b       TEXT,
        score_a      INTEGER,
        score_b      INTEGER,
        winner       TEXT,
        match_time   TEXT,
        FOREIGN KEY(event_id) REFERENCES events(event_id)
    );

    CREATE TABLE IF NOT EXISTS users (
        user_id      INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id   TEXT UNIQUE,
        username     TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role         TEXT DEFAULT 'student',
        created_at   TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(student_id) REFERENCES students(student_id)
    );
    """)

    conn.commit()
    conn.close()
    print(f"[OK] 資料庫已建立: {DB_PATH}")


if __name__ == "__main__":
    init_db()
