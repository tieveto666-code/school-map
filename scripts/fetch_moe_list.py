#!/usr/bin/env python3
"""Fetch / merge MOE school list for build_schools.py.

Sources (priority):
1. data/raw/moe_schools_2025.xls  — official XLS if manually downloaded
2. data/raw/eol_202506.html       — EOL 2025 article (if table embedded)
3. data/raw/eol_202406.html       — EOL 2024 full HTML table (1308 本科 baseline)
4. Applies data/raw/moe_schools_2025_patch.json (renames + 2025 additions)

Official XLS download (anti-bot may block automation):
  https://gaokao.chsi.com.cn/news/file.do?method=downFile&id=2293393220&attach=true&hist=false
"""

from __future__ import annotations

import csv
import json
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT_CSV = RAW / "moe_schools.csv"
PATCH = RAW / "moe_schools_2025_patch.json"

PROVINCE_FULL = {
    "北京": "北京市", "天津": "天津市", "河北": "河北省", "山西": "山西省",
    "内蒙古": "内蒙古自治区", "辽宁": "辽宁省", "吉林": "吉林省", "黑龙江": "黑龙江省",
    "上海": "上海市", "江苏": "江苏省", "浙江": "浙江省", "安徽": "安徽省",
    "福建": "福建省", "江西": "江西省", "山东": "山东省", "河南": "河南省",
    "湖北": "湖北省", "湖南": "湖南省", "广东": "广东省", "广西": "广西壮族自治区",
    "海南": "海南省", "重庆": "重庆市", "四川": "四川省", "贵州": "贵州省",
    "云南": "云南省", "西藏": "西藏自治区", "陕西": "陕西省", "甘肃": "甘肃省",
    "青海": "青海省", "宁夏": "宁夏回族自治区", "新疆": "新疆维吾尔自治区",
}


class TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_td = False
        self.cur = ""
        self.row: list[str] = []
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag, attrs):
        if tag == "td":
            self.in_td = True
            self.cur = ""

    def handle_endtag(self, tag):
        if tag == "td":
            self.in_td = False
            self.row.append(self.cur.strip())
        elif tag == "tr":
            if self.row:
                self.rows.append(self.row)
            self.row = []

    def handle_data(self, data):
        if self.in_td:
            self.cur += data


def parse_eol_html(path: Path) -> list[dict]:
    html = path.read_text(encoding="utf-8", errors="ignore")
    parser = TableParser()
    parser.feed(html)
    schools: list[dict] = []
    province = ""
    seq = 0
    for row in parser.rows:
        if len(row) == 1 and "（" in row[0] and "所）" in row[0]:
            m = re.match(r"(.+?)（\d+所）", row[0])
            if m:
                province = m.group(1).strip()
            continue
        if len(row) < 6 or row[0] == "序号":
            continue
        if not re.fullmatch(r"\d{10}", row[2]):
            continue
        level = row[5].strip()
        if level != "本科":
            continue
        seq += 1
        schools.append({
            "seq": str(seq),
            "name": row[1].strip(),
            "code": row[2].strip(),
            "department": row[3].strip(),
            "location": row[4].strip(),
            "level": level,
            "remark": row[6].strip() if len(row) > 6 else "",
            "province": province,
        })
    return schools


def parse_xls(path: Path) -> list[dict]:
    try:
        import pandas as pd
    except ImportError as exc:
        raise SystemExit("pip install pandas xlrd openpyxl") from exc
    df = pd.read_excel(path, header=None)
    schools: list[dict] = []
    province = ""
    seq = 0
    for _, row in df.iterrows():
        cells = [str(x).strip() if pd.notna(x) else "" for x in row.tolist()]
        if len(cells) < 6:
            continue
        if cells[0].endswith("所）") and not cells[1]:
            m = re.match(r"(.+?)（\d+所）", cells[0])
            if m:
                province = m.group(1)
            continue
        if cells[0] == "序号" or not cells[1]:
            continue
        code = re.sub(r"\.0$", "", cells[2])
        if not re.fullmatch(r"\d{10}", code):
            continue
        if cells[5] != "本科":
            continue
        seq += 1
        schools.append({
            "seq": str(seq),
            "name": cells[1],
            "code": code,
            "department": cells[3],
            "location": cells[4],
            "level": cells[5],
            "remark": cells[6] if len(cells) > 6 else "",
            "province": province,
        })
    return schools


