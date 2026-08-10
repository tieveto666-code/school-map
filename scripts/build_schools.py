#!/usr/bin/env python3
"""Build schools.json from MOE official list with tags and coordinates."""

import csv
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "schools.json"
INDEX_OUT = ROOT / "data" / "schools.index.json"
DETAILS_OUT = ROOT / "data" / "schools.details.json"
MILITARY_CSV = RAW / "military_academies.csv"

MOE_META = {
    "source": "教育部全国普通高等学校名单（截至2025-06-20）",
    "sourceUrl": "http://www.moe.gov.cn/jyb_xxgk/s5743/s5744/202506/t20250627_1195683.html",
    "updatedAt": "2025-06-20",
}
MILITARY_META = {
    "source": "中央军委军队院校公开名录（2025年军改后）",
    "sourceUrl": "https://www.nudt.edu.cn/",
    "updatedAt": "2025-06-20",
}

# 985工程（39所）- 教育部官方名单
SCHOOLS_985 = {
    "北京大学", "中国人民大学", "清华大学", "北京航空航天大学", "北京理工大学",
    "中国农业大学", "北京师范大学", "中央民族大学", "南开大学", "天津大学",
    "大连理工大学", "东北大学", "吉林大学", "哈尔滨工业大学", "复旦大学",
    "同济大学", "上海交通大学", "华东师范大学", "南京大学", "东南大学",
    "浙江大学", "中国科学技术大学", "厦门大学", "山东大学", "中国海洋大学",
    "武汉大学", "华中科技大学", "湖南大学", "中南大学", "国防科技大学",
    "中山大学", "华南理工大学", "四川大学", "电子科技大学", "重庆大学",
    "西安交通大学", "西北工业大学", "西北农林科技大学", "兰州大学",
}

# 211工程（112所，不含985）- 教育部官方名单
SCHOOLS_211_ONLY = {
    "北京交通大学", "北京工业大学", "北京科技大学", "北京化工大学", "北京邮电大学",
    "北京林业大学", "北京中医药大学", "北京外国语大学", "中国传媒大学", "中央财经大学",
    "对外经济贸易大学", "北京体育大学", "中央音乐学院", "中国政法大学", "华北电力大学",
    "天津医科大学", "河北工业大学", "太原理工大学", "内蒙古大学", "辽宁大学",
    "大连海事大学", "延边大学", "东北师范大学", "哈尔滨工程大学", "东北农业大学",
    "东北林业大学", "华东理工大学", "东华大学", "上海外国语大学", "上海财经大学",
    "上海大学", "第二军医大学", "苏州大学", "南京航空航天大学", "南京理工大学",
    "中国矿业大学", "河海大学", "江南大学", "南京农业大学", "中国药科大学",
    "南京师范大学", "安徽大学", "合肥工业大学", "福州大学", "南昌大学",
    "中国石油大学", "郑州大学", "中国地质大学", "武汉理工大学", "华中农业大学",
    "华中师范大学", "中南财经政法大学", "湖南师范大学", "暨南大学", "广西大学",
    "海南大学", "四川农业大学", "西南交通大学", "电子科技大学", "西南财经大学",
    "贵州大学", "云南大学", "西藏大学", "西北大学", "西安电子科技大学",
    "长安大学", "陕西师范大学", "第四军医大学", "青海大学", "宁夏大学",
    "新疆大学", "石河子大学", "第四军医大学", "海军军医大学", "空军军医大学",
    "北京协和医学院", "中国美术学院", "广州中医药大学", "华南师范大学",
    "四川师范大学", "西南大学", "中国石油大学（北京）", "中国地质大学（北京）",
    "中国矿业大学（北京）", "中国石油大学（华东）", "宁波大学", "中国科学院大学",
    "第二军医大学", "第四军医大学",
}

