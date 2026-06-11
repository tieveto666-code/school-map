# 数据构建脚本

本目录提供**完整真实**的数据构建脚本，与平台前端配套使用。**仓库默认只附带模拟演示数据**；真实院校数据须用户自行从公开渠道获取后再运行脚本。

## 环境准备

```bash
pip install -r scripts/requirements.txt
```

## 推荐流程

在仓库根目录执行：

```bash
# 1. 获取教育部本科名单（生成 data/raw/moe_schools.csv 等）
python3 scripts/fetch_moe_list.py

# 2. 准备军队院校 CSV（参考 data/raw/military_academies.csv.sample，可选）
#    将文件保存为 data/raw/military_academies.csv

# 3. 准备本地标签与详情（勿提交到公开仓库）
cp data/raw/school_tags.sample.json data/raw/school_tags.json
# 编辑 school_tags.json，按教育部公开名单填写校名
cp data/raw/school_details.sample.json data/raw/school_details.json  # 可选

# 4. 生成院校索引与详情
python3 scripts/build_schools.py

# 5. 可选：录取分数
cp data/raw/province_scores.sample.json data/raw/province_scores.json
# 编辑 province_scores.json 后运行：
python3 scripts/fetch_scores.py

# 6. 可选：专业排名
python3 scripts/fetch_major_rankings.py

# 7. 可选：校徽与校园图片
cp data/raw/asset_sources.sample.json data/raw/asset_sources.json
# 编辑 asset_sources.json 填入有权使用的 favicon / 照片 URL 后运行：
python3 scripts/fetch_assets.py

# 8. 可选：百科录取分数线
python3 scripts/enrich_baike.py
```

## 输出文件

| 脚本 | 主要输出 |
|------|----------|
| `fetch_moe_list.py` | `data/raw/moe_schools.csv` 等 |
| `build_schools.py` | `data/schools.index.json`、`data/schools.details.json` |
| `fetch_scores.py` | `data/scores/{province}/{year}.json` |
| `fetch_major_rankings.py` | `data/majors/index.json`、`data/majors/rankings/*.json` |
| `fetch_assets.py` | `assets/logos/`、`assets/photos/` |
| `enrich_baike.py` | `data/baike/scores.json` |

生成真实数据后，请将 `data/schools.index.json` 中 `meta.demo` 设为 `false`（或删除该字段），并更新 `js/app.js` 中的 `DATA_VERSION`。

## 注意事项

- `data/raw/` 下的大体积原始文件已被 `.gitignore` 排除，请勿将未授权数据提交到公开仓库。
- 脚本会访问外部网站，请遵守各站点服务条款与 robots 规则。
- 公开发布生成结果前，请阅读 `DATA_SOURCES.md` 与 `NOTICE.md`。
