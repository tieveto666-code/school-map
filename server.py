#!/usr/bin/env python3
import json
import os
import pathlib
import re
import socket
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


ROOT = pathlib.Path(__file__).resolve().parent
SCHOOLS_DATA_PATH = ROOT / "data" / "schools.json"
SCHOOLS_INDEX_PATH = ROOT / "data" / "schools.index.json"
SCHOOLS_DETAILS_PATH = ROOT / "data" / "schools.details.json"
ALIASES_DATA_PATH = ROOT / "data" / "aliases.json"
PROVINCES_DATA_PATH = ROOT / "data" / "provinces.json"
MAJORS_INDEX_PATH = ROOT / "data" / "majors" / "index.json"
MAJOR_RANKINGS_DIR = ROOT / "data" / "majors" / "rankings"
SCORES_DIR = ROOT / "data" / "scores"
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
DEFAULT_MODEL = "deepseek-v4-flash"
MAX_REQUEST_BYTES = 16 * 1024
SUMMARY_EVERY_ROUNDS = 10
RECENT_ROUNDS_AFTER_SUMMARY = 0
MAX_SESSION_ID_LENGTH = 80
MAX_RECENT_TURNS_ON_SUMMARY_FAILURE = 20
MAX_SCHOOL_EVIDENCE = 80
MAX_PROVINCE_SCHOOL_NAMES = 120
MAX_MAJOR_MATCHES = 6
MAX_RANKING_RECORDS = 50
MAX_SCORE_RECORDS = 80
SCORE_AROUND_DELTA = 20
SESSIONS = {}
SESSIONS_LOCK = threading.Lock()

BASE_SYSTEM_PROMPT = """你是“全国本科院校可视化地图”的智能问答助手。
请严格基于本次请求提供的 evidence JSON 回答问题。
回答要求：
1. 只能使用 evidence 中存在的信息，不要编造学校属性、排名、分数或录取结论。
2. 如果 evidence 不足以回答，明确说明“当前数据不足”，并提示用户需要补充什么条件。
3. 涉及录取、志愿、分数时，只能做数据解释和筛选建议，不要承诺录取概率或保证结果。
4. 优先用简洁中文回答，必要时用列表。
5. 当前院校名单口径为教育部 2025-06-20 本科名单 + 军队院校公开名录。
6. 专业排名口径以 evidence 中的专业排名来源、年份和记录为准。
7. 回答时可以引用 evidence 中的学校名称、专业名称、排名、等级、分数、年份和数据口径。"""

SUMMARY_SYSTEM_PROMPT = """你是智能问答系统的对话上下文摘要器。
请把用户与助手的最近对话压缩成后续问答可用的上下文摘要。
要求：
1. 保留用户已明确提出的目标、偏好、约束、地域、分数、专业、学校名称等关键信息。
2. 保留助手已经给出的关键结论和未解决问题。
3. 不要添加对话中没有出现的新事实。
4. 用简洁中文输出，不超过 800 字。"""

SCHOOL_ALIASES = {
  "北大": "北京大学",
  "清华": "清华大学",
  "人大": "中国人民大学",
  "北航": "北京航空航天大学",
  "北理": "北京理工大学",
  "浙大": "浙江大学",
  "复旦": "复旦大学",
  "上交": "上海交通大学",
  "南大": "南京大学",
  "武大": "武汉大学",
  "华科": "华中科技大学",
  "中大": "中山大学",
  "川大": "四川大学",
  "西交": "西安交通大学",
  "哈工大": "哈尔滨工业大学",
}

# 常见宏观区域 → 省级行政区（按常见高考/统计口径）
REGION_PROVINCES = {
  "西部": [
    "重庆市", "四川省", "贵州省", "云南省", "西藏自治区",
    "陕西省", "甘肃省", "青海省", "宁夏回族自治区", "新疆维吾尔自治区",
    "广西壮族自治区", "内蒙古自治区",
  ],
  "西部地区": [
    "重庆市", "四川省", "贵州省", "云南省", "西藏自治区",
    "陕西省", "甘肃省", "青海省", "宁夏回族自治区", "新疆维吾尔自治区",
    "广西壮族自治区", "内蒙古自治区",
  ],
  "东部": [
    "北京市", "天津市", "河北省", "上海市", "江苏省", "浙江省",
    "福建省", "山东省", "广东省", "海南省",
  ],
  "东部地区": [
    "北京市", "天津市", "河北省", "上海市", "江苏省", "浙江省",
    "福建省", "山东省", "广东省", "海南省",
  ],
  "中部": [
    "山西省", "安徽省", "江西省", "河南省", "湖北省", "湖南省",
  ],
  "中部地区": [
    "山西省", "安徽省", "江西省", "河南省", "湖北省", "湖南省",
  ],
  "东北": ["辽宁省", "吉林省", "黑龙江省"],
  "东北地区": ["辽宁省", "吉林省", "黑龙江省"],
  "华北": ["北京市", "天津市", "河北省", "山西省", "内蒙古自治区"],
  "华东": ["上海市", "江苏省", "浙江省", "安徽省", "福建省", "江西省", "山东省"],
  "华南": ["广东省", "广西壮族自治区", "海南省"],
  "华中": ["河南省", "湖北省", "湖南省"],
  "西南": ["重庆市", "四川省", "贵州省", "云南省", "西藏自治区"],
  "西北": ["陕西省", "甘肃省", "青海省", "宁夏回族自治区", "新疆维吾尔自治区"],
}

