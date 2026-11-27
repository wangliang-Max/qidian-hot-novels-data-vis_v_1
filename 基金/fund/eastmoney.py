# -*- coding: utf-8 -*-
"""天天基金（东方财富）数据源：解析 + 抓取。

两个接口的坑都在这里处理掉，上层不用关心：

* 基金列表返回的是 JS 赋值语句 ``var r = [...]``，不是标准 JSON，且带 BOM。
* 历史净值是 JSON，但响应头没有 charset，中文按 UTF-8 解。
"""

from __future__ import annotations

import json
import re

from fund import config
from fund.client import Client, FetchError
from fund.encoding import strip_bom
from fund.models import Fund, NavPoint

# 匹配 `var r = [ ... ]` 里的数组部分；用贪婪到最后一个 ] 更稳，
# 因为基金名里可能出现 ]（极少），而非贪婪会提前截断。
_LIST_RE = re.compile(r"var\s+\w+\s*=\s*(\[.*\])\s*;?\s*$", re.S)


def parse_fund_list(js_text: str) -> list[Fund]:
    """解析基金列表 JS，返回 :class:`Fund` 列表。

    >>> parse_fund_list('var r = [["000001","HXCZHH","华夏成长混合","混合型-偏股","HUAXIA"]];')
    [Fund(code='000001', abbr='HXCZHH', name='华夏成长混合', ...)]
    """
    text = strip_bom(js_text).strip()
    match = _LIST_RE.search(text)
    if not match:
        # 退化方案：直接取第一个 [ 到最后一个 ]
        start, end = text.find("["), text.rfind("]")
        if start < 0 or end <= start:
            raise ValueError("基金列表格式不认识，前 60 字符：%r" % text[:60])
        payload = text[start:end + 1]
    else:
        payload = match.group(1)

    rows = json.loads(payload)
    funds: list[Fund] = []
    for row in rows:
        if len(row) < 4:
            continue
        funds.append(Fund(
            code=str(row[0]).strip(),
            abbr=str(row[1]).strip(),
            name=str(row[2]).strip(),
            type=str(row[3]).strip(),
            pinyin=str(row[4]).strip() if len(row) > 4 else "",
        ))
    return funds


def fetch_fund_list(client: Client, refresh: bool = False) -> list[Fund]:
    """抓全量基金列表（约 2 万只）。"""
    key = None if refresh else "fund_list.js"
    text, used = client.get_text(config.LIST_JS_URL, cache_key=key)
    if not text.strip():
        raise FetchError("基金列表为空（编码 %s）" % used)
    return parse_fund_list(text)


def parse_nav_page(payload: dict) -> tuple[list[NavPoint], int]:
    """解析一页历史净值，返回 ``(净值列表, 总条数)``。

    接口返回形如::

        {"Data": {"LSJZList": [{"FSRQ": "2026-11-20", "DWJZ": "0.9370", ...}],
                  "TotalCount": 5000, "PageSize": 20, "PageIndex": 1},
         "ErrCode": 0, "ErrMsg": null}
    """
    if not isinstance(payload, dict):
        raise ValueError("净值返回不是对象：%r" % type(payload))
    err = payload.get("ErrCode")
    if err not in (0, "0", None):
        raise FetchError("接口报错：%s %s" % (err, payload.get("ErrMsg")))

    data = payload.get("Data") or {}
    rows = data.get("LSJZList") or []
    total = int(data.get("TotalCount") or 0)

    points: list[NavPoint] = []
    for item in rows:
        date = str(item.get("FSRQ") or "").strip()
        if not date:
            continue
        points.append(NavPoint(
            code="",  # 由调用方填，避免依赖接口里没有的字段
            date=date,
            unit_nav=str(item.get("DWJZ") or "").strip(),
            accum_nav=str(item.get("LJJZ") or "").strip(),
            growth=str(item.get("JZZZL") or "").strip(),
        ))
    return points, total


def fetch_nav_history(client: Client, code: str, max_pages: int | None = None,
                      refresh: bool = False) -> list[NavPoint]:
    """抓一只基金的历史净值（按页翻，默认最多 :data:`config.NAV_MAX_PAGES` 页）。

    实测该接口每页固定 20 条且不返回 ``TotalCount``（传 ``pageSize`` 会被忽略），
    所以翻页的停止条件只能是「这一页不满 20 条」或「这一页是空的」。
    """
    pages = config.NAV_MAX_PAGES if max_pages is None else max_pages
    collected: list[NavPoint] = []
    total = 0

    for page in range(1, pages + 1):
        key = None if refresh else "nav_%s_%d.json" % (code, page)
        payload = client.get_json(
            config.NAV_API_URL,
            params={"fundCode": code, "pageIndex": page,
                    "pageSize": config.NAV_PAGE_SIZE},
            cache_key=key,
        )
        points, total = parse_nav_page(payload)
        if not points:              # 没有更多历史了
            break
        for point in points:
            point.code = code
        collected.extend(points)

        if len(points) < config.NAV_PAGE_SIZE:   # 不满一页 = 最后一页
            break
        if total and len(collected) >= total:
            break

    return collected


def fund_type_counts(funds: list[Fund]) -> dict[str, int]:
    """按基金类型计数（调试和统计用）。"""
    counts: dict[str, int] = {}
    for fund in funds:
        counts[fund.type] = counts.get(fund.type, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: kv[1], reverse=True))
