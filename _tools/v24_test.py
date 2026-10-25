# -*- coding: utf-8 -*-
"""v1.14 验收：新闻出题——全部离线（解析与出题为纯函数，不访问外网）+ 参数校验分支。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.services.ielts import IeltsService  # noqa: E402

PASS, FAIL = [], []


def check(name, ok):
    (PASS if ok else FAIL).append(name)
    print(("  ✓ " if ok else "  ✗ ") + name)


SVC = IeltsService.__new__(IeltsService)   # 只用类方法/静态方法，不连库

print("== 1. 出题纯函数 _gen_quiz ==")
TEXT = ("Many people struggle to get a good night's sleep. Researchers believe "
        "that screen time before bed reduces the quality of rest significantly. "
        "Adults typically need between seven and nine hours of sleep every night. "
        "Sleep deprivation affects memory, concentration, and emotional balance. "
        "Experts recommend keeping the bedroom cool, dark, and quiet. Avoiding "
        "caffeine in the evening helps the body prepare for rest. Regular exercise "
        "during the day improves sleep quality dramatically. Reading a paper book "
        "calms the mind better than scrolling through social media feeds.") * 2
qs = SVC._gen_quiz(TEXT, n=8)
check("生成 8 题", qs and len(qs) == 8)
check("通过 _validate_set", SVC._validate_set(
    {"subject": "listening", "title": "t", "sections": [{"material": TEXT, "questions": qs}]}))
blanks = [q for q in qs if q["type"] == "blank"]
choices = [q for q in qs if q["type"] == "choice"]
check("blank 与 choice 混合", blanks and choices)
check("blank 答案来自原句", all(
    q["answer"] in q["explain"].replace("原句：", "").lower() for q in blanks))
check("choice 干扰项不含正确词", all(
    q["options"].count(q["options"][ord(q["answer"]) - 65]) == 1 for q in choices))
check("choice 答案字母合法", all(q["answer"] in "ABCD" for q in choices))
check("题干含挖空标记", all("______" in q["stem"] for q in qs))
check("无停用词被选为答案", all(
    q["answer"].lower() not in SVC._STOPWORDS for q in qs))

print("== 2. HTML 解析纯函数 ==")
h = '<div data-feature-item="/features/6-minute-english_2026/ep-261022" class="x"></div>' \
    '<div data-feature-item="/features/6-minute-english_2025/ep-250315"></div>' \
    '<div data-feature-item="/features/6-minute-english_2026/ep-261022"></div>'
eps = SVC._parse_bbc_le_list(h)
check("BBC LE 列表去重有序", len(eps) == 2 and eps[0]["id"] == "ep-261022"
      and eps[0]["url"].startswith("https://www.bbc.co.uk/learningenglish"))

detail_html = '<html><script>bad()</script><p>short</p>' \
    '<a href="https://downloads.bbc.co.uk/learningenglish/features/6min/261022_x_download.mp3">dl</a>' \
    'This is not a word-for-word transcript.<p>Neil: Hello and welcome to Six Minute English, ' \
    'the programme where we discuss something interesting every week.</p>' \
    '<p>Phil: And I am Phil, and today we are talking about sleep and dreams.</p></html>'
det = SVC._parse_bbc_le_detail(detail_html)
check("BBC LE mp3 提取", det["mp3"] and det["mp3"].endswith(".mp3"))
check("BBC LE 文稿提取（去脚本/短行）", any("Six Minute English" in l for l in det["text"].split("\n"))
      and "bad()" not in det["text"])

nh = '<a href="/news/articles/c95ynd587ynzo">A</a><a href="/news/articles/c6y93ylpl5p2o">B</a>'
check("BBC News 列表", len(SVC._parse_bbc_news_list(nh)) == 2)

vh = '<a href="/a/lets-learn-english-lesson-one/3111026.html">course</a>' \
     '<a href="/a/some-news-title-here/7777123.html">News title line here</a>' \
     '<a href="/a/some-news-title-here/7777123.html">dup</a>'
vlist = SVC._parse_voa_list(vh)
check("VOA 列表过滤课程页+去重", len(vlist) == 1 and "7777123" in vlist[0]["id"])

check("VOA 正文提取", SVC._parse_voa_detail(
    '<p>' + 'Scientists discovered a remarkable pattern in ocean currents. ' * 2 + '</p>'
    '<p>Download the document below for a lesson plan.</p>')["text"].startswith("Scientists"))

check("标题提取", SVC._extract_title(
    '<title>What should you eat for a better night&apos;s sleep - BBC Learning English</title>')
    == "What should you eat for a better night's sleep")
check("实体解码", any("sleep & dreams research" in l for l in SVC._strip_html(
    "<p>sleep &amp; dreams research shows clear patterns in memory</p>")))

print("== 3. 服务编排参数校验（无外网） ==")
from app.core.registry import AppContext  # noqa: E402
from app.core.db import Database
from app.core.events import EventBus
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
ctx = AppContext(root=ROOT, data_dir=ROOT / "data",
                 config={}, db=Database(ROOT / "data" / "workbench.db"), events=EventBus(),
                 ai=None)
svc = IeltsService(ctx)
s, r = svc.news_fetch("bad-kind")
check("非法 kind → 400", s == 400)
s, r = svc.news_fetch("reading", "bad-src")
check("非法 source → 400", s == 400)

print(f"\n===== {len(PASS)} passed, {len(FAIL)} failed =====")
if FAIL:
    print("失败项：", FAIL)
    raise SystemExit(1)
