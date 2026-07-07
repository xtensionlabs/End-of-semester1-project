"""
users.py
========
Member: Warui, Aaron
Handles all direct data operations for the `users` table: creating users,
looking them up, and updating their profile. All password handling and
interactive prompts live in auth.py — this file is the data layer only.
"""

import hashlib
from database import insert_data, fetch_one, update_data


def hash_password(password):
    """Hash a password with SHA-256. Not perfectly secure, but far better
    than storing plain text, and simple enough for this project's scope."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password, hashed):
    """Check a plain-text password against a stored hash."""
    return hash_password(password) == hashed


def username_exists(username):
    """Return True if a user with this username already exists."""
    row = fetch_one("SELECT user_id FROM users WHERE username = ?", (username,))
    return row is not None


def create_user(username, password, role, location="", phone=""):
    """
    Create a new user record.
    Returns the new user_id on success, or None if the username is taken.
    """
    if username_exists(username):
        return None

    data = {
        "username": username,
        "password": hash_password(password),
        "role": role,
        "location": location,
        "phone": phone,
    }
    return insert_data("users", data)


def get_user_by_username(username):
    """Return the full user row for a username, or None if not found."""
    return fetch_one("SELECT * FROM users WHERE username = ?", (username,))


def get_user_by_id(user_id):
    """Return the full user row for a user_id, or None if not found."""
    return fetch_one("SELECT * FROM users WHERE user_id = ?", (user_id,))


def update_user_location(user_id, new_location):
    """Update a user's location field."""
    update_data("users", {"location": new_location}, {"user_id": user_id})


def update_user_phone(user_id, new_phone):
    """Update a user's phone field."""
    update_data("users", {"phone": new_phone}, {"user_id": user_id})
