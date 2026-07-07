"""
users.py
========
Member: Warui, Aaron
Handles all direct data operations for the users table.
"""

import hashlib

from database import (
    insert_data,
    fetch_one,
    update_data
)


def hash_password(password):
    return hashlib.sha256(
        password.encode("utf-8")
    ).hexdigest()


def verify_password(password, hashed):
    return hash_password(password) == hashed


def username_exists(username):

    row = fetch_one(
        "SELECT user_id FROM users WHERE username = ?",
        (username,)
    )

    return row is not None


def create_user(username, password, role, location="", phone=""):

    if username_exists(username):
        return None

    data = {
        "username": username,
        "password": hash_password(password),
        "role": role,
        "location": location,
        "phone": phone
    }

    return insert_data(
        "users",
        data
    )


def get_user_by_username(username):

    return fetch_one(
        "SELECT * FROM users WHERE username = ?",
        (username,)
    )


def get_user_by_id(user_id):

    return fetch_one(
        "SELECT * FROM users WHERE user_id = ?",
        (user_id,)
    )


def update_user_location(user_id, new_location):

    update_data(
        "users",
        {"location": new_location},
        "user_id = ?",
        (user_id,)
    )


def update_user_phone(user_id, new_phone):

    update_data(
        "users",
        {"phone": new_phone},
        "user_id = ?",
        (user_id,)
    )