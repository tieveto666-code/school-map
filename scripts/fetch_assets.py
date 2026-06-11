#!/usr/bin/env python3
"""Download school favicons and campus photos from local configuration.

Copy data/raw/asset_sources.sample.json to data/raw/asset_sources.json and
fill favicon URLs / photo sources you are allowed to use. When useSchoolWebsite
is true, the script also tries {website}/favicon.ico from data/schools.json.

The public repo does not ship real school favicon or photo URLs.
"""

import json
import urllib.request
from pathlib import Path
from urllib.parse import urljoin, urlparse

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
SCHOOLS_FILE = ROOT / "data" / "schools.json"
LOGOS_DIR = ROOT / "assets" / "logos"
PHOTOS_DIR = ROOT / "assets" / "photos"
SOURCES_FILE = RAW / "asset_sources.json"
SOURCES_SAMPLE = RAW / "asset_sources.sample.json"


def _load_sources() -> dict:
    path = SOURCES_FILE if SOURCES_FILE.exists() else SOURCES_SAMPLE
    if not path.exists():
        print(
            f"No {SOURCES_FILE.name} found. Copy {SOURCES_SAMPLE.name} to "
            f"{SOURCES_FILE.name} before running."
        )
        return {"useSchoolWebsite": True, "favicons": {}, "photos": {}}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {k: v for k, v in data.items() if not k.startswith("_")}


def download(url, dest, timeout=10):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            dest.write_bytes(resp.read())
        return True
    except Exception as e:
        print(f"  skip {dest.name}: {e}")
        return False


def favicon_candidates(code: str, school: dict, favicons: dict, use_school_website: bool) -> list[str]:
    urls = []
    if code in favicons and favicons[code]:
        urls.append(favicons[code])
    if use_school_website:
        website = (school.get("website") or "").strip()
        if website:
            base = website if website.endswith("/") else website + "/"
            parsed = urlparse(website)
            origin = f"{parsed.scheme}://{parsed.netloc}/"
            urls.append(urljoin(base, "favicon.ico"))
            urls.append(urljoin(origin, "favicon.ico"))
    seen = set()
    ordered = []
    for url in urls:
        if url and url not in seen:
            seen.add(url)
            ordered.append(url)
    return ordered


def generate_svg_logo(code, name, dest):
    initial = name[0] if name else "校"
    colors = ["2563eb", "7c3aed", "059669", "dc2626", "d97706", "0891b2"]
    color = colors[int(code[-2:]) % len(colors)] if len(code) >= 2 else colors[0]
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="8" fill="#{color}"/>
  <text x="32" y="42" text-anchor="middle" fill="white" font-size="28" font-family="sans-serif">{initial}</text>
</svg>'''
    dest.write_text(svg, encoding="utf-8")


def write_photo_license(photos: dict) -> None:
    lines = [
        "Campus photos - license information",
        "=" * 40,
        "",
    ]
    if photos:
        for fname, meta in photos.items():
            if isinstance(meta, str):
                lines.append(f"{fname} - configured locally ({meta})")
            else:
                license_name = meta.get("license", "see attribution")
                lines.append(f"{fname} - {license_name}")
                if meta.get("attribution"):
                    lines.append(f"  {meta['attribution']}")
                if meta.get("url"):
                    lines.append(f"  source: {meta['url']}")
    else:
        lines.append("(no photos configured in asset_sources.json)")
    lines.extend([
        "",
        "School favicons - from asset_sources.json or school website fields.",
        "Generated SVG logos - project original, for schools without a favicon.",
    ])
    (PHOTOS_DIR / "LICENSE.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build():
    if not SCHOOLS_FILE.exists():
        raise FileNotFoundError(
            f"Missing {SCHOOLS_FILE}. Run: python3 scripts/build_schools.py"
        )

    sources = _load_sources()
    favicons = sources.get("favicons") or {}
    photos = sources.get("photos") or {}
    use_school_website = bool(sources.get("useSchoolWebsite", True))

    LOGOS_DIR.mkdir(parents=True, exist_ok=True)
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

    with open(SCHOOLS_FILE, encoding="utf-8") as f:
        schools = json.load(f)["schools"]

    logo_ok = 0
    for s in schools:
        code = s["code"]
        dest = LOGOS_DIR / f"{code}.png"
        svg_dest = LOGOS_DIR / f"{code}.svg"
        downloaded = False
        for url in favicon_candidates(code, s, favicons, use_school_website):
            if download(url, dest):
                logo_ok += 1
                downloaded = True
                break
        if not downloaded:
            generate_svg_logo(code, s["name"], svg_dest)
            s["logo"] = f"assets/logos/{code}.svg"

    photo_ok = 0
    for fname, meta in photos.items():
        url = meta if isinstance(meta, str) else meta.get("url")
        if url and download(url, PHOTOS_DIR / fname):
            photo_ok += 1

    write_photo_license(photos)

    with open(SCHOOLS_FILE, encoding="utf-8") as f:
        data = json.load(f)
    for s in data["schools"]:
        png = LOGOS_DIR / f"{s['code']}.png"
        svg = LOGOS_DIR / f"{s['code']}.svg"
        if png.exists():
            s["logo"] = f"assets/logos/{s['code']}.png"
        elif svg.exists():
            s["logo"] = f"assets/logos/{s['code']}.svg"
    with open(SCHOOLS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Logos: {logo_ok} favicons downloaded, {len(schools) - logo_ok} SVG placeholders")
    print(f"Photos: {photo_ok}/{len(photos)} configured images downloaded")


if __name__ == "__main__":
    build()