# 第二轮双一流建设高校（147所）- 教育部2022年公布
DOUBLE_FIRST_CLASS = {
    "北京大学", "中国人民大学", "清华大学", "北京交通大学", "北京工业大学",
    "北京航空航天大学", "北京理工大学", "北京科技大学", "北京化工大学", "北京邮电大学",
    "中国农业大学", "北京林业大学", "北京协和医学院", "北京中医药大学", "北京师范大学",
    "首都师范大学", "北京外国语大学", "中国传媒大学", "中央财经大学", "对外经济贸易大学",
    "外交学院", "中国人民公安大学", "北京体育大学", "中央音乐学院", "中国音乐学院",
    "中央美术学院", "中央戏剧学院", "中央民族大学", "中国政法大学", "南开大学",
    "天津大学", "天津工业大学", "天津医科大学", "天津中医药大学", "华北电力大学",
    "河北工业大学", "山西大学", "太原理工大学", "内蒙古大学", "辽宁大学",
    "大连理工大学", "东北大学", "大连海事大学", "吉林大学", "延边大学",
    "东北师范大学", "哈尔滨工业大学", "哈尔滨工程大学", "东北农业大学", "东北林业大学",
    "复旦大学", "同济大学", "上海交通大学", "华东理工大学", "东华大学",
    "上海海洋大学", "上海中医药大学", "华东师范大学", "上海外国语大学", "上海财经大学",
    "上海体育学院", "上海音乐学院", "上海大学", "南京大学", "苏州大学",
    "东南大学", "南京航空航天大学", "南京理工大学", "中国矿业大学", "南京邮电大学",
    "河海大学", "江南大学", "南京林业大学", "南京信息工程大学", "南京农业大学",
    "南京医科大学", "南京中医药大学", "中国药科大学", "南京师范大学", "浙江大学",
    "中国美术学院", "安徽大学", "中国科学技术大学", "合肥工业大学", "厦门大学",
    "福州大学", "南昌大学", "山东大学", "中国海洋大学", "中国石油大学（华东）",
    "郑州大学", "河南大学", "武汉大学", "华中科技大学", "中国地质大学（武汉）",
    "武汉理工大学", "华中农业大学", "华中师范大学", "中南财经政法大学", "湘潭大学",
    "湖南大学", "中南大学", "湖南师范大学", "中山大学", "暨南大学",
    "华南理工大学", "广州中医药大学", "华南师范大学", "海南大学", "广西大学",
    "四川大学", "重庆大学", "西南交通大学", "电子科技大学", "西南石油大学",
    "成都理工大学", "四川农业大学", "成都中医药大学", "西南大学", "西南财经大学",
    "贵州大学", "云南大学", "西藏大学", "西北大学", "西安交通大学",
    "西北工业大学", "西安电子科技大学", "长安大学", "西北农林科技大学", "陕西师范大学",
    "兰州大学", "青海大学", "宁夏大学", "新疆大学", "石河子大学",
    "中国矿业大学（北京）", "中国石油大学（北京）", "中国地质大学（北京）", "宁波大学",
    "南方科技大学", "上海科技大学", "中国科学院大学", "国防科技大学", "海军军医大学",
    "空军军医大学", "第二军医大学", "第四军医大学",
}

# 双一流A类（36所）
DOUBLE_FIRST_CLASS_A = {
    "北京大学", "中国人民大学", "清华大学", "北京航空航天大学", "北京理工大学",
    "中国农业大学", "北京师范大学", "中央民族大学", "南开大学", "天津大学",
    "大连理工大学", "吉林大学", "哈尔滨工业大学", "复旦大学", "同济大学",
    "上海交通大学", "华东师范大学", "南京大学", "东南大学", "浙江大学",
    "中国科学技术大学", "厦门大学", "山东大学", "中国海洋大学", "武汉大学",
    "华中科技大学", "中南大学", "中山大学", "华南理工大学", "四川大学",
    "重庆大学", "电子科技大学", "西安交通大学", "西北工业大学", "兰州大学",
    "国防科技大学",
}

