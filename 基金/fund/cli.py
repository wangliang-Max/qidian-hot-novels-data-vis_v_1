# -*- coding: utf-8 -*-
"""命令行入口。

用法::

    python -m fund list                 # 抓全量基金列表
    python -m fund nav 000001 110022    # 抓指定基金的历史净值
    python -m fund sync                 # 列表 + 默认几只基金，一条龙
    python -m fund debug                # 联网/编码/缓存/数据库自检
    python -m fund stats                # 看库里现在有什么

加 ``--refresh`` 忽略缓存重新下载，加 ``--no-cache`` 完全不落盘。
"""

from __future__ import annotations

import argparse
import sys
import time

from fund import config
from fund.client import Client, FetchError, clear_cache
from fund.eastmoney import (fetch_fund_list, fetch_nav_history, fund_type_counts,
                            parse_fund_list)
from fund.encoding import decode_bytes, looks_mojibake, normalize_text
from fund.models import FetchStats
from fund.store import (connect, counts, latest_nav, upsert_funds, upsert_navs,
                        write_funds_csv, write_nav_csv)

DEFAULT_CODES = ["000001", "110022", "161725"]


# --------------------------------------------------------------------------- #
# 子命令
# --------------------------------------------------------------------------- #
def cmd_list(args) -> int:
    with Client(use_cache=not args.no_cache) as client:
        funds = fetch_fund_list(client, refresh=args.refresh)
    rows = write_funds_csv(funds)
    with connect() as conn:
        upsert_funds(conn, funds)

    print("基金列表：%d 只 -> %s（%d 行）" % (len(funds), config.FUND_LIST_CSV, rows))
    print("\n按类型分布（前 8）：")
    for name, num in list(fund_type_counts(funds).items())[:8]:
        print("  %-14s %6d" % (name, num))
    return 0


def cmd_nav(args) -> int:
    codes = _split_codes(args.codes)
    stats = FetchStats(codes=codes)
    all_points = []

    with Client(use_cache=not args.no_cache) as client:
        for code in codes:
            try:
                points = fetch_nav_history(client, code, max_pages=args.pages,
                                           refresh=args.refresh)
            except (FetchError, ValueError) as exc:
                print("  [失败] %s：%s" % (code, exc))
                stats.failed.append(code)
                continue
            if not points:
                print("  [空] %s 没有抓到净值（代码是否存在？）" % code)
                stats.failed.append(code)
                continue

            all_points.extend(points)
            stats.funds += 1
            latest = points[0]
            print("  %-8s %4d 条  最新 %s  单位净值 %s  日增长 %s%%"
                  % (code, len(points), latest.date, latest.unit_nav, latest.growth or "-"))

        if all_points:
            rows = write_nav_csv(all_points, append=True)
            with connect() as conn:
                upsert_navs(conn, all_points)
            stats.navs = len(all_points)
            print("\n净值合计 %d 条 -> %s" % (rows, config.NAV_CSV))
            print("数据库：%s" % config.DB_PATH)

    print(stats.summary())
    return 0 if stats.ok else 1


def cmd_sync(args) -> int:
    print("== 1/2 基金列表")
    code = cmd_list(args)
    if code != 0:
        return code
    print("\n== 2/2 历史净值（%s）" % ", ".join(_split_codes(args.codes)))
    return cmd_nav(args)


def cmd_stats(args) -> int:
    if not config.DB_PATH.exists():
        print("数据库还不存在：%s（先跑 python -m fund list）" % config.DB_PATH)
        return 1
    with connect() as conn:
        info = counts(conn)
        print("数据库：%s" % config.DB_PATH)
        print("  基金 %d 只，净值 %d 条" % (info["fund"], info["nav"]))
        row = conn.execute("SELECT COUNT(DISTINCT code) FROM nav").fetchone()
        print("  有净值数据的基金：%d 只" % row[0])
        top = conn.execute(
            "SELECT type, COUNT(*) c FROM fund GROUP BY type ORDER BY c DESC LIMIT 5"
        ).fetchall()
        print("  类型 Top5：" + "，".join("%s(%d)" % (t, c) for t, c in top))
        one = latest_nav(conn, "000001")
        if one:
            print("  000001 最新：%s 单位净值 %s" % (one[1], one[2]))
    return 0