MAJOR_KEYWORDS = [
  "计算机", "软件", "人工智能", "数据科学", "网络空间", "电子信息", "通信",
  "临床", "口腔", "医学", "法学", "经济", "金融", "会计", "师范", "教育",
  "汉语言", "新闻", "建筑", "土木", "机械", "自动化", "电气", "数学",
]


def load_env_file():
  env_path = ROOT / ".env"
  if not env_path.exists():
    return
  for line in env_path.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
      continue
    key, value = line.split("=", 1)
    key = key.strip()
    value = value.strip().strip('"').strip("'")
    if key and key not in os.environ:
      os.environ[key] = value


def load_json(path, default):
  try:
    return json.loads(path.read_text(encoding="utf-8"))
  except FileNotFoundError:
    return default
  except json.JSONDecodeError as exc:
    raise RuntimeError(f"{path.relative_to(ROOT)} 格式错误：{exc}") from exc


def compact_json(data):
  return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def clip_text(text, limit):
  text = str(text or "")
  if len(text) <= limit:
    return text
  return text[:limit] + "..."


def build_schools_from_public_demo_files():
  index_data = load_json(SCHOOLS_INDEX_PATH, {"meta": {}, "schools": []})
  details_data = load_json(SCHOOLS_DETAILS_PATH, {})
  schools = []
  for item in index_data.get("schools") or []:
    code = str(item.get("c") or "")
    detail = details_data.get(code) or {}
    natures = item.get("ns") or []
    school_type = item.get("t") or detail.get("schoolType") or "其他"
    schools.append({
      "code": code,
      "name": item.get("n"),
      "province": item.get("p"),
      "provinceShort": detail.get("provinceShort"),
      "location": detail.get("location") or item.get("p"),
      "department": detail.get("department"),
      "level": detail.get("level") or "本科",
      "schoolType": school_type,
      "natures": natures,
      "is985": bool(detail.get("is985") or school_type == "985"),
      "is211": bool(detail.get("is211") or school_type in ("985", "211")),
      "isDoubleFirstClass": bool(detail.get("isDoubleFirstClass") or school_type in ("985", "双一流")),
      "isMilitary": bool(detail.get("isMilitary") or "军队" in natures or school_type == "军队院校"),
      "website": detail.get("website"),
      "intro": detail.get("intro") or detail.get("remark"),
      "majors": detail.get("majors") or [],
      "logo": detail.get("logo") or item.get("l"),
    })
  return {
    "meta": index_data.get("meta") or {},
    "schools": schools,
  }


def load_school_index():
  if SCHOOLS_DATA_PATH.exists():
    data = load_json(SCHOOLS_DATA_PATH, {"meta": {}, "schools": []})
  else:
    data = build_schools_from_public_demo_files()
  schools = data.get("schools") or []
  by_code = {}
  by_name = {}
  province_to_schools = {}
  province_aliases = {}

  for school in schools:
    code = str(school.get("code") or "")
    name = str(school.get("name") or "")
    province = str(school.get("province") or "")
    province_short = str(school.get("provinceShort") or "")
    if code:
      by_code[code] = school
    if name:
      by_name[name] = school
    if province:
      province_to_schools.setdefault(province, []).append(school)
      province_aliases[province] = province
    if province_short and province:
      province_aliases[province_short] = province

  return {
    "meta": data.get("meta") or {},
    "schools": schools,
    "by_code": by_code,
    "by_name": by_name,
    "province_to_schools": province_to_schools,
    "province_aliases": province_aliases,
    "school_names": sorted(by_name.keys(), key=len, reverse=True),
  }


def load_province_index():
  provinces = load_json(PROVINCES_DATA_PATH, [])
  by_code = {}
  alias_to_code = {}
  for province in provinces:
    code = province.get("code")
    if not code:
      continue
    by_code[code] = province
    for key in ("name", "shortName"):
      alias = province.get(key)
      if alias:
        alias_to_code[alias] = code
  return {
    "items": provinces,
    "by_code": by_code,
    "alias_to_code": alias_to_code,
  }


def load_major_index():
  index_data = load_json(MAJORS_INDEX_PATH, {"meta": {}, "majors": []})
  majors = index_data.get("majors") or []
  by_code = {}
  by_name = {}
  for major in majors:
    code = str(major.get("code") or "")
    name = str(major.get("name") or "")
    if code:
      by_code[code] = major
    if name:
      by_name[name] = major

  rankings = {}
  if MAJOR_RANKINGS_DIR.exists():
    for path in sorted(MAJOR_RANKINGS_DIR.glob("*.json")):
      data = load_json(path, {})
      code = str(data.get("majorCode") or path.stem)
      rankings[code] = {
        "majorCode": code,
        "majorName": data.get("majorName"),
        "discipline": data.get("discipline"),
        "majorClass": data.get("majorClass"),
        "year": data.get("year"),
        "source": data.get("source"),
        "sourceUrl": data.get("sourceUrl"),
        "records": data.get("records") or [],
      }

  return {
    "meta": index_data.get("meta") or {},
    "majors": majors,
    "by_code": by_code,
    "by_name": by_name,
    "major_names": sorted(by_name.keys(), key=len, reverse=True),
    "rankings": rankings,
  }


