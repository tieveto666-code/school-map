#!/usr/bin/env python3
"""Fetch major rankings from 软科中国大学专业排名 (ShanghaiRanking BCMR)."""

from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX_FILE = ROOT / "data" / "schools.index.json"
MAJORS_DIR = ROOT / "data" / "majors"
MAJORS_INDEX = MAJORS_DIR / "index.json"
RANKINGS_DIR = MAJORS_DIR / "rankings"
CACHE_FILE = MAJORS_DIR / ".fetch_cache.json"

YEAR = 2025
SOURCE = "2025软科中国大学专业排名"
SOURCE_URL = f"https://www.shanghairanking.cn/rankings/bcmr/{YEAR}"
API_MAJOR = f"https://www.shanghairanking.cn/api/pub/v1/bcmr/major?year={YEAR}"
API_RANK = f"https://www.shanghairanking.cn/api/pub/v1/bcmr/rank?year={YEAR}&majorCode={{code}}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": SOURCE_URL,
}

TAG_PRIORITY = ("985", "211", "双一流", "一本", "二本", "其他")


def load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def fetch_url(url: str, retries: int = 3) -> dict:
    last_err = None
    for _ in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            if payload.get("code") != 200:
                raise RuntimeError(payload.get("msg") or "API error")
            return payload["data"]
        except (urllib.error.URLError, TimeoutError, RuntimeError, json.JSONDecodeError) as err:
            last_err = err
            time.sleep(0.8)
    raise RuntimeError(f"fetch failed: {url} ({last_err})")


def flatten_majors(tree: list) -> list[dict]:
    items = []

    def walk(nodes, path: list[str]):
        for node in nodes:
            current = path + [node["name"]]
            children = node.get("children") or []
            if children:
                walk(children, current)
            else:
                items.append({
                    "code": node["code"],
                    "name": node["name"],
                    "discipline": current[0] if current else "",
                    "majorClass": current[1] if len(current) > 1 else "",
                    "path": current,
                    "schoolCount": node.get("univPublished") or 0,
                    "ranked": (node.get("univPublished") or 0) >= 4,
                })

    walk(tree, [])
    return items


def build_school_type_map() -> dict[str, str]:
    schools = load_json(INDEX_FILE)["schools"]
    mapping = {}
    for s in schools:
        t = s["t"]
        if t == "普通一本":
            mapping[s["n"]] = "一本"
        elif t == "普通二本":
            mapping[s["n"]] = "二本"
        elif t == "其他":
            mapping[s["n"]] = "其他"
        else:
            mapping[s["n"]] = t
    return mapping


def normalize_name(name: str) -> str:
    return re.sub(r"\s+", "", name)


def resolve_tag(name: str, api_tags: list[str] | None, type_map: dict[str, str]) -> str:
    tags = set(api_tags or [])
    local = type_map.get(name) or type_map.get(normalize_name(name))
    if local:
        tags.add(local)
    for tag in TAG_PRIORITY:
        if tag in tags:
            return tag
    return "其他"


def build_ranking_file(major: dict, rank_data: dict, type_map: dict[str, str]) -> dict:
    records = []
    for item in rank_data.get("rankings") or []:
        rank_text = str(item.get("ranking") or "").strip()
        if not rank_text or rank_text == "-":
            continue
        try:
            rank = int(re.search(r"\d+", rank_text).group())
        except (AttributeError, ValueError):
            continue
        name = item.get("univNameCn") or ""
        records.append({
            "rank": rank,
            "schoolName": name,
            "province": item.get("province") or "",
            "score": item.get("score"),
            "grade": item.get("grade") or "",
            "tag": resolve_tag(name, item.get("univTags"), type_map),
        })
    records.sort(key=lambda r: r["rank"])
    return {
        "majorCode": major["code"],
        "majorName": major["name"],
        "discipline": major["discipline"],
        "majorClass": major["majorClass"],
        "year": YEAR,
        "source": SOURCE,
        "sourceUrl": SOURCE_URL,
        "records": records,
    }


def run(delay: float, limit: int | None, use_cache: bool):
    type_map = build_school_type_map()
    tree = fetch_url(API_MAJOR)
    majors = flatten_majors(tree)
    ranked_all = [m for m in majors if m["ranked"]]
    ranked = ranked_all[:limit] if limit else ranked_all

    cache = load_json(CACHE_FILE) if use_cache and CACHE_FILE.exists() else {}
    done = 0
    hits = 0

    for major in ranked:
        code = major["code"]
        out_path = RANKINGS_DIR / f"{code}.json"
        if use_cache and cache.get(code) == "ok" and out_path.exists():
            hits += 1
            done += 1
            continue

        data = fetch_url(API_RANK.format(code=urllib.parse.quote(code)))
        payload = build_ranking_file(major, data, type_map)
        save_json(out_path, payload)
        cache[code] = "ok"
        done += 1
        if done % 20 == 0:
            save_json(CACHE_FILE, cache)
            print(f"  fetched {done}/{len(ranked)} majors...")
        time.sleep(delay)

    save_json(CACHE_FILE, cache)
    save_json(MAJORS_INDEX, {
        "meta": {
            "year": YEAR,
            "source": SOURCE,
            "sourceUrl": SOURCE_URL,
            "totalMajors": len(majors),
            "rankedMajors": len(ranked_all),
            "updatedAt": time.strftime("%Y-%m-%d"),
        },
        "majors": majors,
    })
    print(f"Done: {len(ranked)} ranked majors ({hits} cached), index has {len(majors)} majors")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--delay", type=float, default=0.25, help="seconds between rank requests")
    parser.add_argument("--limit", type=int, default=None, help="limit majors for testing")
    parser.add_argument("--no-cache", action="store_true")
    args = parser.parse_args()
    run(args.delay, args.limit, not args.no_cache)
