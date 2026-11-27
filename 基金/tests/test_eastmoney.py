# -*- coding: utf-8 -*-
"""数据源解析的单元测试：全部用离线样本，不联网。"""

import json

import pytest

from fund import config
from fund.client import FetchError
from fund.eastmoney import (fetch_nav_history, fund_type_counts, parse_fund_list,
                            parse_nav_page)
from fund.models import Fund

# 真实接口的样子：BOM + `var r = [...]` + 五个字段
LIST_JS = (
    '\ufeffvar r = [["000001","HXCZHH","华夏成长混合","混合型-偏股","HUAXIACHENGZHANGHUNHE"],'
    '["110022","YFDXFP","易方达消费行业股票","股票型","YIFANGDAXIAOFEIHANGYEGUPIAO"]];'
)


def test_parse_fund_list():
    funds = parse_fund_list(LIST_JS)
    assert len(funds) == 2
    assert funds[0] == Fund(code="000001", abbr="HXCZHH", name="华夏成长混合",
                            type="混合型-偏股", pinyin="HUAXIACHENGZHANGHUNHE")
    assert funds[1].type == "股票型"


def test_parse_fund_list_without_var_prefix():
    """格式退化时也能解析（直接取首个 [ 到最后一个 ]）。"""
    funds = parse_fund_list('[["161725","ZJBY","招商中证白酒","指数型"]]')
    assert funds[0].code == "161725"


def test_parse_fund_list_skips_short_rows():
    funds = parse_fund_list('var r = [["000001","A","短行"],["000002","B","正常基金","债券型"]];')
    assert [f.code for f in funds] == ["000002"]


def test_parse_fund_list_rejects_garbage():
    with pytest.raises(ValueError):
        parse_fund_list("<!DOCTYPE html><html>拒绝访问</html>")


def _nav_payload(rows, total=0, err=0):
    return {"Data": {"LSJZList": rows, "TotalCount": total,
                     "PageSize": 50, "PageIndex": 1},
            "ErrCode": err, "ErrMsg": None}


def test_parse_nav_page():
    payload = _nav_payload([
        {"FSRQ": "2026-11-20", "DWJZ": "0.9370", "LJJZ": "3.2400", "JZZZL": "0.21"},
        {"FSRQ": "2026-11-19", "DWJZ": "0.9350", "LJJZ": "3.2380", "JZZZL": ""},
    ], total=1203)
    points, total = parse_nav_page(payload)
    assert total == 1203
    assert len(points) == 2
    assert points[0].date == "2026-11-20"
    assert points[0].unit_nav == "0.9370"
    assert points[1].growth == ""


def test_parse_nav_page_skips_rows_without_date():
    points, _ = parse_nav_page(_nav_payload([
        {"FSRQ": "", "DWJZ": "1.0"},
        {"FSRQ": "2026-11-18", "DWJZ": "1.1"},
    ]))
    assert [p.date for p in points] == ["2026-11-18"]


def test_parse_nav_page_error_code():
    with pytest.raises(FetchError):
        parse_nav_page(_nav_payload([], err=-1))


def test_parse_nav_page_not_a_dict():
    with pytest.raises(ValueError):
        parse_nav_page(["不是对象"])


class FakeClient:
    """替身客户端：按 pageIndex 返回预置页，并记录调用顺序。"""

    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def get_json(self, url, params=None, cache_key=None):
        page = params["pageIndex"]
        self.calls.append(page)
        return self.pages[page]


def _rows(n, start=1):
    return [{"FSRQ": "2026-11-%02d" % (start + i), "DWJZ": "1.0", "LJJZ": "1.0",
             "JZZZL": "0.0"} for i in range(n)]


PAGE = config.NAV_PAGE_SIZE


def test_fetch_nav_history_stops_on_partial_page():
    client = FakeClient({1: _nav_payload(_rows(PAGE)), 2: _nav_payload(_rows(3, PAGE + 1))})
    points = fetch_nav_history(client, "000001", max_pages=5)
    assert len(points) == PAGE + 3
    assert client.calls == [1, 2]           # 第二页不满一页，不再请求第三页
    assert {p.code for p in points} == {"000001"}   # 代码由调用方填进去


def test_fetch_nav_history_stops_on_empty_page():
    """接口翻到底时返回空列表，必须停下来，不能一直翻。"""
    client = FakeClient({1: _nav_payload(_rows(PAGE)), 2: _nav_payload([])})
    points = fetch_nav_history(client, "000001", max_pages=5)
    assert len(points) == PAGE
    assert client.calls == [1, 2]


def test_fetch_nav_history_respects_max_pages():
    client = FakeClient({i: _nav_payload(_rows(PAGE)) for i in range(1, 6)})
    points = fetch_nav_history(client, "000001", max_pages=2)
    assert len(points) == PAGE * 2
    assert client.calls == [1, 2]


def test_fund_type_counts():
    funds = [Fund("1", "A", "a", "股票型"), Fund("2", "B", "b", "股票型"),
             Fund("3", "C", "c", "债券型")]
    assert fund_type_counts(funds) == {"股票型": 2, "债券型": 1}