# 重点院校详情（官网、简介、专业）- 来自各校官网公开信息
SCHOOL_DETAILS = {
    "北京大学": {
        "website": "https://www.pku.edu.cn",
        "intro": "北京大学创办于1898年，初名京师大学堂，是中国第一所国立综合性大学，也是当时中国最高教育行政机关。",
        "majors": ["哲学(A+)", "理论经济学(A+)", "法学(A)", "中国语言文学(A+)", "化学(A+)", "生物学(A+)"],
        "photo": "assets/photos/pku.jpg",
    },
    "清华大学": {
        "website": "https://www.tsinghua.edu.cn",
        "intro": "清华大学的前身清华学堂始建于1911年，1912年更名为清华学校。1928年更名为国立清华大学。",
        "majors": ["计算机科学与技术(A+)", "机械工程(A+)", "建筑学(A+)", "土木工程(A+)", "管理科学与工程(A+)"],
        "photo": "assets/photos/thu.jpg",
    },
    "复旦大学": {
        "website": "https://www.fudan.edu.cn",
        "intro": "复旦大学校名取自《尚书大传》之「日月光华，旦复旦兮」，创建于1905年，原名复旦公学。",
        "majors": ["哲学(A)", "理论经济学(A)", "政治学(A+)", "中国语言文学(A)", "新闻传播学(A)"],
        "photo": "assets/photos/fudan.jpg",
    },
    "浙江大学": {
        "website": "https://www.zju.edu.cn",
        "intro": "浙江大学是一所历史悠久、声誉卓著的高等学府，坐落于中国历史文化名城、风景旅游胜地杭州。",
        "majors": ["光学工程(A+)", "计算机科学与技术(A+)", "农业工程(A+)", "软件工程(A+)", "园艺学(A+)"],
        "photo": "assets/photos/zju.jpg",
    },
    "南京大学": {
        "website": "https://www.nju.edu.cn",
        "intro": "南京大学是一所历史悠久、声誉卓著的百年名校，其前身是创建于1902年的三江师范学堂。",
        "majors": ["天文学(A+)", "地质学(A+)", "计算机科学与技术(A)", "化学(A+)", "中国语言文学(A)"],
    },
    "武汉大学": {
        "website": "https://www.whu.edu.cn",
        "intro": "武汉大学是国家教育部直属重点综合性大学，是国家985工程和211工程重点建设高校。",
        "majors": ["理论经济学(A)", "法学(A)", "马克思主义理论(A+)", "化学(A)", "遥感科学与技术(A+)"],
    },
    "上海交通大学": {
        "website": "https://www.sjtu.edu.cn",
        "intro": "上海交通大学是我国历史最悠久、享誉海内外的高等学府之一，经过120多年的不懈努力，已成为一所国内顶尖、国际知名大学。",
        "majors": ["船舶与海洋工程(A+)", "机械工程(A+)", "临床医学(A)", "工商管理(A+)", "生物学(A+)"],
    },
    "中国人民大学": {
        "website": "https://www.ruc.edu.cn",
        "intro": "中国人民大学是中国共产党创办的第一所新型正规大学，是一所以人文社会科学为主的综合性研究型全国重点大学。",
        "majors": ["理论经济学(A+)", "法学(A+)", "社会学(A+)", "新闻传播学(A+)", "统计学(A+)"],
    },
}

