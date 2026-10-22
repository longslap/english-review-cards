#!/usr/bin/env python3
"""Validate the published deck against browser-side requirements."""
import json, re, sys, unicodedata
from pathlib import Path
p=Path(sys.argv[1] if len(sys.argv)>1 else "English_Learning_Database.json")
d=json.loads(p.read_text(encoding="utf-8"))
def fail(message):
    raise ValueError(message)
if d.get("schema_version")!=1 or d.get("deck_id")!="mark-english-master": fail("Invalid schema/deck ID")
if not all(isinstance(d.get(k),list) for k in ("entries","sources","events")): fail("Missing arrays")
source_ids=[s.get("id") for s in d["sources"]]
if len(source_ids)!=len(set(source_ids)) or any(not s for s in source_ids):fail("Duplicate/empty source IDs")
seen_ids=set();seen_en=set()
def norm(s):
    return " ".join(re.sub(r"[^\w\s'-]","",unicodedata.normalize("NFKC",s).replace("’","'").replace("‘","'").replace("–","-").replace("—","-").lower()).split())
for i,c in enumerate(d["entries"]):
    if not isinstance(c,dict):fail(f"entry {i}: not object")
    for k in ("id","en","zh","scene","kind","notes","evidence","status"):
        if not isinstance(c.get(k),str):fail(f"entry {i}: invalid {k}")
    if not c["id"] or not c["en"].strip() or not c["zh"].strip():fail(f"entry {i}: empty required value")
    if c["kind"] not in ("句子","单词","短语") or c["status"] not in ("active","archived"):fail(f"entry {i}: invalid kind/status")
    if not isinstance(c.get("practice_dates"),list) or not isinstance(c.get("sources"),list):fail(f"entry {i}: invalid lists")
    if any(not isinstance(x,str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}",x) for x in c["practice_dates"]):fail(f"entry {i}: bad date")
    if any(not isinstance(x,dict) or x.get("source_id") not in source_ids for x in c["sources"]):fail(f"entry {i}: unknown source")
    key=norm(c["en"])
    if c["id"] in seen_ids or key in seen_en:fail(f"entry {i}: duplicate ID/English")
    seen_ids.add(c["id"]);seen_en.add(key)
if not d["entries"]: fail("Empty deck")
print(f"Deck validated: {len(d['entries'])} entries; {len(source_ids)} sources; revision {d.get('revision')}")
