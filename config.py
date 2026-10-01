# -*- coding: utf-8 -*-
"""全局配置：数据源、路径、清洗与可视化所需常量。"""

import os
import sys

# ---------------------------------------------------------------- 控制台编码
# Windows 控制台默认 GBK，输出中文与符号易抛 UnicodeEncodeError，
# 这里统一切换为 UTF-8，保证日志稳定。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001 - 非 TTY 或已重定向时忽略
        pass

# ---------------------------------------------------------------- 路径配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
WEB_DIR = os.path.join(BASE_DIR, "web")

DB_PATH = os.path.join(DATA_DIR, "announcements.db")
CSV_PATH = os.path.join(DATA_DIR, "announcements.csv")
EXCEL_PATH = os.path.join(DATA_DIR, "announcements.xlsx")

for _d in (DATA_DIR, WEB_DIR):
    os.makedirs(_d, exist_ok=True)

# ---------------------------------------------------------------- 标的信息
STOCK_CODE = "600519"
STOCK_NAME = "贵州茅台"
COMPANY_NAME = "贵州茅台酒股份有限公司"
# 用于从资讯类数据源中筛出与本标的相关的条目
STOCK_KEYWORDS = ["贵州茅台", "茅台", "600519"]

# ---------------------------------------------------------------- 抓取配置
# 三大数据源按优先级排列，前一个失败自动降级到后一个
DATA_SOURCES = ["cninfo", "sina", "mock"]

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/json,application/xhtml+xml,*/*",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

REQUEST_TIMEOUT = 20      # 单次请求超时（秒）
REQUEST_RETRY = 3         # 失败重试次数
REQUEST_DELAY = (0.6, 1.5)  # 每次请求之间的随机休眠区间，避免被封 IP
PAGE_SIZE = 30            # 巨潮每页条数
MAX_PAGES = 20            # 最多翻页数，控制抓取规模

CNINFO_QUERY_URL = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
CNINFO_REFERER = "http://www.cninfo.com.cn/new/commonUrl?url=disclosure/list/notice"
CNINFO_STATIC_PREFIX = "http://static.cninfo.com.cn/"

SINA_ANNOUNCE_URL = (
    "https://vip.stock.finance.sina.com.cn/corp/go.php/vCB_AllNewsStock/"
    "symbol/sh{code}.phtml"
)

# 抓取的时间窗口（留空则抓取全部历史）
DATE_FROM = "2021-01-01"
DATE_TO = "2026-12-31"

# ---------------------------------------------------------------- 公告分类
# 依据标题关键词归类，顺序敏感：越靠前优先级越高
CATEGORY_RULES = [
    ("财务报告", ["年度报告", "半年度报告", "季度报告", "一季报", "三季报", "中报",
                  "业绩快报", "业绩预告", "财务报表", "审计报告", "财务报告"]),
    ("分红配股", ["分红", "派息", "送股", "转增", "配股", "权益分派", "现金红利"]),
    ("股东大会", ["股东大会", "股东会", "股东大会决议"]),
    ("治理变动", ["董事会", "监事会", "董事", "监事", "高管", "独立董事", "聘任",
                  "辞职", "选举", "章程", "治理", "人事", "决议", "会议"]),
    ("股权变动", ["增持", "减持", "回购", "股权", "股份", "质押", "解禁", "激励"]),
    ("关联交易", ["关联交易", "收购", "重组", "对外投资", "担保", "重大合同", "重大事项"]),
    ("投资者关系", ["业绩说明会", "投资者关系", "接待", "调研", "路演"]),
    ("风险提示", ["风险", "警示", "问询", "监管", "处罚", "异常波动", "澄清", "诉讼"]),
]
DEFAULT_CATEGORY = "其他公告"

# ---------------------------------------------------------------- Flask 配置
HOST = "127.0.0.1"
PORT = 5000
DEBUG = True