def cmd_debug(args) -> int:
    """自检：联网、编码、解析、缓存、数据库。每项都打印判定结果。"""
    ok = True
    print("== 环境")
    print("  Python %s" % sys.version.split()[0])
    try:
        import requests
        print("  requests %s" % requests.__version__)
    except Exception as exc:  # pragma: no cover - 环境问题
        print("  requests 不可用：%s" % exc)
        ok = False
    print("  缓存目录 %s" % config.CACHE_DIR)

    print("\n== 编码自检")
    cases = [
        ("UTF-8 带 BOM", "华夏成长混合".encode("utf-8-sig")),
        ("UTF-8", "华夏成长混合".encode("utf-8")),
        ("GBK", "华夏成长混合".encode("gbk")),
    ]
    for label, raw in cases:
        text, used = decode_bytes(raw)
        good = text == "华夏成长混合" and not looks_mojibake(text)
        ok &= good
        print("  %-12s 解码=%s 结果=%s %s" % (label, used, text, "OK" if good else "FAIL"))
    print("  乱码检测：正常文本=%s，乱码文本=%s"
          % (looks_mojibake("华夏成长混合"), looks_mojibake("ä¸­å›½")))
    print("  名称归一化：%r -> %r" % ("华夏　成长　混合\u200b",
                                    normalize_text("华夏　成长　混合\u200b")))

    print("\n== 数据源连通性")
    with Client(use_cache=not args.no_cache) as client:
        # 1) 基金列表
        try:
            started = time.time()
            text, used = client.get_text(config.LIST_JS_URL,
                                         cache_key=None if args.refresh else "fund_list.js")
            funds = parse_fund_list(text)
            good = len(funds) > 1000
            ok &= good
            print("  [%s] 基金列表  %d 只，%d 字节，编码 %s，%.1fs%s"
                  % ("OK" if good else "FAIL", len(funds), len(text.encode()),
                     used, time.time() - started,
                     "" if good else "（数量异常）"))
            print("        示例：%s %s %s" % (funds[0].code, funds[0].name, funds[0].type)
                  if funds else "        示例：无")
        except Exception as exc:
            ok = False
            print("  [FAIL] 基金列表：%s" % exc)

        # 2) 净值接口
        try:
            started = time.time()
            points = fetch_nav_history(client, "000001", max_pages=1,
                                       refresh=args.refresh)
            good = bool(points)
            ok &= good
            print("  [%s] 历史净值  %d 条，最新 %s 单位净值 %s，%.1fs"
                  % ("OK" if good else "FAIL", len(points),
                     points[0].date if points else "-",
                     points[0].unit_nav if points else "-", time.time() - started))
        except Exception as exc:
            ok = False
            print("  [FAIL] 历史净值：%s" % exc)

    print("\n== 本地状态")
    cached = list(config.CACHE_DIR.glob("*")) if config.CACHE_DIR.exists() else []
    print("  缓存文件 %d 个" % len(cached))
    if config.DB_PATH.exists():
        with connect() as conn:
            info = counts(conn)
        print("  数据库：基金 %d 只，净值 %d 条" % (info["fund"], info["nav"]))
    else:
        print("  数据库：尚未创建（跑 python -m fund list 即可）")

    print("\n%s" % ("全部通过" if ok else "有检查项失败，按上面的 FAIL 排查"))
    return 0 if ok else 1


def cmd_clean(args) -> int:
    num = clear_cache()
    print("已删除缓存文件 %d 个" % num)
    return 0


# --------------------------------------------------------------------------- #
# 参数
# --------------------------------------------------------------------------- #
def _positive_int(text: str) -> int:
    """argparse 校验：翻页数必须是正整数。"""
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError("需要整数，收到 %r" % text)
    if value < 1:
        raise argparse.ArgumentTypeError("必须 >= 1，收到 %d" % value)
    return value


def _split_codes(values: list[str] | None) -> list[str]:
    """支持 `nav 000001 110022` 和 `nav 000001,110022` 两种写法。"""
    if not values:
        return list(DEFAULT_CODES)
    codes = " ".join(values).replace(",", " ").split()
    return [c.strip() for c in codes if c.strip()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m fund",
        description="天天基金数据爬取（基金列表 + 历史净值）",
    )
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--refresh", action="store_true", help="忽略缓存，重新下载")
    common.add_argument("--no-cache", action="store_true", help="不读写本地缓存")

    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", parents=[common], help="抓全量基金列表")
    p_list.set_defaults(func=cmd_list)

    p_nav = sub.add_parser("nav", parents=[common], help="抓指定基金的历史净值")
    p_nav.add_argument("codes", nargs="*", help="基金代码，可多个；默认 %s"
                       % " ".join(DEFAULT_CODES))
    p_nav.add_argument("--pages", type=_positive_int, default=config.NAV_MAX_PAGES,
                       help="最多翻几页（接口每页固定 20 条），默认 %d" % config.NAV_MAX_PAGES)
    p_nav.set_defaults(func=cmd_nav)

    p_sync = sub.add_parser("sync", parents=[common], help="列表 + 净值一条龙")
    p_sync.add_argument("codes", nargs="*", help="基金代码，默认 %s" % " ".join(DEFAULT_CODES))
    p_sync.add_argument("--pages", type=_positive_int, default=config.NAV_MAX_PAGES)
    p_sync.set_defaults(func=cmd_sync)

    p_debug = sub.add_parser("debug", parents=[common], help="联网/编码/缓存/数据库自检")
    p_debug.set_defaults(func=cmd_debug)

    p_stats = sub.add_parser("stats", help="查看数据库现状")
    p_stats.set_defaults(func=cmd_stats)

    p_clean = sub.add_parser("clean", help="清空缓存")
    p_clean.set_defaults(func=cmd_clean)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\n已中断", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
