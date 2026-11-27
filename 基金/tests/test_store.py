# -*- coding: utf-8 -*-
"""存储层测试：CSV 编码、去重合并、SQLite 幂等写入。"""

from fund import config
from fund.models import Fund, NavPoint
from fund.store import (connect, counts, latest_nav, upsert_funds, upsert_navs,
                        write_csv, write_funds_csv, write_nav_csv)

FUNDS = [Fund("000001", "HXCZHH", "华夏成长混合", "混合型-偏股", "HUAXIA"),
         Fund("110022", "YFDXFP", "易方达消费行业股票", "股票型", "YIFANGDA")]


def _points(code, dates):
    return [NavPoint(code, d, "1.%04d" % i, "2.%04d" % i, "0.1")
            for i, d in enumerate(dates)]


# --------------------------------------------------------------------------- #
# CSV
# --------------------------------------------------------------------------- #
def test_write_csv_has_utf8_bom(tmp_path):
    """Excel 靠 BOM 判断 UTF-8，没有 BOM 中文就成问号。"""
    path = tmp_path / "t.csv"
    write_csv(path, [{"基金代码": "000001", "基金简称": "华夏成长混合"}],
              ["基金代码", "基金简称"])
    raw = path.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")
    assert "华夏成长混合" in raw.decode("utf-8-sig")
    assert "华夏成长混合" in path.read_text(encoding="utf-8-sig")


def test_write_funds_csv(tmp_path):
    path = tmp_path / "funds.csv"
    rows = write_funds_csv(FUNDS, path)
    assert rows == 2
    text = path.read_text(encoding="utf-8-sig").splitlines()
    assert text[0].split(",") == config.FUND_FIELDS
    assert "华夏成长混合" in text[1]


def test_write_nav_csv_merges_and_dedupes(tmp_path):
    path = tmp_path / "nav.csv"
    write_nav_csv(_points("000001", ["2026-11-19", "2026-11-18"]), path, append=True)
    # 第二次：一条重复（11-19）+ 一条新的（11-20），另外换一只基金
    write_nav_csv(_points("000001", ["2026-11-20", "2026-11-19"]), path, append=True)
    write_nav_csv(_points("110022", ["2026-11-20"]), path, append=True)

    lines = path.read_text(encoding="utf-8-sig").splitlines()
    assert len(lines) == 1 + 4          # 表头 + 3 行 000001 + 1 行 110022
    body = "\n".join(lines[1:])
    assert body.count("2026-11-19") == 1     # 重复的日期只留一行
    assert "110022" in body


def test_write_csv_ignores_extra_keys(tmp_path):
    path = tmp_path / "t.csv"
    write_csv(path, [{"基金代码": "1", "多出来的": "x"}], ["基金代码"])
    assert path.read_text(encoding="utf-8-sig").splitlines()[1] == "1"


# --------------------------------------------------------------------------- #
# SQLite
# --------------------------------------------------------------------------- #
def test_upsert_funds_is_idempotent(tmp_path):
    conn = connect(tmp_path / "f.db")
    assert upsert_funds(conn, FUNDS) == 2
    assert upsert_funds(conn, FUNDS) == 2          # 再写一次不报错、不重复
    assert counts(conn)["fund"] == 2
    conn.close()


def test_upsert_funds_updates_fields(tmp_path):
    conn = connect(tmp_path / "f.db")
    upsert_funds(conn, FUNDS)
    changed = Fund("000001", "HXCZHH", "华夏成长混合A", "混合型-偏股", "HUAXIA")
    upsert_funds(conn, [changed])
    name = conn.execute("SELECT name FROM fund WHERE code='000001'").fetchone()[0]
    assert name == "华夏成长混合A"
    conn.close()


def test_upsert_navs_and_latest(tmp_path):
    conn = connect(tmp_path / "f.db")
    upsert_navs(conn, _points("000001", ["2026-11-18", "2026-11-20", "2026-11-19"]))
    row = latest_nav(conn, "000001")
    assert row[1] == "2026-11-20"          # 按日期倒序取最新
    assert counts(conn) == {"fund": 0, "nav": 3}
    conn.close()


def test_upsert_navs_dedupes_by_code_and_date(tmp_path):
    conn = connect(tmp_path / "f.db")
    upsert_navs(conn, _points("000001", ["2026-11-20"]))
    upsert_navs(conn, _points("000001", ["2026-11-20"]))
    assert counts(conn)["nav"] == 1
    conn.close()


def test_latest_nav_missing_code(tmp_path):
    conn = connect(tmp_path / "f.db")
    assert latest_nav(conn, "999999") is None
    conn.close()