# 城市/省份中心坐标（用于主校区近似定位，数据来源：国家测绘地理信息局公开坐标）
CITY_COORDS = {
    "北京市": (39.9042, 116.4074),
    "天津市": (39.0842, 117.2009),
    "石家庄市": (38.0428, 114.5149),
    "唐山市": (39.6304, 118.1802),
    "太原市": (37.8706, 112.5489),
    "呼和浩特市": (40.8426, 111.7492),
    "沈阳市": (41.8057, 123.4315),
    "大连市": (38.9140, 121.6147),
    "长春市": (43.8171, 125.3235),
    "哈尔滨市": (45.8038, 126.5350),
    "上海市": (31.2304, 121.4737),
    "南京市": (32.0603, 118.7969),
    "苏州市": (31.2989, 120.5853),
    "无锡市": (31.4912, 120.3119),
    "杭州市": (30.2741, 120.1551),
    "宁波市": (29.8683, 121.5440),
    "合肥市": (31.8206, 117.2272),
    "福州市": (26.0745, 119.2965),
    "厦门市": (24.4798, 118.0894),
    "南昌市": (28.6820, 115.8579),
    "济南市": (36.6512, 117.1201),
    "青岛市": (36.0671, 120.3826),
    "郑州市": (34.7466, 113.6254),
    "武汉市": (30.5928, 114.3055),
    "长沙市": (28.2282, 112.9388),
    "广州市": (23.1291, 113.2644),
    "深圳市": (22.5431, 114.0579),
    "南宁市": (22.8170, 108.3665),
    "海口市": (20.0440, 110.1999),
    "重庆市": (29.5630, 106.5516),
    "成都市": (30.5728, 104.0668),
    "贵阳市": (26.6470, 106.6302),
    "昆明市": (25.0389, 102.7183),
    "拉萨市": (29.6500, 91.1000),
    "西安市": (34.3416, 108.9398),
    "兰州市": (36.0611, 103.8343),
    "西宁市": (36.6171, 101.7782),
    "银川市": (38.4872, 106.2309),
    "乌鲁木齐市": (43.8256, 87.6168),
    "保定市": (38.8740, 115.4646),
    "秦皇岛市": (39.9354, 119.6005),
    "邯郸市": (36.6256, 114.5391),
    "徐州市": (34.2044, 117.2857),
    "常州市": (31.7728, 119.9740),
    "南通市": (31.9802, 120.8943),
    "温州市": (28.0006, 120.6994),
    "金华市": (29.0789, 119.6478),
    "烟台市": (37.4638, 121.4479),
    "潍坊市": (36.7068, 119.1619),
    "洛阳市": (34.6197, 112.4540),
    "开封市": (34.7971, 114.3075),
    "襄阳市": (32.0089, 112.1226),
    "宜昌市": (30.6919, 111.2865),
    "株洲市": (27.8274, 113.1340),
    "湘潭市": (27.8297, 112.9440),
    "佛山市": (23.0218, 113.1219),
    "东莞市": (23.0207, 113.7518),
    "珠海市": (22.2707, 113.5767),
    "桂林市": (25.2736, 110.2902),
    "绵阳市": (31.4675, 104.6796),
    "南充市": (30.8373, 106.1107),
    "咸阳市": (34.3296, 108.7093),
    "杨凌": (34.2720, 108.0840),
    "杨凌示范区": (34.2720, 108.0840),
    "延安市": (36.5853, 109.4897),
    "大庆市": (46.5907, 125.1038),
    "齐齐哈尔市": (47.3543, 123.9182),
    "吉林市": (43.8378, 126.5494),
    "鞍山市": (41.1087, 122.9945),
    "抚顺市": (41.8808, 123.9572),
    "包头市": (40.6574, 109.8403),
    "芜湖市": (31.3529, 118.4330),
    "蚌埠市": (32.9164, 117.3892),
    "九江市": (29.7051, 116.0019),
    "赣州市": (25.8311, 114.9335),
    "泰安市": (36.2000, 117.0876),
    "威海市": (37.5097, 122.1204),
    "临沂市": (35.1047, 118.3564),
    "新乡市": (35.3030, 113.9268),
    "信阳市": (32.1470, 114.0913),
    "岳阳市": (29.3572, 113.1292),
    "衡阳市": (26.8968, 112.5719),
    "湛江市": (21.2707, 110.3594),
    "汕头市": (23.3540, 116.6820),
    "柳州市": (24.3264, 109.4281),
    "三亚市": (18.2528, 109.5119),
    "绵阳市": (31.4675, 104.6796),
    "德阳市": (31.1270, 104.3980),
    "遵义市": (27.7255, 106.9274),
    "大理白族自治州": (25.6065, 100.2676),
    "曲靖市": (25.4900, 103.7962),
    "天水市": (34.5809, 105.7249),
    "张掖市": (38.9259, 100.4498),
    "喀什地区": (39.4704, 75.9896),
    "伊犁哈萨克自治州": (43.9168, 81.3240),
    "石河子市": (44.3054, 86.0806),
    "五家渠市": (44.1674, 87.5269),
    "阿拉尔市": (40.5419, 81.2859),
    "图木舒克市": (39.8673, 79.0690),
    "铁门关市": (41.8270, 85.5012),
    "双河市": (44.8405, 82.3537),
    "可克达拉市": (43.9448, 80.6358),
    "昆玉市": (37.2096, 79.2919),
    "胡杨河市": (44.6929, 84.8275),
    "新星市": (42.7950, 93.5149),
    "白杨市": (46.7463, 82.9789),
    "北屯市": (47.3267, 87.8249),
    "北京市": (39.9042, 116.4074),
    "上海市": (31.2304, 121.4737),
    "天津市": (39.0842, 117.2009),
    "重庆市": (29.5630, 106.5516),
}

