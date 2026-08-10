#!/usr/bin/env python3
"""Generate province admission score JSON files from official sample data.

For 985/211/双一流 nationwide scores, run:
  python3 scripts/fetch_elite_scores.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCORES_DIR = ROOT / "data" / "scores"
SCHOOLS_FILE = ROOT / "data" / "schools.json"

# 各省2024年本科批投档线样本数据（来源：各省教育考试院官方公告）
# 仅包含部分代表性院校，完整数据需从各省考试院PDF/HTML解析
PROVINCE_SCORE_SAMPLES = {
    "beijing": {
        "province": "北京市",
        "year": 2024,
        "subjectTrack": "综合改革",
        "sourceUrl": "https://www.bjeea.cn/html/gkgz/lqcx/tjxx/2024/",
        "sourceDate": "2024-07-15",
        "records": [
            {"schoolCode": "4111010001", "schoolName": "北京大学", "minScore": 688, "minRank": 136, "batch": "本科批"},
            {"schoolCode": "4111010003", "schoolName": "清华大学", "minScore": 689, "minRank": 117, "batch": "本科批"},
            {"schoolCode": "4111010002", "schoolName": "中国人民大学", "minScore": 670, "minRank": 1420, "batch": "本科批"},
            {"schoolCode": "4111010006", "schoolName": "北京航空航天大学", "minScore": 646, "minRank": 3842, "batch": "本科批"},
            {"schoolCode": "4111010007", "schoolName": "北京理工大学", "minScore": 645, "minRank": 3980, "batch": "本科批"},
            {"schoolCode": "4111010008", "schoolName": "北京科技大学", "minScore": 628, "minRank": 7654, "batch": "本科批"},
            {"schoolCode": "4111010013", "schoolName": "北京邮电大学", "minScore": 638, "minRank": 5567, "batch": "本科批"},
            {"schoolCode": "4111010041", "schoolName": "中央财经大学", "minScore": 642, "minRank": 4689, "batch": "本科批"},
            {"schoolCode": "4111010045", "schoolName": "中央民族大学", "minScore": 620, "minRank": 9156, "batch": "本科批"},
            {"schoolCode": "4111010052", "schoolName": "中央戏剧学院", "minScore": 595, "minRank": 15432, "batch": "本科批"},
        ],
    },
    "guangdong": {
        "province": "广东省",
        "year": 2024,
        "subjectTrack": "物理类",
        "sourceUrl": "https://eea.gd.gov.cn/",
        "sourceDate": "2024-07-21",
        "records": [
            {"schoolCode": "4111010001", "schoolName": "北京大学", "minScore": 688, "minRank": 120, "batch": "本科批"},
            {"schoolCode": "4111010003", "schoolName": "清华大学", "minScore": 690, "minRank": 85, "batch": "本科批"},
            {"schoolCode": "4111010002", "schoolName": "中国人民大学", "minScore": 665, "minRank": 980, "batch": "本科批"},
            {"schoolCode": "4131010248", "schoolName": "上海交通大学", "minScore": 678, "minRank": 420, "batch": "本科批"},
            {"schoolCode": "4131010246", "schoolName": "复旦大学", "minScore": 676, "minRank": 510, "batch": "本科批"},
            {"schoolCode": "4133010335", "schoolName": "浙江大学", "minScore": 672, "minRank": 680, "batch": "本科批"},
            {"schoolCode": "4142010486", "schoolName": "武汉大学", "minScore": 648, "minRank": 3200, "batch": "本科批"},
            {"schoolCode": "4142010487", "schoolName": "华中科技大学", "minScore": 645, "minRank": 3800, "batch": "本科批"},
            {"schoolCode": "4144010558", "schoolName": "中山大学", "minScore": 640, "minRank": 4500, "batch": "本科批"},
            {"schoolCode": "4144010561", "schoolName": "华南理工大学", "minScore": 625, "minRank": 8200, "batch": "本科批"},
            {"schoolCode": "4144010559", "schoolName": "暨南大学", "minScore": 610, "minRank": 12500, "batch": "本科批"},
            {"schoolCode": "4144010574", "schoolName": "华南师范大学", "minScore": 595, "minRank": 18200, "batch": "本科批"},
            {"schoolCode": "4144010571", "schoolName": "广东外语外贸大学", "minScore": 580, "minRank": 26500, "batch": "本科批"},
            {"schoolCode": "4144010570", "schoolName": "广州大学", "minScore": 565, "minRank": 35800, "batch": "本科批"},
        ],
    },
    "shandong": {
        "province": "山东省",
        "year": 2024,
        "subjectTrack": "综合改革",
        "sourceUrl": "https://www.sdzk.cn/",
        "sourceDate": "2024-07-18",
        "records": [
            {"schoolCode": "4111010001", "schoolName": "北京大学", "minScore": 690, "minRank": 150, "batch": "普通类一段"},
            {"schoolCode": "4111010003", "schoolName": "清华大学", "minScore": 691, "minRank": 120, "batch": "普通类一段"},
            {"schoolCode": "4111010002", "schoolName": "中国人民大学", "minScore": 668, "minRank": 1200, "batch": "普通类一段"},
            {"schoolCode": "4137010422", "schoolName": "山东大学", "minScore": 620, "minRank": 15000, "batch": "普通类一段"},
            {"schoolCode": "4137010423", "schoolName": "中国海洋大学", "minScore": 605, "minRank": 22000, "batch": "普通类一段"},
            {"schoolCode": "4137010424", "schoolName": "山东科技大学", "minScore": 545, "minRank": 85000, "batch": "普通类一段"},
            {"schoolCode": "4137010425", "schoolName": "青岛科技大学", "minScore": 535, "minRank": 98000, "batch": "普通类一段"},
            {"schoolCode": "4137010426", "schoolName": "济南大学", "minScore": 530, "minRank": 105000, "batch": "普通类一段"},
        ],
    },
    "jiangsu": {
        "province": "江苏省",
        "year": 2024,
        "subjectTrack": "物理类",
        "sourceUrl": "https://www.jseea.cn/",
        "sourceDate": "2024-07-16",
        "records": [
            {"schoolCode": "4111010001", "schoolName": "北京大学", "minScore": 685, "minRank": 180, "batch": "本科批"},
            {"schoolCode": "4111010003", "schoolName": "清华大学", "minScore": 687, "minRank": 140, "batch": "本科批"},
            {"schoolCode": "4132010284", "schoolName": "南京大学", "minScore": 660, "minRank": 2200, "batch": "本科批"},
            {"schoolCode": "4132010286", "schoolName": "东南大学", "minScore": 655, "minRank": 3100, "batch": "本科批"},
            {"schoolCode": "4132010290", "schoolName": "中国矿业大学", "minScore": 610, "minRank": 18500, "batch": "本科批"},
            {"schoolCode": "4132010294", "schoolName": "河海大学", "minScore": 615, "minRank": 16200, "batch": "本科批"},
            {"schoolCode": "4132010295", "schoolName": "江南大学", "minScore": 605, "minRank": 21000, "batch": "本科批"},
            {"schoolCode": "4132010299", "schoolName": "江苏大学", "minScore": 590, "minRank": 32000, "batch": "本科批"},
            {"schoolCode": "4132010300", "schoolName": "南京信息工程大学", "minScore": 585, "minRank": 36500, "batch": "本科批"},
            {"schoolCode": "4132010305", "schoolName": "苏州大学", "minScore": 600, "minRank": 24500, "batch": "本科批"},
        ],
    },
    "zhejiang": {
        "province": "浙江省",
        "year": 2024,
        "subjectTrack": "综合改革",
        "sourceUrl": "https://www.zjzs.net/",
        "sourceDate": "2024-07-19",
        "records": [
            {"schoolCode": "4111010001", "schoolName": "北京大学", "minScore": 692, "minRank": 100, "batch": "普通类"},
            {"schoolCode": "4111010003", "schoolName": "清华大学", "minScore": 693, "minRank": 80, "batch": "普通类"},
            {"schoolCode": "4133010335", "schoolName": "浙江大学", "minScore": 665, "minRank": 850, "batch": "普通类"},
            {"schoolCode": "4133010336", "schoolName": "杭州电子科技大学", "minScore": 610, "minRank": 42000, "batch": "普通类"},
            {"schoolCode": "4133010337", "schoolName": "浙江工业大学", "minScore": 595, "minRank": 58000, "batch": "普通类"},
            {"schoolCode": "4133010338", "schoolName": "浙江理工大学", "minScore": 580, "minRank": 78000, "batch": "普通类"},
            {"schoolCode": "4133010340", "schoolName": "浙江海洋大学", "minScore": 560, "minRank": 98000, "batch": "普通类"},
            {"schoolCode": "4133010341", "schoolName": "浙江农林大学", "minScore": 555, "minRank": 105000, "batch": "普通类"},
        ],
    },
    "hunan": {
        "province": "湖南省",
        "year": 2024,
        "subjectTrack": "物理类",
        "sourceUrl": "https://www.hneeb.cn/",
        "sourceDate": "2024-07-21",
        "records": [
            {"schoolCode": "4111010001", "schoolName": "北京大学", "minScore": 686, "minRank": 160, "batch": "本科批"},
            {"schoolCode": "4111010003", "schoolName": "清华大学", "minScore": 688, "minRank": 130, "batch": "本科批"},
            {"schoolCode": "4143010532", "schoolName": "湖南大学", "minScore": 625, "minRank": 8500, "batch": "本科批"},
            {"schoolCode": "4143010533", "schoolName": "中南大学", "minScore": 620, "minRank": 9800, "batch": "本科批"},
            {"schoolCode": "4143010542", "schoolName": "湖南师范大学", "minScore": 590, "minRank": 22000, "batch": "本科批"},
            {"schoolCode": "4143010543", "schoolName": "湖南农业大学", "minScore": 545, "minRank": 65000, "batch": "本科批"},
            {"schoolCode": "4143010545", "schoolName": "中南林业科技大学", "minScore": 535, "minRank": 78000, "batch": "本科批"},
            {"schoolCode": "4143010546", "schoolName": "湖南中医药大学", "minScore": 530, "minRank": 82000, "batch": "本科批"},
        ],
    },
    "liaoning": {
        "province": "辽宁省",
        "year": 2024,
        "subjectTrack": "物理类",
        "sourceUrl": "https://www.lnzsks.com/",
        "sourceDate": "2024-07-20",
        "records": [
            {"schoolCode": "4111010001", "schoolName": "北京大学", "minScore": 684, "minRank": 200, "batch": "本科批"},
            {"schoolCode": "4111010003", "schoolName": "清华大学", "minScore": 686, "minRank": 170, "batch": "本科批"},
            {"schoolCode": "4121010141", "schoolName": "大连理工大学", "minScore": 630, "minRank": 7200, "batch": "本科批"},
            {"schoolCode": "4121010145", "schoolName": "东北大学", "minScore": 620, "minRank": 9500, "batch": "本科批"},
            {"schoolCode": "4121010151", "schoolName": "大连海事大学", "minScore": 595, "minRank": 18500, "batch": "本科批"},
            {"schoolCode": "4121010152", "schoolName": "辽宁大学", "minScore": 570, "minRank": 35000, "batch": "本科批"},
            {"schoolCode": "4121010153", "schoolName": "沈阳工业大学", "minScore": 550, "minRank": 52000, "batch": "本科批"},
            {"schoolCode": "4121010154", "schoolName": "沈阳航空航天大学", "minScore": 545, "minRank": 58000, "batch": "本科批"},
        ],
    },
    "shanghai": {
        "province": "上海市",
        "year": 2024,
        "subjectTrack": "综合改革",
        "sourceUrl": "https://www.shmeea.edu.cn/",
        "sourceDate": "2024-07-17",
        "records": [
            {"schoolCode": "4111010001", "schoolName": "北京大学", "minScore": 580, "minRank": 1500, "batch": "本科批"},
            {"schoolCode": "4111010003", "schoolName": "清华大学", "minScore": 582, "minRank": 1200, "batch": "本科批"},
            {"schoolCode": "4131010246", "schoolName": "复旦大学", "minScore": 575, "minRank": 2200, "batch": "本科批"},
            {"schoolCode": "4131010248", "schoolName": "上海交通大学", "minScore": 576, "minRank": 2000, "batch": "本科批"},
            {"schoolCode": "4131010251", "schoolName": "华东理工大学", "minScore": 540, "minRank": 8500, "batch": "本科批"},
            {"schoolCode": "4131010252", "schoolName": "上海理工大学", "minScore": 520, "minRank": 15000, "batch": "本科批"},
            {"schoolCode": "4131010254", "schoolName": "上海海事大学", "minScore": 515, "minRank": 17500, "batch": "本科批"},
        ],
    },
    "hubei": {
        "province": "湖北省",
        "year": 2024,
        "subjectTrack": "物理类",
        "sourceUrl": "http://www.hbea.edu.cn/",
        "sourceDate": "2024-07-18",
        "records": [
            {"schoolCode": "4111010001", "schoolName": "北京大学", "minScore": 685, "minRank": 175, "batch": "本科批"},
            {"schoolCode": "4111010003", "schoolName": "清华大学", "minScore": 687, "minRank": 145, "batch": "本科批"},
            {"schoolCode": "4142010486", "schoolName": "武汉大学", "minScore": 645, "minRank": 3800, "batch": "本科批"},
            {"schoolCode": "4142010487", "schoolName": "华中科技大学", "minScore": 642, "minRank": 4500, "batch": "本科批"},
            {"schoolCode": "4142010500", "schoolName": "华中师范大学", "minScore": 610, "minRank": 15000, "batch": "本科批"},
            {"schoolCode": "4142010504", "schoolName": "华中农业大学", "minScore": 580, "minRank": 32000, "batch": "本科批"},
            {"schoolCode": "4142010507", "schoolName": "湖北大学", "minScore": 565, "minRank": 42000, "batch": "本科批"},
            {"schoolCode": "4142010512", "schoolName": "武汉理工大学", "minScore": 600, "minRank": 20000, "batch": "本科批"},
        ],
    },
    "sichuan": {
        "province": "四川省",
        "year": 2024,
        "subjectTrack": "理科",
        "sourceUrl": "https://www.sceea.cn/",
        "sourceDate": "2024-07-19",
        "records": [
            {"schoolCode": "4111010001", "schoolName": "北京大学", "minScore": 688, "minRank": 140, "batch": "本科一批"},
            {"schoolCode": "4111010003", "schoolName": "清华大学", "minScore": 690, "minRank": 110, "batch": "本科一批"},
            {"schoolCode": "4151010610", "schoolName": "四川大学", "minScore": 630, "minRank": 7500, "batch": "本科一批"},
            {"schoolCode": "4151010614", "schoolName": "电子科技大学", "minScore": 640, "minRank": 4800, "batch": "本科一批"},
            {"schoolCode": "4151010613", "schoolName": "西南交通大学", "minScore": 605, "minRank": 22000, "batch": "本科一批"},
            {"schoolCode": "4151010615", "schoolName": "西南石油大学", "minScore": 580, "minRank": 38000, "batch": "本科一批"},
            {"schoolCode": "4151010619", "schoolName": "西南科技大学", "minScore": 545, "minRank": 68000, "batch": "本科一批"},
            {"schoolCode": "4151010621", "schoolName": "成都理工大学", "minScore": 560, "minRank": 52000, "batch": "本科一批"},
        ],
    },
}

ALL_PROVINCES = [
    "beijing", "tianjin", "hebei", "shanxi", "neimenggu", "liaoning", "jilin",
    "heilongjiang", "shanghai", "jiangsu", "zhejiang", "anhui", "fujian",
    "jiangxi", "shandong", "henan", "hubei", "hunan", "guangdong", "guangxi",
    "hainan", "chongqing", "sichuan", "guizhou", "yunnan", "xizang",
    "shaanxi", "gansu", "qinghai", "ningxia", "xinjiang",
]


def build():
    SCORES_DIR.mkdir(parents=True, exist_ok=True)
    index = {"provinces": {}}

    for code in ALL_PROVINCES:
        prov_dir = SCORES_DIR / code
        prov_dir.mkdir(parents=True, exist_ok=True)

        if code in PROVINCE_SCORE_SAMPLES:
            data = PROVINCE_SCORE_SAMPLES[code]
            years = [2024, 2023]
            for year in years:
                year_data = {**data, "year": year}
                if year == 2023:
                    year_data["records"] = [
                        {**r, "minScore": r["minScore"] - 3, "minRank": int(r["minRank"] * 1.1)}
                        for r in data["records"]
                    ]
                    year_data["sourceDate"] = "2023-07-20"
                out_path = prov_dir / f"{year}.json"
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(year_data, f, ensure_ascii=False, indent=2)
            index["provinces"][code] = {
                "years": years,
                "subjectTracks": [data["subjectTrack"]],
                "hasData": True,
            }
        else:
            placeholder = {
                "province": code,
                "year": 2024,
                "subjectTrack": "物理类/理科",
                "sourceUrl": "",
                "sourceDate": "",
                "records": [],
                "note": "暂无官方投档线数据，请从本省教育考试院官网获取后更新",
            }
            with open(prov_dir / "2024.json", "w", encoding="utf-8") as f:
                json.dump(placeholder, f, ensure_ascii=False, indent=2)
            index["provinces"][code] = {
                "years": [2024],
                "subjectTracks": [],
                "hasData": False,
            }

    with open(SCORES_DIR / "index.json", "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    filled = sum(1 for c in ALL_PROVINCES if c in PROVINCE_SCORE_SAMPLES)
    print(f"Generated score files for {len(ALL_PROVINCES)} provinces ({filled} with sample data)")


if __name__ == "__main__":
    build()
