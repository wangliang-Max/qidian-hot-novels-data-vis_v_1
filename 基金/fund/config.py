# -*- coding: utf-8 -*-
"""基金数据爬取：配置。

和仓库根目录的 config.py 一样，把「会变的东西」集中放这里：
数据源地址、抓取参数、输出路径、字段顺序。改需求基本只动这个文件。
"""

from pathlib import Path

# --------------------------------------------------------------------------- #
# 数据源：天天基金（东方财富）
#   1) 全量基金列表：一个 3MB 左右的 JS 文件，赋值给变量 r，UTF-8 编码且带 BOM。
#   2) 历史净值：JSON 接口，必须带 Referer，否则返回空。
#   两者都不需要登录，也没有验证码，适合课程作业。
# --------------------------------------------------------------------------- #
BASE_URL = "http://fund.eastmoney.com"
LIST_JS_URL = BASE_URL + "/js/fundcode_search.js"
NAV_API_URL = "http://api.fund.eastmoney.com/f10/lsjz"
DETAIL_JS_URL = BASE_URL + "/pingzhongdata/{code}.js"
REFERER = BASE_URL + "/"

# 爬虫礼仪：带上能标识自己的 UA，方便对方出问题时联系你
USER_AGENT = (
    "fund-data-course-project/1.0 "
    "(Python course assignment; contact: your-name@example.com)"
)
REQUEST_TIMEOUT = 20   # 单次请求超时（秒）
REQUEST_DELAY = 0.20   # 请求间隔（秒），避免给对方服务器压力
MAX_RETRY = 4          # 失败重试次数（指数退避）

# 历史净值接口**实际**每页固定返回 20 条（传 pageSize=50 会被忽略，
# 响应里也不返回 TotalCount），所以页大小必须按实测的 20 来定，
# 否则「返回条数 < 页大小」的判断会提前结束翻页、漏掉历史数据。
NAV_PAGE_SIZE = 20
NAV_MAX_PAGES = 5

# --------------------------------------------------------------------------- #
# 目录与文件（cache/ 已被根目录 .gitignore 忽略，可随时删除重下）
# --------------------------------------------------------------------------- #
ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "cache" / "fund"
DATA_DIR = ROOT / "data" / "fund"

FUND_LIST_CSV = DATA_DIR / "fund_list.csv"
NAV_CSV = DATA_DIR / "fund_nav.csv"
DB_PATH = DATA_DIR / "fund.db"

# --------------------------------------------------------------------------- #
# 字段顺序（CSV / Excel 的列顺序，也是答辩时讲字段口径的依据）
# --------------------------------------------------------------------------- #
FUND_FIELDS = ["基金代码", "拼音缩写", "基金简称", "基金类型", "拼音全称"]
NAV_FIELDS = ["基金代码", "净值日期", "单位净值", "累计净值", "日增长率"]