def load_score_index():
  scores = {}
  if not SCORES_DIR.exists():
    return scores
  for path in sorted(SCORES_DIR.glob("*/*.json")):
    province_code = path.parent.name
    year = path.stem
    data = load_json(path, {})
    records = data.get("records") or []
    scores.setdefault(province_code, {})[year] = {
      "meta": data.get("meta") or {},
      "records": records,
    }
  return scores


def available_score_years(scores):
  years = sorted({
    year
    for by_year in scores.values()
    for year in by_year.keys()
    if re.fullmatch(r"20\d{2}", str(year))
  })
  return years


def resolve_year_alias_value(value, score_years):
  value = str(value or "").strip()
  if not value:
    return ""
  if re.fullmatch(r"20\d{2}", value):
    return value
  if not score_years:
    return ""

  latest = score_years[-1]
  if value == "latest":
    return latest
  if value == "previous":
    return score_years[-2] if len(score_years) >= 2 else latest
  if value == "two_years_ago":
    return score_years[-3] if len(score_years) >= 3 else latest
  return value


def canonical_province_name(value, provinces):
  value = str(value or "").strip()
  if not value:
    return ""
  for province in provinces["items"]:
    if value in {
      str(province.get("code") or ""),
      str(province.get("name") or ""),
      str(province.get("shortName") or ""),
    }:
      return province.get("name") or ""
  return value


def load_alias_index(schools, provinces, scores):
  alias_data = load_json(ALIASES_DATA_PATH, {})
  score_years = available_score_years(scores)

  school_aliases = {}
  for name in schools["by_name"].keys():
    school_aliases[name] = name
  school_aliases.update(SCHOOL_ALIASES)
  school_aliases.update(alias_data.get("schools") or {})
  school_aliases = {
    str(alias): str(name)
    for alias, name in school_aliases.items()
    if alias and name and str(name) in schools["by_name"]
  }

  province_aliases = {}
  for province in provinces["items"]:
    name = province.get("name")
    short_name = province.get("shortName")
    code = province.get("code")
    for alias in (name, short_name, code):
      if alias and name:
        province_aliases[str(alias)] = str(name)
  for alias, name in (alias_data.get("provinces") or {}).items():
    canonical = canonical_province_name(name, provinces)
    if alias and canonical:
      province_aliases[str(alias)] = canonical

  province_contexts = {}
  templates = alias_data.get("provinceContextTemplates") or []
  for province in provinces["items"]:
    name = province.get("name")
    short_name = province.get("shortName") or name
    code = province.get("code") or ""
    if not name:
      continue
    for template in templates:
      alias = str(template).format(name=name, shortName=short_name, code=code)
      if alias:
        province_contexts[alias] = name
  for alias, name in (alias_data.get("provinceContexts") or {}).items():
    canonical = canonical_province_name(name, provinces)
    if alias and canonical:
      province_contexts[str(alias)] = canonical

  year_aliases = {}
  for alias, value in (alias_data.get("years") or {}).items():
    resolved = resolve_year_alias_value(value, score_years)
    if alias and resolved:
      year_aliases[str(alias)] = resolved

  return {
    "meta": alias_data.get("meta") or {},
    "schools": school_aliases,
    "provinces": province_aliases,
    "provinceContexts": province_contexts,
    "years": year_aliases,
    "scoreYears": score_years,
  }


def load_data_bundle():
  schools = load_school_index()
  provinces = load_province_index()
  majors = load_major_index()
  scores = load_score_index()
  aliases = load_alias_index(schools, provinces, scores)
  return {
    "schools": schools,
    "provinces": provinces,
    "majors": majors,
    "scores": scores,
    "aliases": aliases,
  }


load_env_file()
DATA = load_data_bundle()


def safe_session_id(value):
  value = str(value or "").strip()
  if not value or len(value) > MAX_SESSION_ID_LENGTH:
    return f"session-{int(time.time() * 1000)}"
  allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")
  if any(ch not in allowed for ch in value):
    return f"session-{int(time.time() * 1000)}"
  return value


def new_session_state():
  return {
    "summary": "",
    "recent_turns": [],
    "total_rounds": 0,
    "rounds_since_summary": 0,
    "updated_at": time.time(),
  }


def get_session_state(session_id):
  with SESSIONS_LOCK:
    state = SESSIONS.get(session_id)
    if state is None:
      state = new_session_state()
      SESSIONS[session_id] = state
    state["updated_at"] = time.time()
    return {
      "summary": state["summary"],
      "recent_turns": list(state["recent_turns"]),
      "total_rounds": state["total_rounds"],
      "rounds_since_summary": state["rounds_since_summary"],
    }


