# Data and Asset Notice

## What This Repository Ships

| Part | Status |
|------|--------|
| Platform code | Complete implementation |
| Local Q&A backend `server.py` | Complete local proxy, requires your own DeepSeek API key |
| Bundled JSON under `data/` | Mock demo data only |
| Real school records, scores, rankings, logos, photos | Not included |
| API keys and secrets | Not included |

The intelligent Q&A widget and backend proxy are included for local use. The backend reads local JSON files, builds a compact evidence payload, and sends it to DeepSeek only after you configure your own key in `.env`.

No private key, token, cookie, production credential, or real user data is shipped in this repository.

## Included Assets

- `data/geo/china.json` is included for demo rendering. Verify upstream terms before commercial use.
- `assets/logos/DEMO*.svg` are generic placeholders and are not real school logos.
- `assets/vendor/echarts.min.js` is included to avoid CDN loading failure.
- `assets/photos/` contains no public photos.

## Build Scripts

Scripts may download or generate third-party data under ignored paths such as `data/raw/`. Do not commit generated real data unless you have the right to redistribute it.
