# -*- coding: utf-8 -*-
"""落地存储：CSV（Excel 直接双击不乱码）+ SQLite（方便二次查询）。

CSV 用 ``utf-8-sig``：带 BOM 的 UTF-8，Excel 打开中文才不乱码。
不带 BOM 的话 Excel 会按 GBK 猜，基金名全是问号 —— 这是本项目「编码」主题的
一个具体落点。
"""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from fund import config
from fund.models import Fund, NavPoint

_SCHEMA = """
CREATE TABLE IF NOT EXISTS fund (
    code    TEXT PRIMARY KEY,
    abbr    TEXT,
    name    TEXT,
    type    TEXT,
    pinyin  TEXT
);
CREATE TABLE IF NOT EXISTS nav (
    code       TEXT NOT NULL,
    date       TEXT NOT NULL,
    unit_nav   TEXT,
    accum_nav  TEXT,
    growth     TEXT,
    PRIMARY KEY (code, date)
);
CREATE INDEX IF NOT EXISTS idx_nav_date ON nav (date);
"""


def ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, rows: list[dict], fields: list[str],
              append: bool = False) -> int:
    """写 CSV，返回写入行数。默认覆盖写，``append=True`` 时追加。"""
    ensure_dir(path)
    mode = "a" if append and path.exists() else "w"
    written = 0
    with path.open(mode, encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        if mode == "w":
            writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})
            written += 1
    return written


def write_funds_csv(funds: list[Fund], path: Path | None = None) -> int:
    target = path or config.FUND_LIST_CSV
    return write_csv(target, [f.row() for f in funds], config.FUND_FIELDS)


def write_nav_csv(points: list[NavPoint], path: Path | None = None,
                  append: bool = True) -> int:
    """写净值 CSV。

    追加模式会先读回已有内容，再按 ``(基金代码, 净值日期)`` 去重合并，
    这样反复跑 ``nav`` 不会把同一只基金的记录堆成重复行。
    """
    target = path or config.NAV_CSV
    rows = [p.row() for p in points]
    if append and target.exists():
        merged: dict[tuple[str, str], dict] = {}
        with target.open(encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                merged[(row.get("基金代码", ""), row.get("净值日期", ""))] = row
        for row in rows:
            merged[(row["基金代码"], row["净值日期"])] = row
        rows = sorted(merged.values(), key=lambda r: (r["基金代码"], r["净值日期"]),
                      reverse=True)
        append = False
    return write_csv(target, rows, config.NAV_FIELDS, append=append)


def connect(path: Path | None = None) -> sqlite3.Connection:
    target = path or config.DB_PATH
    if str(target) != ":memory:":
        ensure_dir(target)
    conn = sqlite3.connect(str(target))
    conn.executescript(_SCHEMA)
    return conn


def upsert_funds(conn: sqlite3.Connection, funds: list[Fund]) -> int:
    rows = [(f.code, f.abbr, f.name, f.type, f.pinyin) for f in funds]
    conn.executemany(
        "INSERT INTO fund (code, abbr, name, type, pinyin) VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT(code) DO UPDATE SET abbr=excluded.abbr, name=excluded.name, "
        "type=excluded.type, pinyin=excluded.pinyin",
        rows,
    )
    conn.commit()
    return len(rows)


def upsert_navs(conn: sqlite3.Connection, points: list[NavPoint]) -> int:
    rows = [(p.code, p.date, p.unit_nav, p.accum_nav, p.growth) for p in points]
    conn.executemany(
        "INSERT INTO nav (code, date, unit_nav, accum_nav, growth) "
        "VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT(code, date) DO UPDATE SET unit_nav=excluded.unit_nav, "
        "accum_nav=excluded.accum_nav, growth=excluded.growth",
        rows,
    )
    conn.commit()
    return len(rows)


def counts(conn: sqlite3.Connection) -> dict[str, int]:
    """库里各表行数，调试时一眼看出有没有真的写进去。"""
    result = {}
    for table in ("fund", "nav"):
        result[table] = conn.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
    return result


def latest_nav(conn: sqlite3.Connection, code: str) -> tuple | None:
    """取某只基金最新一条净值，用于冒烟验证。"""
    return conn.execute(
        "SELECT code, date, unit_nav, accum_nav, growth FROM nav "
        "WHERE code = ? ORDER BY date DESC LIMIT 1", (code,)
    ).fetchone()