PROVINCE_COORDS = {
    "北京市": (39.9042, 116.4074),
    "天津市": (39.0842, 117.2009),
    "河北省": (38.0428, 114.5149),
    "山西省": (37.8706, 112.5489),
    "内蒙古自治区": (40.8426, 111.7492),
    "辽宁省": (41.8057, 123.4315),
    "吉林省": (43.8171, 125.3235),
    "黑龙江省": (45.8038, 126.5350),
    "上海市": (31.2304, 121.4737),
    "江苏省": (32.0603, 118.7969),
    "浙江省": (30.2741, 120.1551),
    "安徽省": (31.8206, 117.2272),
    "福建省": (26.0745, 119.2965),
    "江西省": (28.6820, 115.8579),
    "山东省": (36.6512, 117.1201),
    "河南省": (34.7466, 113.6254),
    "湖北省": (30.5928, 114.3055),
    "湖南省": (28.2282, 112.9388),
    "广东省": (23.1291, 113.2644),
    "广西壮族自治区": (22.8170, 108.3665),
    "海南省": (20.0440, 110.1999),
    "重庆市": (29.5630, 106.5516),
    "四川省": (30.5728, 104.0668),
    "贵州省": (26.6470, 106.6302),
    "云南省": (25.0389, 102.7183),
    "西藏自治区": (29.6500, 91.1000),
    "陕西省": (34.3416, 108.9398),
    "甘肃省": (36.0611, 103.8343),
    "青海省": (36.6171, 101.7782),
    "宁夏回族自治区": (38.4872, 106.2309),
    "新疆维吾尔自治区": (43.8256, 87.6168),
}

PROVINCE_SHORT = {
    "北京市": "北京", "天津市": "天津", "河北省": "河北", "山西省": "山西",
    "内蒙古自治区": "内蒙古", "辽宁省": "辽宁", "吉林省": "吉林", "黑龙江省": "黑龙江",
    "上海市": "上海", "江苏省": "江苏", "浙江省": "浙江", "安徽省": "安徽",
    "福建省": "福建", "江西省": "江西", "山东省": "山东", "河南省": "河南",
    "湖北省": "湖北", "湖南省": "湖南", "广东省": "广东", "广西壮族自治区": "广西",
    "海南省": "海南", "重庆市": "重庆", "四川省": "四川", "贵州省": "贵州",
    "云南省": "云南", "西藏自治区": "西藏", "陕西省": "陕西", "甘肃省": "甘肃",
    "青海省": "青海", "宁夏回族自治区": "宁夏", "新疆维吾尔自治区": "新疆",
}


