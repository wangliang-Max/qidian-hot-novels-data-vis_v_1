# -*- coding: utf-8 -*-
"""数据模型：抓下来的一条记录长什么样。"""

from __future__ import annotations

from dataclasses import dataclass, field

from fund.encoding import normalize_text


@dataclass
class Fund:
    """一只基金的基本信息（来自基金列表 JS）。"""

    code: str
    abbr: str          # 拼音缩写
    name: str          # 基金简称
    type: str          # 基金类型：股票型 / 混合型 / 债券型 ...
    pinyin: str = ""   # 拼音全称

    def row(self) -> dict:
        return {
            "基金代码": self.code,
            "拼音缩写": self.abbr,
            "基金简称": self.name,
            "基金类型": self.type,
            "拼音全称": self.pinyin,
        }


@dataclass
class NavPoint:
    """一条历史净值记录。"""

    code: str
    date: str              # FSRQ，形如 2026-11-20
    unit_nav: str          # DWJZ 单位净值
    accum_nav: str         # LJJZ 累计净值
    growth: str = ""       # JZZZL 日增长率，可能为空

    def row(self) -> dict:
        return {
            "基金代码": self.code,
            "净值日期": self.date,
            "单位净值": self.unit_nav,
            "累计净值": self.accum_nav,
            "日增长率": self.growth,
        }


@dataclass
class FetchStats:
    """一次抓取的统计，给 CLI 打印和调试用。"""

    codes: list[str] = field(default_factory=list)
    funds: int = 0
    navs: int = 0
    failed: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failed

    def summary(self) -> str:
        return "基金 %d 只，净值 %d 条，失败 %d 个" % (
            self.funds, self.navs, len(self.failed))


def clean_fund_name(name: str) -> str:
    """基金简称的额外清洗：去掉尾部「(前端)」「(后端)」这类销售渠道后缀。

    这些后缀会让同一只基金在列表里出现多个名字，统计时被当成不同基金。
    """
    text = normalize_text(name)
    for suffix in ("(前端)", "(后端)", "(A)", "(B)", "(C)", "(D)", "(E)"):
        if text.endswith(suffix):
            text = text[: -len(suffix)].rstrip()
    return text
