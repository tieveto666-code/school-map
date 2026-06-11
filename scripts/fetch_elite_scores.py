#!/usr/bin/env python3
"""Fetch 985/211/双一流 admission scores from Baidu Gaokao (中国教育在线)."""

from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX_FILE = ROOT / "data" / "schools.index.json"
PROVINCES_FILE = ROOT / "data" / "provinces.json"
SCORES_DIR = ROOT / "data" / "scores"
BAIKE_OUT = ROOT / "data" / "baike" / "scores.json"
DETAILS_OUT = ROOT / "data" / "schools.details.json"
CACHE_FILE = ROOT / "data" / "scores" / ".elite_fetch_cache.json"

API_URL = "https://gaokao.baidu.com/gk/gkschool/schoolscore"
SOURCE_NAME = "百度高考（中国教育在线）"
SOURCE_BASE = "https://gaokao.baidu.com/okam/pages/schoolhome/index"
YEARS = (2023, 2024, 2025)

EXCLUDE_BATCH = ("艺术", "体育", "专项", "提前", "单招", "高水平")
REGULAR_BATCH = ("本科批", "普通类一段", "普通类", "本科一批", "本一", "一段", "二段")

ALIASES_FILE = ROOT / "data" / "raw" / "name_aliases.json"
ALIASES_SAMPLE = ROOT / "data" / "raw" / "name_aliases.sample.json"
_name_aliases_cache: dict | None = None


def load_name_aliases() -> dict:
    global _name_aliases_cache
    if _name_aliases_cache is not None:
        return _name_aliases_cache
    path = ALIASES_FILE if ALIASES_FILE.exists() else ALIASES_SAMPLE
    if not path.exists():
        _name_aliases_cache = {}
        return _name_aliases_cache
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    _name_aliases_cache = {k: v for k, v in data.items() if not k.startswith("_")}
    return _name_aliases_cache


def load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def elite_schools():
    schools = load_json(INDEX_FILE)["schools"]
    return [s for s in schools if s["t"] in ("985", "211", "双一流")]


def api_school_name(name: str) -> str:
    return load_name_aliases().get(name, name)


def is_regular_batch(batch_name: str) -> bool:
    if not batch_name:
        return True
    if any(k in batch_name for k in EXCLUDE_BATCH):
        return False
    if any(k in batch_name for k in REGULAR_BATCH):
        return True
    return "本科" in batch_name and "提前" not in batch_name


def parse_int(value) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text == "-":
        return None
    m = re.search(r"\d+", text)
    return int(m.group()) if m else None


def pick_record(rows: list[dict]) -> dict | None:
    if not rows:
        return None
    regular = [r for r in rows if is_regular_batch(r.get("batchName", ""))]
    pool = regular or rows
    best = None
    best_score = 10**9
    for row in pool:
        score = parse_int(row.get("minScore"))
        if score is None:
            continue
        if score < best_score:
            best_score = score
            best = row
    return best


def fetch_score(school_name: str, province_short: str, year: int, retries: int = 3) -> dict | None:
    params = urllib.parse.urlencode({
        "school": api_school_name(school_name),
        "province": province_short,
        "year": str(year),
    })
    req = urllib.request.Request(
        f"{API_URL}?{params}",
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
    )
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                payload = json.load(resp)
            block = payload.get("data", {}).get("school_score", {})
            rows = block.get("dataList") or []
            record = pick_record(rows)
            if not record:
                return None
            options = block.get("options") or []
            track = options[2]["text"] if len(options) >= 3 else ""
            return {
                "record": record,
                "subjectTrack": track,
                "sourceUrl": block.get("h5Url") or f"{SOURCE_BASE}?word={urllib.parse.quote(school_name)}&tab=score",
            }
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            if attempt + 1 >= retries:
                return None
            time.sleep(0.8 * (attempt + 1))
    return None


def cache_key(school_code: str, prov_code: str, year: int) -> str:
    return f"{school_code}|{prov_code}|{year}"


def load_cache() -> dict:
    if CACHE_FILE.exists():
        return load_json(CACHE_FILE)
    return {}


def save_cache(cache: dict):
    save_json(CACHE_FILE, cache)


def build_records(result, school, prov, year):
    row = result["record"]
    score = parse_int(row.get("minScore"))
    if score is None:
        return None
    rank = parse_int(row.get("minScoreOrder"))
    batch = row.get("batchName") or row.get("enrollType") or "本科批"
    major = row.get("simplifySpecialCourse") or row.get("majorGroup") or ""
    return {
        "schoolCode": school["c"],
        "schoolName": school["n"],
        "minScore": score,
        "minRank": rank or 0,
        "batch": batch,
        "majorGroup": major,
        "subjectTrack": result.get("subjectTrack", ""),
        "sourceUrl": result.get("sourceUrl", ""),
    }


def merge_baike_row(baike_rows, school_name, prov_short, year, record):
    score = parse_int(record.get("minScore"))
    rank = parse_int(record.get("minScoreOrder"))
    batch = record.get("batchName") or "本科批"
    major = record.get("simplifySpecialCourse") or record.get("majorGroup") or ""
    score_rank = f"{score}/{rank}" if rank else str(score)
    row = [str(year), prov_short, batch, score_rank, major]
    key = tuple(row)
    if key not in baike_rows:
        baike_rows[key] = row


def enrich_details(baike_all: dict):
    if not DETAILS_OUT.exists():
        return
    details = load_json(DETAILS_OUT)
    for code, bk in baike_all.items():
        if code not in details:
            continue
        details[code]["baikeUrl"] = bk["baikeUrl"]
        details[code]["baikeScores"] = {
            "source": SOURCE_NAME,
            "sourceUrl": bk["baikeUrl"],
            "title": bk["title"],
            "headers": bk["headers"],
            "rows": bk["rows"],
        }
    with open(DETAILS_OUT, "w", encoding="utf-8") as f:
        json.dump(details, f, ensure_ascii=False, separators=(",", ":"))