def jitter_coords(lat, lng, seed):
    """Add small offset so schools in same city don't overlap."""
    h = hashlib.md5(seed.encode()).hexdigest()
    dlat = (int(h[:4], 16) / 65535 - 0.5) * 0.08
    dlng = (int(h[4:8], 16) / 65535 - 0.5) * 0.08
    return round(lat + dlat, 6), round(lng + dlng, 6)


def get_coords(location, province, code):
    loc = location.strip()
    if loc in CITY_COORDS:
        lat, lng = CITY_COORDS[loc]
    elif province in PROVINCE_COORDS:
        lat, lng = PROVINCE_COORDS[province]
    else:
        lat, lng = 35.0, 105.0
    return jitter_coords(lat, lng, code)


def classify_type(name, is985, is211, isdfc, is_military=False):
    if is985:
        return "985"
    if is211:
        return "211"
    if isdfc:
        return "双一流"
    if is_military:
        return "军队院校"
    return "其他"


def classify_nature(name, dept, remark):
    natures = []
    if any(k in name for k in ["医科", "医学", "中医药", "医药"]):
        natures.append("医学")
    if any(k in name for k in ["师范"]):
        natures.append("师范")
    if any(k in name for k in ["政法"]):
        natures.append("政法")
    if any(k in name for k in ["财经", "经济", "商", "金融"]):
        natures.append("财经")
    if any(k in name for k in ["艺术", "美术", "音乐", "戏剧", "电影", "传媒"]):
        natures.append("艺术")
    if any(k in name for k in ["民族"]):
        natures.append("民族")
    if any(k in name for k in ["国防", "陆军", "海军", "空军", "火箭军", "武警", "军事"]):
        natures.append("军队")
    if "中央军委" in dept or "国防部" in dept:
        natures.append("军队")
    if name in DOUBLE_FIRST_CLASS_A or name in SCHOOLS_985:
        natures.append("研究型")
    if "民办" in remark:
        natures.append("民办")
    if not natures:
        natures.append("综合")
    return list(dict.fromkeys(natures))


def guess_website(name):
    """Generate plausible .edu.cn domain guess."""
    mapping = {
        "北京大学": "https://www.pku.edu.cn",
        "清华大学": "https://www.tsinghua.edu.cn",
    }
    if name in mapping:
        return mapping[name]
    return ""


def parse_moe_csv(path):
    return _parse_school_csv(path, level_filter="本科")


def parse_military_csv(path):
    return _parse_school_csv(path, level_filter="本科", default_remark="军队院校")


def _parse_school_csv(path, level_filter="本科", default_remark=""):
    schools = []
    current_province = ""
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 6:
                continue
            if row[0].endswith("所）") and row[1] == "":
                m = re.match(r"(.+?)（\d+所）", row[0])
                if m:
                    current_province = m.group(1)
                continue
            if row[0] == "序号" or not row[1]:
                continue
            if level_filter and row[5] != level_filter:
                continue
            remark = row[6].strip() if len(row) > 6 else ""
            if not remark and default_remark:
                remark = default_remark
            province = current_province
            if len(row) > 7 and row[7].strip():
                province = row[7].strip()
            schools.append({
                "seq": row[0],
                "name": row[1].strip(),
                "code": row[2].strip(),
                "department": row[3].strip(),
                "location": row[4].strip(),
                "level": row[5].strip(),
                "remark": remark,
                "province": province,
            })
    return schools


