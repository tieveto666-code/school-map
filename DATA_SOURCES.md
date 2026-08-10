# 数据来源说明

本仓库采用代码与数据分离策略：平台代码完整开源，`data/` 下为模拟演示数据。真实院校名单、录取分数、专业排名、校徽和图片须自行获取并确认授权。

## 演示包内置内容

| 路径 | 内容 |
|------|------|
| `data/schools.index.json` | 15 所虚构示例院校 |
| `data/schools.details.json` | 示例院校详情 |
| `data/scores/beijing/2025.json` | 北京市示例分数 |
| `data/majors/` | 示例专业目录与排名 |
| `assets/logos/DEMO*.svg` | 占位图标，非真实校徽 |
| `assets/photos/` | 不包含照片 |

## 智能问答数据边界

`server.py` 不内置私有数据或 API Key。它只读取当前仓库本地 JSON：

- 院校：优先读取 `data/schools.json`；若不存在，则读取 `data/schools.index.json` + `data/schools.details.json`
- 专业：读取 `data/majors/index.json` 与 `data/majors/rankings/*.json`
- 分数：读取 `data/scores/{provinceCode}/{year}.json`
- 省份：读取 `data/provinces.json`
- 别名：读取 `data/aliases.json`，用于把学校简称、省份上下文短语、年份相对词归一化到标准字段

后端会根据用户问题检索相关 evidence JSON，再把 evidence、系统提示词、会话上下文和用户问题发送给 DeepSeek。真实 `DEEPSEEK_API_KEY` 只应保存在本地 `.env`。

## 真实数据来源建议

- 院校名单：教育部全国高等学校名单。
- 985/211/双一流标签：教育部公开通知。
- 录取分数：各省教育考试院、阳光高考等允许使用的来源。
- 专业排名：软科等排名机构，使用前请核对服务条款。
- 地图 GeoJSON：见 `data/geo/README.md`。
- 校徽/照片：学校官网、Wikimedia Commons 等有明确授权的来源。

## 发布前检查

- `data/schools.index.json` 中 `meta.demo` 已按实际情况调整。
- 未提交真实 `.env`、API Key、cookie、token。
- 未提交未授权的 `data/raw/*.csv`、`*.xls`、`*.html`。
- 第三方数据、地图、校徽、图片均已确认许可。