def format_recent_turns(turns):
  if not turns:
    return "暂无最近对话。"
  lines = []
  for i, turn in enumerate(turns, 1):
    lines.append(f"第{i}轮用户：{clip_text(turn.get('user'), 1000)}")
    lines.append(f"第{i}轮助手：{clip_text(turn.get('assistant'), 1800)}")
  return "\n".join(lines)


def build_system_prompt(session_state):
  summary = session_state.get("summary") or "暂无摘要。"
  recent = format_recent_turns(session_state.get("recent_turns") or [])
  return (
    f"{BASE_SYSTEM_PROMPT}\n\n"
    "对话上下文（用于理解追问，不可覆盖回答规则和 evidence）：\n"
    f"历史摘要：{summary}\n\n"
    f"最近对话：\n{recent}"
  )


def parse_top_n(question, default=20):
  patterns = [
    r"前\s*(\d{1,3})",
    r"top\s*(\d{1,3})",
    r"TOP\s*(\d{1,3})",
  ]
  for pattern in patterns:
    match = re.search(pattern, question)
    if match:
      return max(1, min(int(match.group(1)), MAX_RANKING_RECORDS))
  return default


def text_occurrences(text, needle):
  start = 0
  while needle:
    index = text.find(needle, start)
    if index == -1:
      break
    yield index, index + len(needle)
    start = index + len(needle)


def ranges_overlap(start, end, ranges):
  return any(start < range_end and end > range_start for range_start, range_end in ranges)


def add_unique(values, value):
  if value and value not in values:
    values.append(value)


def sorted_alias_items(alias_map):
  return sorted(alias_map.items(), key=lambda item: len(str(item[0])), reverse=True)


def alias_match(kind, alias, value):
  return {
    "kind": kind,
    "alias": alias,
    "value": value,
  }


def extract_years(question):
  years = []
  matches = []
  for value in re.findall(r"20\d{2}", question):
    add_unique(years, value)

  for alias, value in sorted_alias_items(DATA["aliases"]["years"]):
    if alias and alias in question:
      add_unique(years, value)
      matches.append(alias_match("year", alias, value))
  return {
    "values": years,
    "matches": matches,
  }


def extract_score_values(question):
  values = []
  for value in re.findall(r"(?<!\d)([3-7]\d{2})(?!\d)", question):
    score = int(value)
    if 300 <= score <= 750 and score not in values:
      values.append(score)
  return values


def extract_types(question):
  type_flags = []
  checks = [
    ("985", "is985", True),
    ("211", "is211", True),
    ("双一流", "isDoubleFirstClass", True),
    ("军队", "isMilitary", True),
    ("军事", "isMilitary", True),
    ("民办", "natures", "民办"),
    ("师范", "natures", "师范"),
    ("医学", "natures", "医学"),
    ("财经", "natures", "财经"),
    ("政法", "natures", "政法"),
    ("艺术", "natures", "艺术"),
    ("民族", "natures", "民族"),
    ("研究型", "natures", "研究型"),
  ]
  for keyword, field, value in checks:
    if keyword in question and (field, value) not in type_flags:
      type_flags.append((field, value))
  return type_flags


def extract_regions(question):
  matches = []
  for alias in sorted(REGION_PROVINCES.keys(), key=len, reverse=True):
    if alias in question:
      for province in REGION_PROVINCES[alias]:
        add_unique(matches, province)
  return matches


def extract_provinces(question, school_spans):
  provinces = extract_regions(question)
  alias_matches = []

  for alias, province in sorted_alias_items(DATA["aliases"]["provinceContexts"]):
    if not alias:
      continue
    for start, end in text_occurrences(question, alias):
      add_unique(provinces, province)
      alias_matches.append(alias_match("province_context", alias, province))
      break

  for alias, province in sorted_alias_items(DATA["aliases"]["provinces"]):
    if not alias:
      continue
    for start, end in text_occurrences(question, alias):
      if ranges_overlap(start, end, school_spans):
        continue
      add_unique(provinces, province)
      alias_matches.append(alias_match("province", alias, province))
      break

  return {
    "values": provinces,
    "matches": alias_matches,
  }


def extract_schools(question):
  schools = []
  alias_matches = []
  spans = []
  by_name = DATA["schools"]["by_name"]
  for alias, school_name in sorted_alias_items(DATA["aliases"]["schools"]):
    if not alias or school_name not in by_name:
      continue
    for start, end in text_occurrences(question, alias):
      if ranges_overlap(start, end, spans):
        continue
      add_unique(schools, school_name)
      spans.append((start, end))
      if alias != school_name:
        alias_matches.append(alias_match("school", alias, school_name))
      break
    if len(schools) >= 10:
      break
  return {
    "values": schools,
    "matches": alias_matches,
    "spans": spans,
  }


def extract_majors(question):
  matches = []
  by_name = DATA["majors"]["by_name"]
  for name in DATA["majors"]["major_names"]:
    if name and name in question and name not in matches:
      matches.append(name)
    if len(matches) >= MAX_MAJOR_MATCHES:
      return matches
  if matches:
    return matches

  for keyword in MAJOR_KEYWORDS:
    if keyword not in question:
      continue
    candidates = [
      major for major in DATA["majors"]["majors"]
      if keyword in str(major.get("name") or "")
    ]
    candidates.sort(key=lambda m: (not m.get("ranked"), -(m.get("schoolCount") or 0), len(m.get("name") or "")))
    for major in candidates[:MAX_MAJOR_MATCHES]:
      name = major.get("name")
      if name and name in by_name and name not in matches:
        matches.append(name)
      if len(matches) >= MAX_MAJOR_MATCHES:
        return matches
  return matches


