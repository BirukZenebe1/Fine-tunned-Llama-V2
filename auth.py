"""
User authentication module with bcrypt password hashing and JSON-file persistence.

Stores user credentials in a local JSON file (data/users.json).
Passwords are hashed with bcrypt before storage.
"""

import json
import os
import bcrypt

USERS_FILE = os.path.join(os.path.dirname(__file__), "data", "users.json")


def _ensure_data_dir():
    """Create the data directory and users file if they don't exist."""
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            json.dump({}, f)


def _load_users():
    """Load user database from disk."""
    _ensure_data_dir()
    with open(USERS_FILE, "r") as f:
        return json.load(f)


def _save_users(users):
    """Save user database to disk."""
    _ensure_data_dir()
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)


def signup(username, password):
    """
    Register a new user.

    Returns:
        (bool, str): (success, message)
    """
    if not username or not password:
        return False, "Please provide both username and password."
    if len(username) < 3:
        return False, "Username must be at least 3 characters."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."

    users = _load_users()
    if username in users:
        return False, "Username already exists."

    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    users[username] = hashed.decode("utf-8")
    _save_users(users)
    return True, "Account created successfully. Please log in."


def login(username, password):
    """
    Authenticate a user.

    Returns:
        (bool, str): (success, message)
    """
    if not username or not password:
        return False, "Please provide both username and password."

    users = _load_users()
    if username not in users:
        return False, "Invalid credentials."

    stored_hash = users[username].encode("utf-8")
    if bcrypt.checkpw(password.encode("utf-8"), stored_hash):
        return True, f"Welcome back, {username}!"
    return False, "Invalid credentials."
