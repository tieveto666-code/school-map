# Data and Asset Notice

## What This Repository Ships

| Part | Status |
|------|--------|
| Platform code (`html/`, `css/`, `js/`, `scripts/`) | **Complete and production-ready** — same implementation as the full school map platform |
| Bundled JSON under `data/` | **Mock demo data only** — 15 fictional sample schools for UI verification |
| Real school records, scores, rankings, logos | **Not included** — users must fetch and build locally |

This public GitHub package intentionally ships with demo placeholder data only.
The files under `data/schools.index.json`, `data/schools.details.json`,
`data/scores/`, `data/baike/`, and `data/majors/` are small mock datasets used
to verify that the map, filters, modal, and ranking panels render correctly.
They are not real school records and should not be used for analysis.

## Sources to Fetch Yourself

If you need a real dataset, fetch and verify it yourself before publishing or
redistributing:

- School list: Ministry of Education public school list, plus independently
  maintained military academy information if your use case requires it.
- 985 / 211 / Double First Class tags: public Ministry of Education notices.
- Major rankings: the ranking provider you choose, subject to that provider's
  terms.
- Admission scores: provincial education examination authorities or other
  sources you are allowed to use.
- China GeoJSON: the map provider you choose, subject to that provider's terms.
- School logos, favicons, photos, and marks: the relevant school or media
  rights holder. Do not assume these assets are free to redistribute.

## Included Assets

- `data/geo/china.json` is a province-level China GeoJSON for demo rendering.
  Source and license notes: [`data/geo/README.md`](data/geo/README.md)
  (Aliyun DataV GeoAtlas / Amap GCJ-02). Verify upstream terms before commercial use.
- `assets/logos/DEMO*.svg` are generic DEMO placeholders and are not real school
  logos.
- `assets/photos/` contains no photos in this public package.

## Build Scripts

The `scripts/` directory contains optional data-fetch and build utilities.
Running them may download third-party data to `data/raw/` or other paths that
are listed in `.gitignore`. Do not commit fetched files unless you have the
right to redistribute them. See `DATA_SOURCES.md` and `scripts/README.md`.