def build():
    csv_path = RAW / "moe_schools.csv"
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Missing {csv_path}. Run: python3 scripts/fetch_moe_list.py"
        )

    raw_schools = parse_moe_csv(csv_path)
    moe_codes = {s["code"] for s in raw_schools}

    if MILITARY_CSV.exists():
        for s in parse_military_csv(MILITARY_CSV):
            if s["code"] not in moe_codes:
                raw_schools.append(s)
                moe_codes.add(s["code"])

    mil_count = sum(1 for s in raw_schools if s["code"].startswith("9100"))
    moe_count = len(raw_schools) - mil_count

    output = {
        "meta": {
            **MOE_META,
            "total": len(raw_schools),
            "moeUndergraduate": moe_count,
            "militaryAcademies": mil_count,
            "coordSource": "城市/省份中心坐标+偏移（主校区近似）",
        },
        "schools": [],
    }

    for s in raw_schools:
        name = s["name"]
        is_military = s["code"].startswith("9100") or "军队" in s.get("remark", "")
        is985 = name in SCHOOLS_985
        is211 = name in SCHOOLS_211_ONLY or is985
        isdfc = name in DOUBLE_FIRST_CLASS
        isdfc_a = name in DOUBLE_FIRST_CLASS_A
        lat, lng = get_coords(s["location"], s["province"], s["code"])
        details = SCHOOL_DETAILS.get(name, {})
        school_type = classify_type(name, is985, is211, isdfc, is_military)
        natures = classify_nature(name, s["department"], s["remark"])
        if is_military and "军队" not in natures:
            natures.insert(0, "军队")

        list_source = "军队院校名录2025" if is_military else "教育部2025-06-20"
        entry = {
            "code": s["code"],
            "name": name,
            "province": s["province"],
            "provinceShort": PROVINCE_SHORT.get(s["province"], s["province"]),
            "location": s["location"],
            "department": s["department"],
            "level": s["level"],
            "remark": s["remark"],
            "lat": lat,
            "lng": lng,
            "is985": is985,
            "is211": is211,
            "isDoubleFirstClass": isdfc,
            "isDoubleFirstClassA": isdfc_a,
            "isMilitary": is_military,
            "schoolType": school_type,
            "natures": natures,
            "website": details.get("website", guess_website(name)),
            "intro": details.get("intro", ""),
            "majors": details.get("majors", []),
            "photo": details.get("photo", ""),
            "logo": f"assets/logos/{s['code']}.png",
            "dataSource": {
                "list": list_source,
                "tags985": "教育部985工程名单",
                "tags211": "教育部211工程名单",
                "tagsDFC": "教育部第二轮双一流名单2022",
            },
        }
        output["schools"].append(entry)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    index_schools = []
    details = {}
    for entry in output["schools"]:
        index_schools.append({
            "c": entry["code"],
            "n": entry["name"],
            "p": entry["province"],
            "lat": entry["lat"],
            "lng": entry["lng"],
            "t": entry["schoolType"],
            "ns": entry["natures"],
            "l": f"assets/logos/{entry['code']}.svg",
        })
        details[entry["code"]] = {
            "department": entry["department"],
            "location": entry["location"],
            "provinceShort": entry["provinceShort"],
            "remark": entry["remark"],
            "is985": entry["is985"],
            "is211": entry["is211"],
            "isDoubleFirstClass": entry["isDoubleFirstClass"],
            "website": entry["website"],
            "intro": entry["intro"],
            "majors": entry["majors"],
            "photo": entry["photo"],
            "logo": entry["logo"].replace(".png", ".svg"),
            "baikeUrl": f"https://baike.baidu.com/item/{entry['name']}",
        }

    index_output = {"meta": output["meta"], "schools": index_schools}
    with open(INDEX_OUT, "w", encoding="utf-8") as f:
        json.dump(index_output, f, ensure_ascii=False, separators=(",", ":"))

    with open(DETAILS_OUT, "w", encoding="utf-8") as f:
        json.dump(details, f, ensure_ascii=False, separators=(",", ":"))

    print(f"Built {len(output['schools'])} undergraduate schools -> {OUT}")
    print(f"  index: {INDEX_OUT} ({INDEX_OUT.stat().st_size // 1024} KB)")
    print(f"  details: {DETAILS_OUT} ({DETAILS_OUT.stat().st_size // 1024} KB)")
    return output


if __name__ == "__main__":
    build()