def analyze_question(question, session_state):
  text = question.strip()
  school_result = extract_schools(text)
  province_result = extract_provinces(text, school_result["spans"])
  year_result = extract_years(text)
  return {
    "question": text,
    "topN": parse_top_n(text),
    "years": year_result["values"],
    "scores": extract_score_values(text),
    "provinces": province_result["values"],
    "schools": school_result["values"],
    "majors": extract_majors(text),
    "typeFilters": extract_types(text),
    "wantsRanking": any(k in text for k in ["排名", "排行", "前", "top", "TOP", "专业"]),
    "wantsScore": any(k in text for k in ["分", "分数", "位次", "录取", "投档", "能上"]),
    "wantsCount": any(k in text for k in ["多少", "几所", "数量", "统计", "分布"]),
    "aliasMatches": (school_result["matches"] + province_result["matches"] + year_result["matches"])[:80],
    "hasContextSummary": bool(session_state.get("summary")),
    "recentTurnCount": len(session_state.get("recent_turns") or []),
  }


def school_matches_type(school, type_filters):
  for field, expected in type_filters:
    if field == "natures":
      if expected not in (school.get("natures") or []):
        return False
    elif bool(school.get(field)) != bool(expected):
      return False
  return True


def summarize_school(school):
  return {
    "code": school.get("code"),
    "name": school.get("name"),
    "province": school.get("province"),
    "location": school.get("location"),
    "department": school.get("department"),
    "level": school.get("level"),
    "schoolType": school.get("schoolType"),
    "natures": school.get("natures") or [],
    "is985": bool(school.get("is985")),
    "is211": bool(school.get("is211")),
    "isDoubleFirstClass": bool(school.get("isDoubleFirstClass")),
    "isMilitary": bool(school.get("isMilitary")),
    "website": school.get("website"),
    "intro": clip_text(school.get("intro"), 180),
    "majors": (school.get("majors") or [])[:10],
  }


def collect_school_evidence(analysis):
  schools_index = DATA["schools"]
  schools = schools_index["schools"]
  selected = []
  notes = []

  if analysis["schools"]:
    for name in analysis["schools"]:
      school = schools_index["by_name"].get(name)
      if school and school not in selected:
        selected.append(school)
  else:
    if analysis["wantsScore"] and not analysis["typeFilters"] and not analysis["wantsCount"]:
      notes.append("分数/位次查询由 scores evidence 提供候选记录，未展开省内学校明细。")
      return {
        "matchedCount": 0,
        "providedCount": 0,
        "schools": [],
        "notes": notes,
      }
    if not analysis["provinces"] and not analysis["typeFilters"]:
      if analysis["wantsCount"]:
        notes.append("总量统计问题仅提供匹配数量，不展开全量学校明细。")
        return {
          "matchedCount": len(schools),
          "providedCount": 0,
          "schools": [],
          "notes": notes,
        }
      notes.append("未识别到具体学校、省份或学校类型，未提供学校明细。")
      return {
        "matchedCount": 0,
        "providedCount": 0,
        "schools": [],
        "notes": notes,
      }
    selected = list(schools)
    if analysis["provinces"]:
      province_set = set(analysis["provinces"])
      selected = [s for s in selected if s.get("province") in province_set]
    if analysis["typeFilters"]:
      selected = [s for s in selected if school_matches_type(s, analysis["typeFilters"])]

  total_matches = len(selected)
  # 名单类问题优先保留 name/province 轻量字段，尽量覆盖全部匹配结果
  list_query = analysis["wantsCount"] or (
    analysis["typeFilters"] and not analysis["wantsScore"] and not analysis["wantsRanking"]
  )
  if list_query and total_matches > MAX_SCHOOL_EVIDENCE:
    compact = [
      {
        "code": s.get("code"),
        "name": s.get("name"),
        "province": s.get("province"),
        "schoolType": s.get("schoolType"),
        "is985": bool(s.get("is985")),
        "is211": bool(s.get("is211")),
        "isDoubleFirstClass": bool(s.get("isDoubleFirstClass")),
      }
      for s in selected
    ]
    return {
      "matchedCount": total_matches,
      "providedCount": len(compact),
      "schools": compact,
      "notes": notes + [f"名单查询已提供全部 {total_matches} 所匹配院校的精简字段。"],
    }

  selected = selected[:MAX_SCHOOL_EVIDENCE]
  if total_matches > len(selected):
    notes.append(
      f"学校匹配结果共 {total_matches} 所，仅提供前 {len(selected)} 所明细给模型；"
      "结果按数据顺序截断，不代表其余省份没有匹配院校。如需某区域/省份名单，请明确地区后重问。"
    )

  return {
    "matchedCount": total_matches,
    "providedCount": len(selected),
    "schools": [summarize_school(school) for school in selected],
    "notes": notes,
  }


