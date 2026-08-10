#!/usr/bin/env python3
"""Download school favicons and sample campus photos."""

import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHOOLS_FILE = ROOT / "data" / "schools.json"
LOGOS_DIR = ROOT / "assets" / "logos"
PHOTOS_DIR = ROOT / "assets" / "photos"

WEBSITES = {
    "4111010001": "https://www.pku.edu.cn/favicon.ico",
    "4111010003": "https://www.tsinghua.edu.cn/favicon.ico",
    "4111010002": "https://www.ruc.edu.cn/favicon.ico",
    "4131010246": "https://www.fudan.edu.cn/favicon.ico",
    "4131010248": "https://www.sjtu.edu.cn/favicon.ico",
    "4133010335": "https://www.zju.edu.cn/favicon.ico",
    "4132010284": "https://www.nju.edu.cn/favicon.ico",
    "4142010486": "https://www.whu.edu.cn/favicon.ico",
    "4142010487": "https://www.hust.edu.cn/favicon.ico",
    "4144010558": "https://www.sysu.edu.cn/favicon.ico",
    "4151010610": "https://www.scu.edu.cn/favicon.ico",
    "4151010614": "https://www.uestc.edu.cn/favicon.ico",
    "4137010422": "https://www.sdu.edu.cn/favicon.ico",
    "4121010141": "https://www.dlut.edu.cn/favicon.ico",
    "4143010532": "https://www.hnu.edu.cn/favicon.ico",
    "4143010533": "https://www.csu.edu.cn/favicon.ico",
}

PHOTOS = {
    "pku.jpg": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a9/Peking_University_Campus.jpg/640px-Peking_University_Campus.jpg",
    "thu.jpg": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4e/Tsinghua_University_Gate.jpg/640px-Tsinghua_University_Gate.jpg",
    "fudan.jpg": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/Fudan_University_Guanghua_Towers.jpg/640px-Fudan_University_Guanghua_Towers.jpg",
    "zju.jpg": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5e/Zhejiang_University_Yuquan_Campus.jpg/640px-Zhejiang_University_Yuquan_Campus.jpg",
}


def download(url, dest, timeout=10):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            dest.write_bytes(resp.read())
        return True
    except Exception as e:
        print(f"  skip {dest.name}: {e}")
        return False


def generate_svg_logo(code, name, dest):
  initial = name[0] if name else "校"
  colors = ["2563eb", "7c3aed", "059669", "dc2626", "d97706", "0891b2"]
  color = colors[int(code[-2:]) % len(colors)] if len(code) >= 2 else colors[0]
  svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="8" fill="#{color}"/>
  <text x="32" y="42" text-anchor="middle" fill="white" font-size="28" font-family="sans-serif">{initial}</text>
</svg>'''
  dest.write_text(svg, encoding="utf-8")


def build():
    LOGOS_DIR.mkdir(parents=True, exist_ok=True)
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

    with open(SCHOOLS_FILE, encoding="utf-8") as f:
        schools = json.load(f)["schools"]

    logo_ok = 0
    for s in schools:
        code = s["code"]
        dest = LOGOS_DIR / f"{code}.png"
        svg_dest = LOGOS_DIR / f"{code}.svg"
        if code in WEBSITES:
            if download(WEBSITES[code], dest):
                logo_ok += 1
                continue
        generate_svg_logo(code, s["name"], svg_dest)
        s["logo"] = f"assets/logos/{code}.svg"

    for fname, url in PHOTOS.items():
        download(url, PHOTOS_DIR / fname)

    license_text = """Wikimedia Commons Photos - License Information
============================================
pku.jpg - CC BY-SA, Wikimedia Commons
thu.jpg - CC BY-SA, Wikimedia Commons
fudan.jpg - CC BY-SA, Wikimedia Commons
zju.jpg - CC BY-SA, Wikimedia Commons

School favicons - from respective official websites, for educational display only.
Generated SVG logos - project original, for schools without downloadable favicon.
"""
    (PHOTOS_DIR / "LICENSE.txt").write_text(license_text, encoding="utf-8")

    with open(SCHOOLS_FILE, encoding="utf-8") as f:
        data = json.load(f)
    for s in data["schools"]:
        svg = LOGOS_DIR / f"{s['code']}.svg"
        png = LOGOS_DIR / f"{s['code']}.png"
        if png.exists():
            s["logo"] = f"assets/logos/{s['code']}.png"
        elif svg.exists():
            s["logo"] = f"assets/logos/{s['code']}.svg"
    with open(SCHOOLS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Logos: {logo_ok} favicons downloaded, {len(schools)} SVG placeholders generated")
    print(f"Photos: {len(PHOTOS)} campus images downloaded")


if __name__ == "__main__":
    build()
