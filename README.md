# 全国本科院校分布图

**在线演示：** https://tieveto666-code.github.io/school-map/

## 本仓库提供什么

| 类别 | 内容 | 说明 |
|------|------|------|
| 平台代码 | `index.html`、`css/`、`js/`、`server.py`、`scripts/` | 完整实现，可直接克隆运行 |
| 内置数据 | `data/schools.*.json`、`data/scores/`、`data/majors/` | 模拟演示数据，仅供验证功能 |
| 真实数据 | 院校名单、分数、排名、校徽、照片 | 不随仓库发布，需自行获取并确认授权 |

克隆后可体验地图、筛选、详情弹窗、省份分析、专业排名和智能问答入口。默认数据为「示例大学甲」等虚构内容，不可用于升学决策或统计分析。

## 重要说明

- 代码完整保留，包括智能问答前端组件、本地 DeepSeek 代理后端、检索 evidence JSON、对话上下文和每 10 轮摘要逻辑。
- 仓库不包含任何真实 API Key、访问令牌、私有数据或未脱敏原始文件。
- DeepSeek API Key 请放在本地 `.env`，不要提交到 GitHub。
- 第三方数据与素材需遵守各自来源条款，见 `DATA_SOURCES.md` 与 `NOTICE.md`。

## 静态演示运行

直接打开 `index.html` 可能因浏览器 CORS 限制无法加载 JSON，请启动静态服务器：

```bash
python3 -m http.server 8080
```

浏览器访问 `http://localhost:8080`。静态模式可使用地图、筛选、详情、省份分析和专业排名；智能问答入口会显示，但真实问答需要本地后端。

## 启用智能问答

GitHub Pages 是静态托管，不能保存 API Key 或运行 `/api/chat`。如需体验智能问答，请本地启动后端：

```bash
cp .env.example .env
# 编辑 .env，将 DEEPSEEK_API_KEY 替换为你自己的 sk-... 密钥

PORT=8081 python3 server.py
```

浏览器访问 `http://localhost:8081`。

智能问答流程：

```text
用户输入问题
-> 前端携带 sessionId 调用 /api/chat
-> 后端解析学校、省份、专业、分数、年份和查询意图
-> 从本地 JSON 数据检索相关 evidence
-> 拼接系统提示词、对话摘要/最近对话、evidence JSON 和用户问题
-> 调用 DeepSeek
-> 前端展示回复
-> 后端记录本轮对话，每 10 轮自动摘要上下文
```

## 替换真实数据

仓库提供完整构建脚本，但不包含真实原始数据。请自行从教育部、各省考试院、排名机构、学校官网等公开且允许使用的来源获取数据。

```bash
pip install -r scripts/requirements.txt
python3 scripts/fetch_moe_list.py
cp data/raw/school_tags.sample.json data/raw/school_tags.json
python3 scripts/build_schools.py
python3 scripts/fetch_scores.py
python3 scripts/fetch_major_rankings.py
```

主要输出：

- `data/schools.index.json`：地图点位与筛选索引
- `data/schools.details.json`：学校详情
- `data/scores/{provinceCode}/{year}.json`：分省录取分
- `data/majors/index.json`、`data/majors/rankings/*.json`：专业目录与排名
- `assets/logos/`、`assets/photos/`：校徽与图片

## 项目结构

```text
index.html
server.py
.env.example
css/
js/
assets/
  vendor/echarts.min.js
  logos/DEMO*.svg
  photos/
data/
  geo/china.json
  raw/
  schools.index.json
  schools.details.json
  scores/
  majors/
scripts/
DATA_SOURCES.md
NOTICE.md
LICENSE
```

## License

代码使用 MIT License。演示数据和占位图仅供功能验证；真实数据、地图和第三方素材按其来源许可管理。
