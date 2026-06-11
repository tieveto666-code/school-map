# 数据来源说明

> **代码与数据分离**：本仓库的院校平台代码（前端 + 构建脚本）完整真实；`data/` 下 JSON 为模拟演示数据。真实院校名单、分数、排名等须用户自行从公开渠道获取并构建。

本文档说明如何从公开渠道获取真实数据，并替换本仓库中的演示 JSON。**演示数据仅供功能验证，不可用于升学决策或统计分析。**

## 演示包内置内容

| 路径 | 内容 |
|------|------|
| `data/schools.index.json` | 15 所示例院校（`DEMO0001`…`DEMO0015`） |
| `data/schools.details.json` | 对应示例详情 |
| `data/scores/beijing/2025.json` | 北京市 2 条示例分数 |
| `data/majors/` | 2 个专业目录 + 1 个示例排名 |
| `data/baike/scores.json` | 空对象 |
| `assets/logos/DEMO*.svg` | 通用占位图标，非真实校徽 |
| `assets/photos/` | 无照片 |

## 真实数据获取指引

### 1. 院校名单

- **教育部普通高等学校（本科）**：[全国高等学校名单（2025-06-20）](http://www.moe.gov.cn/jyb_xxgk/s5743/s5744/202506/t20250627_1195683.html)
- **军队院校**：公开名录或你有权使用的数据源，CSV 格式参考 `data/raw/military_academies.csv.sample`
- **构建方式**：`python3 scripts/fetch_moe_list.py` → `python3 scripts/build_schools.py`

### 2. 985 / 211 / 双一流标签

- [985 工程名单](http://www.moe.gov.cn/srcsite/A22/s7065/200612/t20061206_128833.html)
- [211 工程名单](http://www.moe.gov.cn/srcsite/A22/s7065/200512/t20051223_82762.html)
- [第二轮双一流（2022）](http://www.moe.gov.cn/srcsite/A22/s7065/202202/t20220211_598710.html)

将校名写入 `data/raw/school_tags.json`（参考 `school_tags.sample.json`），`build_schools.py` 构建时自动匹配标签。

### 3. 录取分数

- 各省教育考试院官方公告、阳光高考等你有权使用的渠道
- **构建方式**：将数据写入 `data/raw/province_scores.json`（参考 `province_scores.sample.json`），再运行 `python3 scripts/fetch_scores.py`
- 输出：`data/scores/{provinceCode}/{year}.json`

### 4. 专业排名

- 如 [软科中国大学专业排名](https://www.shanghairanking.cn/rankings/bcmr/2025) 等，使用前请阅读其服务条款
- **构建方式**：`python3 scripts/fetch_major_rankings.py`

### 5. 地图 GeoJSON

- 演示包已包含 `data/geo/china.json`（轻量中国省级地图）
- 来源与许可说明见 [`data/geo/README.md`](data/geo/README.md)（阿里云 DataV GeoAtlas / 高德 GCJ-02 数据）
- 商用或公开发布前，请核对上游许可并遵守《测绘法》等法规

### 6. 校徽与校园图片

- 学校官网 favicon、Wikimedia Commons 等你有权使用的来源
- **构建方式**：复制 `data/raw/asset_sources.sample.json` 为 `asset_sources.json`，填入 favicon / 照片 URL 后运行 `python3 scripts/fetch_assets.py`；也可开启 `useSchoolWebsite` 从 `schools.json` 的 `website` 字段自动尝试 `/favicon.ico`
- 校徽与照片**不自动适用**本仓库 MIT 许可证，转载需保留署名并遵守原许可

## 替换演示数据后的检查清单

- [ ] `data/schools.index.json` 的 `meta.demo` 已关闭或删除
- [ ] `js/app.js` 中 `DATA_VERSION` 已更新
- [ ] 未将 `data/raw/*.csv`、`*.xls`、`*.html` 等待授权原始文件提交到公开仓库
- [ ] 校徽、照片、排名等第三方素材已确认许可
- [ ] 页脚与 `NOTICE.md` 中的数据来源表述与实际一致

## 授权边界

代码（MIT）与数据/素材（各来源自有条款）分开管理。详见 `NOTICE.md` 与 `LICENSE` 末尾说明。
