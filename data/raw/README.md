# 原始数据模板

此目录只保留脱敏模板文件。真实 CSV、XLS、HTML、JSON 原始数据默认被 `.gitignore` 排除。

使用方式：

```bash
cp school_tags.sample.json school_tags.json
cp province_scores.sample.json province_scores.json
cp asset_sources.sample.json asset_sources.json
```

编辑复制后的本地文件，再运行 `scripts/` 中的构建脚本。公开发布前请确认所有数据来源均允许再分发。
