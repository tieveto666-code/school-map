# 数据构建脚本

本目录提供院校地图的数据构建脚本。公开仓库默认只附带模拟演示数据；真实数据须自行从公开且允许使用的来源获取。

## 环境准备

```bash
pip install -r scripts/requirements.txt
```

## 推荐流程

```bash
python3 scripts/fetch_moe_list.py
cp data/raw/school_tags.sample.json data/raw/school_tags.json
python3 scripts/build_schools.py

cp data/raw/province_scores.sample.json data/raw/province_scores.json
python3 scripts/fetch_scores.py

python3 scripts/fetch_major_rankings.py
python3 scripts/fetch_assets.py
python3 scripts/enrich_baike.py
```

## 输出文件

| 脚本 | 主要输出 |
|------|----------|
| `fetch_moe_list.py` | `data/raw/moe_schools.csv` |
| `build_schools.py` | `data/schools.index.json`、`data/schools.details.json` |
| `fetch_scores.py` | `data/scores/{province}/{year}.json` |
| `fetch_major_rankings.py` | `data/majors/index.json`、`data/majors/rankings/*.json` |
| `fetch_assets.py` | `assets/logos/`、`assets/photos/` |
| `enrich_baike.py` | `data/baike/scores.json` |

请勿将未授权原始数据、真实 API Key 或抓取缓存提交到公开仓库。