def load_patch() -> tuple[dict[str, str], list[dict]]:
    if not PATCH.exists():
        return {}, []
    data = json.loads(PATCH.read_text(encoding="utf-8"))
    renames = {k: v for k, v in data.get("renames", {}).items()}
    additions = data.get("additions", [])
    return renames, additions


def apply_patch(schools: list[dict]) -> list[dict]:
    renames, additions = load_patch()
    by_code = {s["code"]: s for s in schools}
    by_name = {s["name"]: s for s in schools}

    for old, new in renames.items():
        if old in by_name:
            by_name[old]["name"] = new
            by_name[new] = by_name[old]
        for s in schools:
            if s["name"] == old:
                s["name"] = new

    existing_codes = set(by_code)
    existing_names = {s["name"] for s in schools}
    seq = len(schools)
    for item in additions:
        name = item["name"]
        code = item["code"]
        if name in existing_names or code in existing_codes:
            continue
        prov = item.get("province", "")
        if prov and prov not in PROVINCE_FULL.values() and prov in PROVINCE_FULL:
            prov = PROVINCE_FULL[prov]
        seq += 1
        schools.append({
            "seq": str(seq),
            "name": name,
            "code": code,
            "department": item.get("department", prov or "省级教育部门"),
            "location": item.get("location", prov),
            "level": "本科",
            "remark": item.get("remark", ""),
            "province": prov,
        })
        existing_codes.add(code)
        existing_names.add(name)

    for i, s in enumerate(schools, 1):
        s["seq"] = str(i)
    return schools


def write_csv(schools: list[dict], path: Path, meta_note: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["附件1：", "", "", "", "", "", ""])
        w.writerow([meta_note, "", "", "", "", "", ""])
        w.writerow(["序号", "学校名称", "学校标识码", "主管部门", "所在地", "办学层次", "备注"])
        province = ""
        prov_count: dict[str, int] = {}
        for s in schools:
            prov_count[s["province"]] = prov_count.get(s["province"], 0) + 1
        for s in schools:
            if s["province"] != province:
                province = s["province"]
                w.writerow([f"{province}（{prov_count[province]}所）", "", "", "", "", "", ""])
            w.writerow([
                s["seq"], s["name"], s["code"], s["department"],
                s["location"], s["level"], s["remark"],
            ])


def main():
    schools: list[dict] = []
    source = ""

    xls_2025 = RAW / "moe_schools_2025.xls"
    if xls_2025.exists() and xls_2025.stat().st_size > 50000:
        schools = parse_xls(xls_2025)
        source = "教育部全国普通高等学校名单（截至2025-06-20，官方XLS）"
    else:
        eol_2025 = RAW / "eol_202506.html"
        eol_2024 = RAW / "eol_202406.html"
        for path in (eol_2025, eol_2024):
            if path.exists() and path.stat().st_size > 100000:
                schools = parse_eol_html(path)
                if schools:
                    source = f"EOL HTML {path.name} + 2025 patch"
                    break
        if not schools:
            raise SystemExit(
                "No MOE source found. Place moe_schools_2025.xls or eol_202406.html in data/raw/"
            )
        schools = apply_patch(schools)
        source = "教育部全国普通高等学校名单（截至2025-06-20，EOL+补丁）"

    write_csv(schools, OUT_CSV, source)
    print(f"Wrote {len(schools)} undergraduate schools -> {OUT_CSV}")
    print(f"  Source: {source}")


if __name__ == "__main__":
    main()