def write_outputs(province_records: dict, baike_by_school: dict, provinces: list):
    today = date.today().isoformat()
    index = {"provinces": {}}

    for prov in provinces:
        code = prov["code"]
        name = prov["name"]
        short = prov["shortName"]
        prov_dir = SCORES_DIR / code
        prov_dir.mkdir(parents=True, exist_ok=True)
        years_written = []

        for year in YEARS:
            records = province_records.get((code, year), [])
            if not records:
                continue
            tracks = sorted({r.get("subjectTrack", "") for r in records if r.get("subjectTrack")})
            clean_records = []
            for r in records:
                item = {k: v for k, v in r.items() if k != "subjectTrack"}
                clean_records.append(item)
            track_label = tracks[0] if len(tracks) == 1 else " / ".join(tracks) if tracks else "物理类/综合改革"
            payload = {
                "province": name,
                "year": year,
                "subjectTrack": track_label,
                "sourceUrl": f"https://gaokao.baidu.com/",
                "sourceDate": today,
                "source": SOURCE_NAME,
                "records": sorted(clean_records, key=lambda x: (-x["minScore"], x["schoolName"])),
            }
            save_json(prov_dir / f"{year}.json", payload)
            years_written.append(year)

        index["provinces"][code] = {
            "years": sorted(set(years_written), reverse=True),
            "subjectTracks": [],
            "hasData": bool(years_written),
            "eliteOnly": True,
            "note": "含全部985/211/双一流院校，来源百度高考",
        }

    save_json(SCORES_DIR / "index.json", index)

    baike_all = {}
    for school in elite_schools():
        code = school["c"]
        rows_map = baike_by_school.get(code, {})
        rows = sorted(rows_map.values(), key=lambda r: (-int(r[0]), r[1]))
        if not rows:
            continue
        baike_all[code] = {
            "name": school["n"],
            "baikeUrl": f"https://baike.baidu.com/item/{urllib.parse.quote(school['n'])}",
            "title": f"{school['n']}历年录取分数线",
            "headers": ["年份", "招生省份", "批次", "最低分/最低位次", "专业组"],
            "rows": rows[:120],
            "source": SOURCE_NAME,
        }

    save_json(BAIKE_OUT, baike_all)
    enrich_details(baike_all)


def run(delay: float, limit_provinces: list[str] | None, limit_schools: int | None, use_cache: bool):
    schools = elite_schools()
    if limit_schools:
        schools = schools[:limit_schools]
    provinces = load_json(PROVINCES_FILE)
    if limit_provinces:
        provinces = [p for p in provinces if p["code"] in limit_provinces or p["shortName"] in limit_provinces]

    cache = load_cache() if use_cache else {}
    province_records: dict[tuple[str, int], list] = defaultdict(list)
    baike_by_school: dict[str, dict] = defaultdict(dict)

    total = len(schools) * len(provinces) * len(YEARS)
    done = 0
    hits = 0
    misses = 0

    for prov in provinces:
        for year in YEARS:
            for school in schools:
                done += 1
                key = cache_key(school["c"], prov["code"], year)
                if use_cache and key in cache:
                    cached = cache[key]
                    if cached:
                        rec = dict(cached)
                        province_records[(prov["code"], year)].append(rec)
                        merge_baike_row(
                            baike_by_school[school["c"]],
                            school["n"],
                            prov["shortName"],
                            year,
                            {
                                "minScore": rec["minScore"],
                                "minScoreOrder": rec["minRank"],
                                "batchName": rec["batch"],
                                "simplifySpecialCourse": rec.get("majorGroup", ""),
                            },
                        )
                        hits += 1
                    else:
                        misses += 1
                    continue

                result = fetch_score(school["n"], prov["shortName"], year)
                if result:
                    rec = build_records(result, school, prov, year)
                    if rec:
                        province_records[(prov["code"], year)].append(dict(rec))
                        merge_baike_row(
                            baike_by_school[school["c"]],
                            school["n"],
                            prov["shortName"],
                            year,
                            result["record"],
                        )
                        cache[key] = rec
                        hits += 1
                    else:
                        cache[key] = None
                        misses += 1
                else:
                    cache[key] = None
                    misses += 1

                if done % 50 == 0:
                    save_cache(cache)
                    print(f"[{done}/{total}] hits={hits} misses={misses} latest={school['n']}@{prov['shortName']} {year}")
                time.sleep(delay)

    save_cache(cache)
    write_outputs(province_records, baike_by_school, provinces)
    schools_with_baike = sum(1 for s in elite_schools() if s["c"] in baike_by_school and baike_by_school[s["c"]])
    print(f"Done. API hits={hits}, misses={misses}, schools with scores={schools_with_baike}/{len(elite_schools())}")


def main():
    parser = argparse.ArgumentParser(description="Fetch 985/211/双一流 scores from Baidu Gaokao")
    parser.add_argument("--delay", type=float, default=0.12, help="Delay between requests (seconds)")
    parser.add_argument("--province", action="append", help="Limit to province code/short name (repeatable)")
    parser.add_argument("--limit-schools", type=int, help="Only fetch first N elite schools (debug)")
    parser.add_argument("--no-cache", action="store_true", help="Ignore fetch cache")
    args = parser.parse_args()
    run(args.delay, args.province, args.limit_schools, use_cache=not args.no_cache)


if __name__ == "__main__":
    main()
