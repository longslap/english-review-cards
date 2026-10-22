#!/usr/bin/env python3
"""Safely merge reviewed English phrases into the one master JSON deck.

Usage:
  python tools/merge_learning.py additions.json
  python tools/merge_learning.py additions.json --apply

additions.json: [{"en":"...", "zh":"...", "scene":"租房",
                   "kind":"句子", "notes":"", "practice_date":"2026-10-22"}]
Dry-run by default. Commit the resulting deck to GitHub separately.
"""
import argparse
import hashlib
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DECK = Path(__file__).resolve().parents[1] / "English_Learning_Database.json"

def normalized(value):
    value = unicodedata.normalize("NFKC", value).lower()
    value = value.replace("’", "'").replace("‘", "'").replace("–", "-").replace("—", "-")
    value = re.sub(r"[^\w\s'\-]", "", value, flags=re.UNICODE)
    return " ".join(value.split())

def main():
    p = argparse.ArgumentParser()
    p.add_argument("additions", type=Path)
    p.add_argument("--deck", type=Path, default=DEFAULT_DECK)
    p.add_argument("--apply", action="store_true", help="Write after validation (default: preview only)")
    args = p.parse_args()
    raw = args.deck.read_text(encoding="utf-8")
    deck = json.loads(raw)
    additions = json.loads(args.additions.read_text(encoding="utf-8"))
    if deck.get("deck_id") != "mark-english-master" or not isinstance(deck.get("entries"), list):
        p.error("Unexpected master database")
    if not isinstance(additions, list):
        p.error("Expected JSON array of reviewed additions")
    seen = {normalized(e["en"]) for e in deck["entries"]}
    known_ids = {e["id"] for e in deck["entries"]}
    new = []
    skipped = []
    timestamp = datetime.now(timezone.utc).isoformat()
    next_revision = deck["revision"] + 1
    for i, item in enumerate(additions, 1):
        if not isinstance(item, dict):
            p.error(f"Item {i} is not an object")
        en, zh = str(item.get("en", "")).strip(), str(item.get("zh", "")).strip()
        scene, kind = str(item.get("scene", "")).strip(), item.get("kind", "句子")
        if not en or not zh or not scene or kind not in ("句子", "单词", "短语"):
            p.error(f"Item {i} missing valid en/zh/scene/kind")
        day = item.get("practice_date", "")
        if day:
            try:
                if datetime.strptime(day, "%Y-%m-%d").strftime("%Y-%m-%d") != day:
                    raise ValueError()
            except ValueError:
                p.error(f"Item {i}: bad practice_date")
        key = normalized(en)
        if not key:
            p.error(f"Item {i}: empty normalized English")
        if key in seen:
            skipped.append(en)
            continue
        uid = "en_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
        if uid in known_ids:
            p.error(f"ID collision at item {i}")
        seen.add(key)
        known_ids.add(uid)
        new.append({
            "id": uid, "en": en, "zh": zh, "scene": scene, "kind": kind,
            "notes": str(item.get("notes", "")), "practice_dates": [day] if day else [],
            "source_claimed_dates": [], "evidence": "new_learning_conversation",
            "sources": [], "created_at": timestamp, "updated_at": timestamp,
            "revision": next_revision, "status": "active"
        })
    print(f"Existing={len(deck['entries'])}; to_add={len(new)}; duplicates_skipped={len(skipped)}")
    for e in new:
        print("ADD", e["scene"], e["en"], "=>", e["zh"])
    for e in skipped:
        print("SKIP duplicate", e)
    if not args.apply or not new:
        print("No file modified" if not args.apply else "No changes needed")
        return
    deck["entries"].extend(new)
    deck["revision"] = next_revision
    deck["updated_at"] = timestamp
    deck.setdefault("events", []).append({
        "type": "reviewed_additions", "at": timestamp,
        "detail": f"Added {len(new)} reviewed items; skipped {len(skipped)} duplicates."
    })
    args.deck.write_text(json.dumps(deck, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(deck['entries'])} entries at revision {next_revision}")

if __name__ == "__main__":
    main()