def collect_province_evidence(analysis, school_evidence):
  provinces = analysis["provinces"]
  if not provinces and not analysis["wantsCount"]:
    return {"items": []}

  items = []
  target_provinces = provinces or sorted(DATA["schools"]["province_to_schools"].keys())
  include_school_names = not analysis["wantsScore"] or analysis["wantsCount"]
  for province in target_provinces[:20]:
    schools = DATA["schools"]["province_to_schools"].get(province, [])
    if analysis["typeFilters"]:
      schools = [s for s in schools if school_matches_type(s, analysis["typeFilters"])]
    type_counts = {}
    nature_counts = {}
    for school in schools:
      school_type = school.get("schoolType") or "未知"
      type_counts[school_type] = type_counts.get(school_type, 0) + 1
      for nature in school.get("natures") or []:
        nature_counts[nature] = nature_counts.get(nature, 0) + 1
    items.append({
      "province": province,
      "schoolCount": len(schools),
      "typeCounts": type_counts,
      "natureCounts": nature_counts,
      "schoolNames": [s.get("name") for s in schools[:MAX_PROVINCE_SCHOOL_NAMES]] if include_school_names else [],
    })

  return {"items": items}


def summarize_major(major):
  return {
    "code": major.get("code"),
    "name": major.get("name"),
    "discipline": major.get("discipline"),
    "majorClass": major.get("majorClass"),
    "schoolCount": major.get("schoolCount"),
    "ranked": bool(major.get("ranked")),
  }


def collect_major_evidence(analysis):
  majors_index = DATA["majors"]
  evidence = []
  notes = []
  school_names = set(analysis["schools"])
  top_n = min(analysis["topN"], MAX_RANKING_RECORDS)

  for name in analysis["majors"]:
    major = majors_index["by_name"].get(name)
    if not major:
      continue
    code = str(major.get("code") or "")
    ranking = majors_index["rankings"].get(code)
    item = {
      "major": summarize_major(major),
      "ranking": None,
    }
    if ranking:
      records = ranking.get("records") or []
      selected_records = records[:top_n]
      related_school_records = []
      if school_names:
        related_school_records = [
          record for record in records
          if record.get("schoolName") in school_names
        ][:MAX_RANKING_RECORDS]
      item["ranking"] = {
        "year": ranking.get("year"),
        "source": ranking.get("source"),
        "sourceUrl": ranking.get("sourceUrl"),
        "totalRecords": len(records),
        "topRecords": selected_records,
        "relatedSchoolRecords": related_school_records,
      }
    elif major.get("ranked"):
      notes.append(f"{name} 标记为有排名，但未找到对应排名文件。")
    else:
      notes.append(f"{name} 暂无专业排名。")
    evidence.append(item)

  if not evidence and analysis["wantsRanking"]:
    suggestions = [
      summarize_major(major)
      for major in majors_index["majors"]
      if major.get("ranked")
    ][:30]
    notes.append("未识别到具体专业，提供部分可排名专业作为参考。")
    return {"items": [], "suggestions": suggestions, "notes": notes}

  return {"items": evidence, "suggestions": [], "notes": notes}


def province_to_score_code(province):
  for item in DATA["provinces"]["items"]:
    if item.get("name") == province or item.get("shortName") == province:
      return item.get("code")
  return None


def collect_score_evidence(analysis):
  if not analysis["wantsScore"] and not analysis["scores"]:
    return {"items": [], "notes": []}

  notes = []
  if not analysis["provinces"]:
    notes.append("分数/位次查询需要明确考生所在省份。")
    return {"items": [], "notes": notes, "missingFields": ["province"]}

  year = analysis["years"][0] if analysis["years"] else "2025"
  score_value = analysis["scores"][0] if analysis["scores"] else None
  school_names = set(analysis["schools"])
  type_filters = analysis["typeFilters"]
  items = []

  for province in analysis["provinces"][:3]:
    score_code = province_to_score_code(province)
    by_year = DATA["scores"].get(score_code or "", {})
    score_data = by_year.get(year)
    if not score_data:
      notes.append(f"{province} 暂无 {year} 年录取分数据。")
      continue

    records = list(score_data.get("records") or [])
    if school_names:
      records = [record for record in records if record.get("schoolName") in school_names]
    if type_filters:
      allowed_codes = {
        school.get("code") for school in DATA["schools"]["schools"]
        if school_matches_type(school, type_filters)
      }
      records = [record for record in records if record.get("schoolCode") in allowed_codes]
    if score_value is not None:
      records = [
        record for record in records
        if isinstance(record.get("minScore"), (int, float))
        and abs(record.get("minScore") - score_value) <= SCORE_AROUND_DELTA
      ]
      records.sort(key=lambda record: abs(record.get("minScore") - score_value))

    items.append({
      "province": province,
      "year": year,
      "queryScore": score_value,
      "totalMatches": len(records),
      "records": records[:MAX_SCORE_RECORDS],
    })

  return {"items": items, "notes": notes, "missingFields": []}


