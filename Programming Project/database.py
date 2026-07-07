"""
database.py — TEMPORARY STUB
=============================
This is a placeholder implementation of the database interface that
David (Member 1) is responsible for building. It exists ONLY so that
Aaron's auth.py / users.py can be developed and tested independently.

Once David delivers the real database.py + schema.sql, DELETE this file
and replace it with his version. As long as his functions have the same
names and signatures, auth.py and users.py will keep working with zero
changes.

Expected interface (per project spec):
    init_db()
    get_db_connection()
    insert_data(table, data_dict)
    fetch_one(query, params)
    fetch_all(query, params)
    update_data(table, updates, condition)
    delete_data(table, condition)
"""

import sqlite3

DB_NAME = "market.db"


def get_db_connection():
    """Return a connection to market.db with row access by column name."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create the database and tables if they don't already exist."""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT UNIQUE NOT NULL,
            password    TEXT NOT NULL,
            role        TEXT NOT NULL CHECK(role IN ('Farmer', 'Buyer', 'Admin')),
            location    TEXT,
            phone       TEXT,
            date_joined TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Minimal placeholders for other tables so foreign keys don't break
    # other members' modules during integration testing.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS listings (
            listing_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            farmer_id    INTEGER,
            crop_name    TEXT,
            quantity_kg  REAL,
            min_price    REAL,
            location     TEXT,
            harvest_date TEXT,
            status       TEXT DEFAULT 'Available',
            FOREIGN KEY (farmer_id) REFERENCES users(user_id)
        )
    """)

    conn.commit()
    conn.close()


def insert_data(table, data_dict):
    """Insert a row into `table` from a dict of column: value. Returns new row id."""
    conn = get_db_connection()
    cur = conn.cursor()

    columns = ", ".join(data_dict.keys())
    placeholders = ", ".join("?" for _ in data_dict)
    values = tuple(data_dict.values())

    cur.execute(
        f"INSERT INTO {table} ({columns}) VALUES ({placeholders})",
        values
    )

    conn.commit()
    new_id = cur.lastrowid
    conn.close()

    return new_id


def fetch_one(query, params=()):
    """Run a SELECT and return a single row (or None)."""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(query, params)
    row = cur.fetchone()

    conn.close()
    return row


def fetch_all(query, params=()):
    """Run a SELECT and return all matching rows as a list."""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(query, params)
    rows = cur.fetchall()

    conn.close()
    return rows


def update_data(table, updates, condition, condition_params=()):
    """
    Update rows in `table`.
    Example:
        update_data(
            "users",
            {"username": "John"},
            "user_id = ?",
            (1,)
        )
    """
    conn = get_db_connection()
    cur = conn.cursor()

    set_clause = ", ".join(f"{column} = ?" for column in updates.keys())
    values = tuple(updates.values()) + tuple(condition_params)

    cur.execute(
        f"UPDATE {table} SET {set_clause} WHERE {condition}",
        values
    )

    conn.commit()
    conn.close()


def delete_data(table, condition, condition_params=()):
    """
    Delete rows from a table.
    Example:
        delete_data("users", "user_id = ?", (1,))
    """
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        f"DELETE FROM {table} WHERE {condition}",
        condition_params
    )

    conn.commit()
    conn.close()