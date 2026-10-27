"""Persistent redeem codes that award one random character of a chosen rarity."""
import json
import os
import threading
import time

from config import DATA_DIR

REDEEM_CODES_FILE = os.path.join(DATA_DIR, "redeem_codes.json")
_lock = threading.RLock()
_codes = {}


def _normalize(code):
    return "".join(str(code or "").strip().split()).upper()


def load_codes():
    global _codes
    try:
        with open(REDEEM_CODES_FILE, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        _codes = data if isinstance(data, dict) else {}
    except FileNotFoundError:
        _codes = {}
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[redeem codes] load failed: {exc}")
        _codes = {}
    return _codes


def save_codes():
    os.makedirs(DATA_DIR, exist_ok=True)
    temporary = REDEEM_CODES_FILE + ".tmp"
    with _lock:
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(_codes, handle, indent=2, ensure_ascii=False)
        os.replace(temporary, REDEEM_CODES_FILE)
    return True


def create_code(code, rarity, max_uses=0, creator_id=None):
    key = _normalize(code)
    rarity = " ".join(str(rarity or "").strip().upper().split())
    if not key or not rarity:
        return False, "A code and character rarity are required."
    try:
        max_uses = max(0, int(max_uses))
    except (TypeError, ValueError):
        return False, "The use limit must be a whole number."
    with _lock:
        if key in _codes:
            return False, "That redeem code already exists."
        _codes[key] = {
            "rarity": rarity,
            "max_uses": max_uses,
            "used_by": [],
            "created_at": time.time(),
            "created_by": creator_id,
        }
        save_codes()
    return True, key


def delete_code(code):
    key = _normalize(code)
    with _lock:
        removed = _codes.pop(key, None)
        if removed is not None:
            save_codes()
        return removed


def list_codes():
    with _lock:
        return {key: dict(value) for key, value in _codes.items()}


def get_code(code):
    with _lock:
        entry = _codes.get(_normalize(code))
        return dict(entry) if entry else None


def redeem_code(code, user_id):
    key = _normalize(code)
    uid = int(user_id)
    with _lock:
        entry = _codes.get(key)
        if not entry:
            return False, "That redeem code is invalid or has expired.", None
        used_by = entry.setdefault("used_by", [])
        if uid in used_by or str(uid) in [str(value) for value in used_by]:
            return False, "You have already redeemed that code.", None
        max_uses = int(entry.get("max_uses", 0) or 0)
        if max_uses and len(used_by) >= max_uses:
            return False, "That redeem code has already reached its use limit.", None
        used_by.append(uid)
        save_codes()
        return True, key, str(entry.get("rarity", "NORMAL"))


load_codes()
