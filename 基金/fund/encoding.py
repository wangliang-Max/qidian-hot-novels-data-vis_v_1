# -*- coding: utf-8 -*-
"""编码处理：这是本项目最容易翻车的地方，单独拆一个模块。

天天基金的三个数据源编码各不相同：

* 基金列表 JS：UTF-8 **带 BOM**，直接 ``json.loads`` 会报
  ``Expecting value: line 1 column 1``，因为第一个字符是 ``\\ufeff``。
* 历史净值 JSON：响应头里**不写 charset**，requests 会猜成 ISO-8859-1，
  中文日期/费用项就成了乱码 —— 必须自己按 UTF-8 解码。
* 部分老页面：GBK / GB18030（历史上东方财富大量用 GBK）。

所以统一走 :func:`decode_bytes`：按候选编码逐个试，严格解码，谁先成功用谁。
"""

from __future__ import annotations

import codecs
import unicodedata

# 无 BOM 时的候选编码顺序：先 UTF-8（严格模式下几乎不会误判），再中文国标。
# 注意不要放 utf-8-sig：它能把任何合法 UTF-8 都解出来，会把编码名误报成 utf-8-sig。
CANDIDATES = ("utf-8", "gb18030", "gbk", "big5")

# 常见 BOM 头 -> 编码名
_BOMS = (
    (codecs.BOM_UTF8, "utf-8-sig"),
    (codecs.BOM_UTF32_LE, "utf-32"),
    (codecs.BOM_UTF32_BE, "utf-32"),
    (codecs.BOM_UTF16_LE, "utf-16"),
    (codecs.BOM_UTF16_BE, "utf-16"),
)


class DecodeError(ValueError):
    """所有候选编码都解不出来时抛出。"""


def strip_bom(text: str) -> str:
    """去掉字符串开头的 BOM（``\\ufeff``），没有就原样返回。"""
    return text.lstrip("\ufeff")


def sniff_bom(data: bytes) -> str | None:
    """按字节前缀判断 BOM 对应的编码名，没有 BOM 返回 ``None``。"""
    for bom, name in _BOMS:
        if data.startswith(bom):
            return name
    return None


def decode_bytes(data: bytes, candidates=CANDIDATES) -> tuple[str, str]:
    """把字节解码成字符串，返回 ``(文本, 实际使用的编码)``。

    先看 BOM；没有 BOM 就按 ``candidates`` 顺序严格解码。UTF-8 严格模式下
    中文字节序列基本不会误判，所以顺序放在最前面是安全的。
    """
    if not data:
        return "", "utf-8"

    bom_name = sniff_bom(data)
    if bom_name:
        try:
            return data.decode(bom_name), bom_name
        except UnicodeDecodeError:
            pass  # BOM 和内容对不上，退回逐个尝试

    tried = []
    for name in candidates:
        try:
            return strip_bom(data.decode(name)), name
        except (UnicodeDecodeError, LookupError):
            tried.append(name)
    raise DecodeError("无法解码（已尝试 %s），前 40 字节：%r" % ("/".join(tried), data[:40]))


def looks_mojibake(text: str) -> bool:
    """粗判是否像乱码：出现替换字符，或典型的「ä¸­」式拉丁乱码片段。"""
    if not text:
        return False
    if "\ufffd" in text:
        return True
    suspicious = ("Ã", "Â", "ã", "å", "ä¸", "ï¿½")
    return any(s in text for s in suspicious)


def normalize_text(text: str | None) -> str:
    """统一全角空格/零宽字符，压缩空白，去掉首尾空格。

    基金简称里常见 ``Ａ`` 全角字母、``\\u3000`` 全角空格、零宽空格，
    不统一会让后续按名字去重、排序出错。这里用 NFKC 归一化。
    """
    if not text:
        return ""
    cleaned = unicodedata.normalize("NFKC", text)
    cleaned = cleaned.replace("\u3000", " ").replace("\u200b", "")
    return " ".join(cleaned.split())


def ensure_utf8_bytes(text: str) -> bytes:
    """把文本转成 UTF-8 字节（写文件前的统一出口）。"""
    return text.encode("utf-8")
