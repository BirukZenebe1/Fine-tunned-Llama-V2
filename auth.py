"""
User authentication module with bcrypt password hashing.

Storage backend:
- MongoDB when MONGO_URI env var is set (recommended for deployment)
- Local JSON file (data/users.json) as fallback for local development
"""

import json
import os
import bcrypt

USERS_FILE = os.path.join(os.path.dirname(__file__), "data", "users.json")

# ---------------------------------------------------------------------------
# MongoDB backend
# ---------------------------------------------------------------------------
_mongo_collection = None


def _get_mongo_collection():
    global _mongo_collection
    if _mongo_collection is not None:
        return _mongo_collection

    mongo_uri = os.environ.get("MONGO_URI")
    if not mongo_uri:
        return None

    from pymongo import MongoClient

    client = MongoClient(mongo_uri)
    db = client.get_default_database()
    _mongo_collection = db["users"]
    _mongo_collection.create_index("username", unique=True)
    return _mongo_collection


def _use_mongo():
    return _get_mongo_collection() is not None


# ---------------------------------------------------------------------------
# JSON file backend (fallback)
# ---------------------------------------------------------------------------
def _ensure_data_dir():
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            json.dump({}, f)


def _load_users():
    _ensure_data_dir()
    with open(USERS_FILE, "r") as f:
        return json.load(f)


def _save_users(users):
    _ensure_data_dir()
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
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

    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    col = _get_mongo_collection()
    if col is not None:
        if col.find_one({"username": username}):
            return False, "Username already exists."
        col.insert_one({"username": username, "password_hash": hashed})
        return True, "Account created successfully. Please log in."

    # JSON fallback
    users = _load_users()
    if username in users:
        return False, "Username already exists."
    users[username] = hashed
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

    col = _get_mongo_collection()
    if col is not None:
        doc = col.find_one({"username": username})
        if not doc:
            return False, "Invalid credentials."
        stored_hash = doc["password_hash"].encode("utf-8")
    else:
        users = _load_users()
        if username not in users:
            return False, "Invalid credentials."
        stored_hash = users[username].encode("utf-8")

    if bcrypt.checkpw(password.encode("utf-8"), stored_hash):
        return True, f"Welcome back, {username}!"
    return False, "Invalid credentials."