def build_evidence(question, session_state):
  analysis = analyze_question(question, session_state)
  school_evidence = collect_school_evidence(analysis)
  evidence = {
    "meta": {
      "mode": "retrieval_evidence_only",
      "schoolData": DATA["schools"]["meta"],
      "majorRanking": DATA["majors"]["meta"],
      "limits": {
        "maxSchools": MAX_SCHOOL_EVIDENCE,
        "maxRankingRecords": MAX_RANKING_RECORDS,
        "maxScoreRecords": MAX_SCORE_RECORDS,
      },
    },
    "queryAnalysis": analysis,
    "schools": school_evidence,
    "provinces": collect_province_evidence(analysis, school_evidence),
    "majors": collect_major_evidence(analysis),
    "scores": collect_score_evidence(analysis),
  }
  return evidence


def build_messages(question, session_state, evidence):
  user_prompt = (
    "以下是后端根据用户问题和会话上下文检索出的 evidence JSON。"
    "请只基于 evidence 回答，不要使用未提供的数据。\n\n"
    f"【evidence JSON】\n{compact_json(evidence)}\n\n"
    f"用户问题：{question}"
  )
  return [
    {"role": "system", "content": build_system_prompt(session_state)},
    {"role": "user", "content": user_prompt},
  ]


def get_deepseek_config_error(api_key):
  if not api_key:
    return "服务端未配置 DEEPSEEK_API_KEY，请在 .env 或启动命令中配置。"
  if not api_key.startswith("sk-"):
    return "DEEPSEEK_API_KEY 格式不正确，请确认 .env 中填入的是以 sk- 开头的真实 DeepSeek API Key。"
  if (
    any(ord(ch) < 33 or ord(ch) > 126 for ch in api_key)
    or api_key in {"你的 DeepSeek API Key", "your_deepseek_api_key", "<your_deepseek_api_key>"}
  ):
    return "DEEPSEEK_API_KEY 格式不正确，请确认 .env 中填入的是以 sk- 开头的真实 DeepSeek API Key。"
  return ""


