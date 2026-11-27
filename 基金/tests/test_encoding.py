# -*- coding: utf-8 -*-
"""编码模块的单元测试：这几个用例就是当初踩坑的现场。"""

import pytest

from fund.encoding import (DecodeError, decode_bytes, looks_mojibake,
                           normalize_text, sniff_bom, strip_bom)

NAME = "华夏成长混合"


def test_utf8_with_bom():
    text, used = decode_bytes(NAME.encode("utf-8-sig"))
    assert text == NAME
    assert used == "utf-8-sig"
    assert not text.startswith("\ufeff")


def test_plain_utf8():
    text, used = decode_bytes(NAME.encode("utf-8"))
    assert text == NAME
    assert used == "utf-8"


def test_gbk_fallback():
    text, used = decode_bytes(NAME.encode("gbk"))
    assert text == NAME
    assert used in ("gb18030", "gbk")


def test_gbk_bytes_are_not_valid_utf8():
    """确认真的走了回退：GBK 字节按 UTF-8 解会失败。"""
    with pytest.raises(UnicodeDecodeError):
        NAME.encode("gbk").decode("utf-8")


def test_sniff_bom():
    assert sniff_bom(b"\xef\xbb\xbfabc") == "utf-8-sig"
    assert sniff_bom(b"abc") is None


def test_strip_bom():
    assert strip_bom("\ufeffvar r = []") == "var r = []"
    assert strip_bom("没有 BOM") == "没有 BOM"


def test_decode_undecodable():
    with pytest.raises(DecodeError):
        decode_bytes(b"\xff\xfe\x00\x00\xff", candidates=("utf-8",))


def test_empty_bytes():
    text, used = decode_bytes(b"")
    assert text == "" and used == "utf-8"


def test_normalize_text():
    assert normalize_text("  华夏　成长 混合\u200b ") == "华夏 成长 混合"
    assert normalize_text(None) == ""


def test_normalize_fullwidth():
    """全角字母应归一化成半角，否则按名字去重会漏。"""
    assert normalize_text("ＡＢＣ基金") == "ABC基金"


def test_looks_mojibake():
    assert not looks_mojibake(NAME)
    assert looks_mojibake("ä¸­å›½")
    assert looks_mojibake("华夏\ufffd成长")
