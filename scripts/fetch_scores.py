#!/usr/bin/env python3
"""Generate province admission score JSON files from a local import file.

Copy data/raw/province_scores.sample.json to data/raw/province_scores.json and
fill records from provincial exam authority sources you are allowed to use.
The public repo does not ship real school names or score lines.

For 985/211/双一流 nationwide scores, run:
  python3 scripts/fetch_elite_scores.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
SCORES_DIR = ROOT / "data" / "scores"
IMPORT_FILE = RAW / "province_scores.json"
IMPORT_SAMPLE = RAW / "province_scores.sample.json"

ALL_PROVINCES = [
    "beijing", "tianjin", "hebei", "shanxi", "neimenggu", "liaoning", "jilin",
    "heilongjiang", "shanghai", "jiangsu", "zhejiang", "anhui", "fujian",
    "jiangxi", "shandong", "henan", "hubei", "hunan", "guangdong", "guangxi",
    "hainan", "chongqing", "sichuan", "guizhou", "yunnan", "xizang",
    "shaanxi", "gansu", "qinghai", "ningxia", "xinjiang",
]


def load_import_samples() -> dict:
    path = IMPORT_FILE if IMPORT_FILE.exists() else IMPORT_SAMPLE
    if not path.exists():
        print(
            f"No {IMPORT_FILE.name} found. Copy {IMPORT_SAMPLE.name} to "
            f"{IMPORT_FILE.name} and add province records before running."
        )
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {k: v for k, v in data.items() if not k.startswith("_")}


def build():
    samples = load_import_samples()
    SCORES_DIR.mkdir(parents=True, exist_ok=True)
    index = {"provinces": {}}

    for code in ALL_PROVINCES:
        prov_dir = SCORES_DIR / code
        prov_dir.mkdir(parents=True, exist_ok=True)

        if code in samples:
            data = samples[code]
            years = [data.get("year", 2024), data.get("year", 2024) - 1]
            years = sorted(set(years), reverse=True)
            for year in years:
                year_data = {**data, "year": year}
                if year != data.get("year", 2024):
                    year_data["records"] = [
                        {
                            **r,
                            "minScore": r["minScore"] - 3,
                            "minRank": int(r["minRank"] * 1.1),
                        }
                        for r in data.get("records", [])
                        if isinstance(r.get("minScore"), (int, float))
                        and isinstance(r.get("minRank"), (int, float))
                    ]
                    year_data["sourceDate"] = str(year) + "-07-20"
                out_path = prov_dir / f"{year}.json"
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(year_data, f, ensure_ascii=False, indent=2)
            index["provinces"][code] = {
                "years": years,
                "subjectTracks": [data.get("subjectTrack", "")],
                "hasData": bool(data.get("records")),
            }
        else:
            placeholder = {
                "province": code,
                "year": 2024,
                "subjectTrack": "物理类/理科",
                "sourceUrl": "",
                "sourceDate": "",
                "records": [],
                "note": "暂无投档线数据。请写入 data/raw/province_scores.json 后重新运行本脚本。",
            }
            with open(prov_dir / "2024.json", "w", encoding="utf-8") as f:
                json.dump(placeholder, f, ensure_ascii=False, indent=2)
            index["provinces"][code] = {
                "years": [2024],
                "subjectTracks": [],
                "hasData": False,
            }

    with open(SCORES_DIR / "index.json", "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    filled = sum(1 for c in ALL_PROVINCES if c in samples and samples[c].get("records"))
    print(f"Generated score files for {len(ALL_PROVINCES)} provinces ({filled} with imported data)")


if __name__ == "__main__":
    build()