def request_deepseek(messages, temperature=0.2, timeout=90, max_tokens=None):
  api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
  config_error = get_deepseek_config_error(api_key)
  if config_error:
    return {
      "status": 500,
      "payload": {"error": config_error},
    }

  model = os.environ.get("DEEPSEEK_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
  body = {
    "model": model,
    "messages": messages,
    "temperature": temperature,
    "stream": False,
  }
  if max_tokens:
    body["max_tokens"] = max_tokens
  req = urllib.request.Request(
    DEEPSEEK_API_URL,
    data=compact_json(body).encode("utf-8"),
    headers={
      "Authorization": f"Bearer {api_key}",
      "Content-Type": "application/json",
    },
    method="POST",
  )

  try:
    with urllib.request.urlopen(req, timeout=timeout) as resp:
      data = json.loads(resp.read().decode("utf-8"))
  except urllib.error.HTTPError as exc:
    details = exc.read().decode("utf-8", errors="replace")
    return {
      "status": exc.code,
      "payload": {
        "error": "DeepSeek 接口返回错误。",
        "details": details[:1000],
      },
    }
  except urllib.error.URLError as exc:
    return {
      "status": 502,
      "payload": {
        "error": "无法连接 DeepSeek 接口。",
        "details": str(exc.reason),
      },
    }
  except (TimeoutError, socket.timeout):
    return {
      "status": 504,
      "payload": {
        "error": "DeepSeek 接口响应超时，请稍后重试。",
      },
    }
  except Exception as exc:
    return {
      "status": 500,
      "payload": {
        "error": "服务端处理智能问答请求失败。",
        "details": str(exc)[:1000],
      },
    }

  content = (
    data.get("choices", [{}])[0]
    .get("message", {})
    .get("content", "")
    .strip()
  )
  if not content:
    return {
      "status": 502,
      "payload": {
        "error": "DeepSeek 接口未返回有效内容。",
      },
    }

  return {
    "status": 200,
    "payload": {
      "content": content,
      "model": model,
    },
  }


def deepseek_chat(question, session_state):
  evidence = build_evidence(question, session_state)
  evidence_text_length = len(compact_json(evidence))
  result = request_deepseek(build_messages(question, session_state, evidence), temperature=0.2, timeout=90)
  if result["status"] != 200:
    result["payload"]["evidenceStats"] = {
      "chars": evidence_text_length,
      "schoolMatches": evidence["schools"]["matchedCount"],
      "majorMatches": len(evidence["majors"]["items"]),
      "scoreGroups": len(evidence["scores"]["items"]),
    }
    return result
  return {
    "status": 200,
    "payload": {
      "answer": result["payload"]["content"],
      "model": result["payload"]["model"],
      "evidenceStats": {
        "chars": evidence_text_length,
        "schoolMatches": evidence["schools"]["matchedCount"],
        "majorMatches": len(evidence["majors"]["items"]),
        "scoreGroups": len(evidence["scores"]["items"]),
      },
    },
  }


def summarize_session_if_needed(session_id):
  with SESSIONS_LOCK:
    state = SESSIONS.get(session_id)
    if not state or state["rounds_since_summary"] < SUMMARY_EVERY_ROUNDS:
      return False
    previous_summary = state["summary"]
    turns_to_summarize = list(state["recent_turns"])

  transcript = format_recent_turns(turns_to_summarize)
  messages = [
    {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
    {
      "role": "user",
      "content": (
        f"已有历史摘要：{previous_summary or '暂无'}\n\n"
        f"最近 {len(turns_to_summarize)} 轮对话：\n{transcript}\n\n"
        "请输出更新后的压缩上下文摘要。"
      ),
    },
  ]
  result = request_deepseek(messages, temperature=0.1, timeout=60, max_tokens=900)
  if result["status"] != 200:
    with SESSIONS_LOCK:
      state = SESSIONS.get(session_id)
      if state and len(state["recent_turns"]) > MAX_RECENT_TURNS_ON_SUMMARY_FAILURE:
        state["recent_turns"] = state["recent_turns"][-MAX_RECENT_TURNS_ON_SUMMARY_FAILURE:]
    return False

  with SESSIONS_LOCK:
    state = SESSIONS.get(session_id)
    if not state:
      return False
    state["summary"] = result["payload"]["content"]
    state["recent_turns"] = state["recent_turns"][-RECENT_ROUNDS_AFTER_SUMMARY:] if RECENT_ROUNDS_AFTER_SUMMARY else []
    state["rounds_since_summary"] = 0
    state["updated_at"] = time.time()
  return True


def record_session_turn(session_id, question, answer):
  with SESSIONS_LOCK:
    state = SESSIONS.setdefault(session_id, new_session_state())
    state["recent_turns"].append({
      "user": clip_text(question, 1200),
      "assistant": clip_text(answer, 2400),
    })
    state["total_rounds"] += 1
    state["rounds_since_summary"] += 1
    state["updated_at"] = time.time()
    total_rounds = state["total_rounds"]
    rounds_since_summary = state["rounds_since_summary"]
  summary_updated = summarize_session_if_needed(session_id)
  return {
    "totalRounds": total_rounds,
    "roundsSinceSummary": 0 if summary_updated else rounds_since_summary,
    "summaryUpdated": summary_updated,
  }


class SchoolMapHandler(SimpleHTTPRequestHandler):
  def api_path(self):
    return urllib.parse.urlparse(self.path).path

  def end_headers(self):
    self.send_header("X-Content-Type-Options", "nosniff")
    super().end_headers()

  def do_OPTIONS(self):
    if self.api_path() == "/api/chat":
      self.send_response(204)
      self.send_header("Access-Control-Allow-Origin", self.headers.get("Origin", "*"))
      self.send_header("Access-Control-Allow-Headers", "Content-Type")
      self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
      self.end_headers()
      return
    self.send_error(404)

  def do_POST(self):
    if self.api_path() != "/api/chat":
      self.send_error(404)
      return

    try:
      length = int(self.headers.get("Content-Length", "0"))
    except ValueError:
      self.write_json(400, {"error": "请求长度无效。"})
      return
    if length <= 0 or length > MAX_REQUEST_BYTES:
      self.write_json(400, {"error": "问题为空或请求过大。"})
      return

    try:
      payload = json.loads(self.rfile.read(length).decode("utf-8"))
    except json.JSONDecodeError:
      self.write_json(400, {"error": "请求 JSON 格式无效。"})
      return

    question = str(payload.get("question", "")).strip()
    if not question:
      self.write_json(400, {"error": "请输入问题。"})
      return
    if len(question) > 1000:
      self.write_json(400, {"error": "问题过长，请控制在 1000 字以内。"})
      return

    session_id = safe_session_id(payload.get("sessionId"))
    session_state = get_session_state(session_id)
    result = deepseek_chat(question, session_state)
    if result["status"] == 200:
      session_meta = record_session_turn(session_id, question, result["payload"]["answer"])
      result["payload"]["sessionId"] = session_id
      result["payload"]["session"] = session_meta
    else:
      result["payload"]["sessionId"] = session_id
    self.write_json(result["status"], result["payload"])

  def write_json(self, status, payload):
    data = compact_json(payload).encode("utf-8")
    self.send_response(status)
    self.send_header("Content-Type", "application/json; charset=utf-8")
    self.send_header("Content-Length", str(len(data)))
    self.send_header("Access-Control-Allow-Origin", self.headers.get("Origin", "*"))
    self.end_headers()
    self.wfile.write(data)


def main():
  port = int(os.environ.get("PORT", "8080"))
  os.chdir(ROOT)
  server = ThreadingHTTPServer(("", port), SchoolMapHandler)
  print(f"Serving school map on http://localhost:{port}")
  print("Chat endpoint: POST /api/chat")
  print(f"Loaded {len(DATA['schools']['schools'])} schools")
  print(f"Loaded {len(DATA['majors']['majors'])} majors and {len(DATA['majors']['rankings'])} ranking files")
  try:
    server.serve_forever()
  except KeyboardInterrupt:
    print("\nServer stopped")


if __name__ == "__main__":
  try:
    main()
  except Exception as exc:
    print(f"启动失败：{exc}", file=sys.stderr)
    sys.exit(1)
