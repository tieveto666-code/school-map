#!/usr/bin/env python3
"""Sync baike score tables from data/baike/scores.json into schools.details.json."""

import json
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DETAILS_OUT = ROOT / "data" / "schools.details.json"
BAIKE_OUT = ROOT / "data" / "baike" / "scores.json"


def baike_url(name: str) -> str:
    return f"https://baike.baidu.com/item/{urllib.parse.quote(name)}"


def enrich_details():
    if not DETAILS_OUT.exists() or not BAIKE_OUT.exists():
        print("Missing details or baike/scores.json — run fetch_elite_scores.py first")
        return
    details = json.loads(DETAILS_OUT.read_text(encoding="utf-8"))
    baike_all = json.loads(BAIKE_OUT.read_text(encoding="utf-8"))
    updated = 0
    for code, bk in baike_all.items():
        if code not in details:
            continue
        details[code]["baikeUrl"] = bk.get("baikeUrl") or baike_url(bk.get("name", ""))
        details[code]["baikeScores"] = {
            "source": bk.get("source", "百度高考（中国教育在线）"),
            "sourceUrl": bk.get("baikeUrl") or details[code]["baikeUrl"],
            "title": bk.get("title", ""),
            "headers": bk.get("headers", []),
            "rows": bk.get("rows", []),
        }
        updated += 1
    DETAILS_OUT.write_text(json.dumps(details, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Synced baike scores for {updated} schools into schools.details.json")


if __name__ == "__main__":
    enrich_details()
