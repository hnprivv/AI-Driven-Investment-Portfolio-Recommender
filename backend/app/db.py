import os
from functools import lru_cache

from dotenv import load_dotenv
from pymongo import MongoClient

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(ROOT, ".env"))


@lru_cache
def get_db():
    uri = os.getenv("MONGODB_URI")
    if not uri:
        raise RuntimeError("MONGODB_URI not found in .env")
    client = MongoClient(uri)
    db = client["aiprs"]
    # "name" is a free-text display field and is NOT unique — two users can
    # share a name. "email" is the only real identity key, so it's the only
    # field with a DB-level uniqueness guarantee (previously enforced only by
    # an app-level check-before-insert, which is racy and doesn't protect
    # reads/updates/deletes at all).
    db["users"].create_index("email", unique=True)
    return db


def get_user_by_name(name: str) -> dict | None:
    """Display-only lookup — "name" is NOT unique, never use this to resolve
    the identity of an authenticated session. Use get_user_by_email instead."""
    return get_db()["users"].find_one({"name": name})


def get_user_by_email(email: str) -> dict | None:
    return get_db()["users"].find_one({"email": email.strip().lower()})


def get_all_users() -> list[dict]:
    return list(get_db()["users"].find({}))


def update_user(email: str, updates: dict) -> bool:
    result = get_db()["users"].update_one({"email": email.strip().lower()}, {"$set": updates})
    return result.matched_count > 0


def delete_user(email: str) -> bool:
    result = get_db()["users"].delete_one({"email": email.strip().lower()})
    return result.deleted_count > 0
