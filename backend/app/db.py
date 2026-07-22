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
    return client["aiprs"]


def get_user_by_name(name: str) -> dict | None:
    return get_db()["users"].find_one({"name": name})


def update_user(name: str, updates: dict) -> bool:
    result = get_db()["users"].update_one({"name": name}, {"$set": updates})
    return result.matched_count > 0


def delete_user(name: str) -> bool:
    result = get_db()["users"].delete_one({"name": name})
    return result.deleted_count > 0
