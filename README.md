# 全国本科院校分布图

## 本仓库提供什么

| 类别 | 内容 | 说明 |
|------|------|------|
| **平台代码** | `index.html`、`css/`、`js/`、`scripts/` | **完整且真实**，与正式院校平台同一套实现，可直接克隆运行 |
| **内置数据** | `data/schools.*.json`、`data/scores/` 等 | **模拟演示数据**，仅 15 所示例院校，供验证功能 |
| **真实数据** | 院校名单、分数、排名、校徽等 | **需用户自行获取**，通过 `scripts/` 构建后替换 JSON |

克隆后即可体验地图、筛选、详情弹窗、省份分析和专业排名等**全部交互**；若要用于升学参考或正式展示，请按 [`DATA_SOURCES.md`](DATA_SOURCES.md) 自行抓取并替换数据。

## 重要说明

- **代码**：前端与构建脚本均为完整实现，非阉割版或伪代码。
- **数据**：`data/schools.index.json`、`data/schools.details.json` 等为**模拟数据**，校名为「示例大学甲」等虚构名称；真实院校名单、录取分数、专业排名、校徽和校园照片**未随仓库发布**。
- **授权**：代码使用 MIT License（Copyright tieveto666-code）；第三方数据与素材须遵守各自来源条款，见 [`NOTICE.md`](NOTICE.md)。

## 本地运行

直接打开 `index.html` 可能因浏览器 CORS 限制无法加载 JSON，请启动静态服务器：

```bash
python3 -m http.server 8080
```

浏览器访问 `http://localhost:8080`。

## 获取真实数据（需自行完成）

仓库提供完整的数据构建脚本，但**不包含**任何真实原始数据。数据须从教育部、各省考试院等公开渠道自行获取，确认授权后再写入本地 `data/raw/` 并运行脚本：

```bash
pip install -r scripts/requirements.txt
python3 scripts/fetch_moe_list.py      # 需自行准备数据源
cp data/raw/school_tags.sample.json data/raw/school_tags.json
python3 scripts/build_schools.py       # 读取本地 school_tags.json 生成 schools.*.json
python3 scripts/fetch_scores.py        # 需先准备 province_scores.json
python3 scripts/fetch_major_rankings.py  # 可选
```

详细说明见 [`DATA_SOURCES.md`](DATA_SOURCES.md) 与 [`scripts/README.md`](scripts/README.md)。

替换或生成后，主要数据文件为：

- `data/schools.index.json` — 地图点位与筛选索引
- `data/schools.details.json` — 学校详情
- `data/scores/{provinceCode}/{year}.json` — 分省录取分
- `data/majors/index.json`、`data/majors/rankings/*.json` — 专业排名
- `assets/logos/`、`assets/photos/` — 校徽与图片（需确认授权）

## 项目结构

```text
index.html
css/  js/
data/
  geo/china.json
  raw/                    # 原始数据模板（无真实 CSV/HTML）
  schools.index.json      # 演示索引
  schools.details.json
  scores/beijing/2025.json
  majors/
scripts/                  # 数据构建脚本
assets/
  logos/DEMO*.svg         # 占位图标
  photos/                 # 公开版无照片
DATA_SOURCES.md
NOTICE.md
LICENSE
```

## GitHub Pages

纯静态项目，上传 GitHub 后可在仓库 Settings → Pages 中启用：分支选 `main`，目录选仓库根目录 `/`。

## 推送前自检

在仓库根目录（即本文件夹）执行：

```bash
# 确认无真实校名泄漏（应无输出）
grep -r "北京大学\|清华大学" data/ assets/ || true

# 确认 scripts 中无真实校名（应无输出）
grep -r "北京大学\|清华大学" scripts/ || true

# 确认 raw 目录无大体积原始文件
ls -la data/raw/
```
