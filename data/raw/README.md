# 原始数据目录

公开版仓库**不包含**完整真实院校原始数据。请自行获取、核验并确认授权后，将文件放到此目录，再运行 `scripts/` 中的构建脚本。

## 文件说明

| 文件 | 说明 |
|------|------|
| `military_academies.csv.sample` | 军队院校 CSV 格式示例（虚构数据） |
| `school_tags.sample.json` | 985/211/双一流标签模板 → 复制为 `school_tags.json` |
| `school_details.sample.json` | 院校详情模板 → 复制为 `school_details.json` |
| `province_scores.sample.json` | 分省投档线模板 → 复制为 `province_scores.json` |
| `name_aliases.sample.json` | API 校名别名模板 → 复制为 `name_aliases.json`（可选） |
| `asset_sources.sample.json` | 校徽 favicon / 校园照片 URL 模板 → 复制为 `asset_sources.json`（可选） |
| `moe_schools.csv` | 由 `scripts/fetch_moe_list.py` 生成，**勿提交到公开仓库** |

`.gitignore` 已排除 `*.csv`、`*.html`、`*.xls`、`*.xlsx` 及本地 `*.json`（保留 `*.sample.json`），防止误提交本地抓取结果。

## 构建流程

```bash
pip install -r scripts/requirements.txt
python3 scripts/fetch_moe_list.py
cp data/raw/school_tags.sample.json data/raw/school_tags.json
# 编辑 school_tags.json，按教育部公开名单填写校名
cp data/raw/school_details.sample.json data/raw/school_details.json  # 可选
python3 scripts/build_schools.py
cp data/raw/province_scores.sample.json data/raw/province_scores.json  # 可选
python3 scripts/fetch_scores.py
cp data/raw/asset_sources.sample.json data/raw/asset_sources.json  # 可选
python3 scripts/fetch_assets.py
```

更多数据来源见仓库根目录 [`DATA_SOURCES.md`](../../DATA_SOURCES.md)。
