# -*- coding: utf-8 -*-
"""起点中文网「阅读榜（热搜榜）」数据采集脚本

功能说明
--------
1. 分页请求起点移动端的榜单 JSON 接口，逐页解析榜单小说信息；
2. Cookie 从环境变量 ``QD_COOKIE`` 读取，不把个人凭据写死在代码里（可公开提交）；
3. 单页请求失败自动重试（指数退避），页与页之间随机休眠，降低触发风控的概率；
4. 支持 ``male`` / ``female`` / ``all`` 三种榜单；``--append`` 可在已有 CSV 上续爬；
5. 结果按「书名 + 作者」去重后写入 CSV，编码 utf-8-sig，Excel 可直接打开。

使用示例
--------
    # PowerShell 里先设置 Cookie（浏览器 F12 -> Network -> 任意请求 -> 复制 Cookie 头）
    $env:QD_COOKIE = "……"
    python qidian_spider.py --start-page 1 --end-page 3 --out qidian_readindex_books.csv
    python qidian_spider.py --gender all --append          # 在已有结果上续爬男女榜
"""
import argparse
import csv
import logging
import os
import random
import re
import sys
import time

import requests

API_URL = "https://m.qidian.com/webcommon/rank/readIndexlist"
FIELDS = ["排名", "小说名称", "作者", "分类", "子类", "字数", "简介"]
GENDERS = ("male", "female")

BASE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0 Mobile Safari/537.36"
    ),
    "Referer": "https://m.qidian.com/rank/readindex/",
    "Accept": "application/json, text/plain, */*",
}

log = logging.getLogger("qidian")


def build_session(cookie):
    """创建带 Cookie 的会话，并复用 TCP 连接。"""
    session = requests.Session()
    session.headers.update(BASE_HEADERS)
    session.headers["Cookie"] = cookie
    csrf = re.search(r"_csrfToken=([^;]+)", cookie)
    session.csrf_token = csrf.group(1) if csrf else ""
    if not session.csrf_token:
        log.warning("Cookie 中未找到 _csrfToken，接口可能返回空数据，请重新复制完整 Cookie")
    return session


def parse_records(records):
    """把接口返回的 records 转成 CSV 行。"""
    rows = []
    for index, book in enumerate(records):
        rows.append([
            book.get("rankNum") or (index + 1),
            book.get("bName", "未知"),
            book.get("bAuth", "未知"),
            book.get("cat", "未知"),
            book.get("subCat", ""),
            book.get("cnt", "未知"),
            (book.get("desc") or "").replace("\n", " ").strip(),
        ])
    return rows


def crawl_page(session, page_num, gender="male", retries=3, timeout=10.0):
    """抓取单页榜单，返回 [[排名, 书名, 作者, 分类, 子类, 字数, 简介], ...]。"""
    params = {
        "gender": gender,
        "pageNum": page_num,
        "catId": "-1",
        "_csrfToken": session.csrf_token,
    }

    for attempt in range(1, retries + 1):
        try:
            resp = session.get(API_URL, params=params, timeout=timeout)
            if resp.status_code in (401, 403):
                log.error("第 %s 页返回 %s，Cookie 很可能已过期，请重新获取",
                          page_num, resp.status_code)
                return []
            resp.raise_for_status()
            payload = resp.json()
        except Exception as exc:  # 网络错误 / JSON 解析错误统一重试
            if attempt >= retries:
                log.error("第 %s 页重试 %s 次仍失败：%s，跳过", page_num, retries, exc)
                return []
            wait = attempt * 2
            log.warning("第 %s 页第 %s 次请求失败：%s，%s 秒后重试",
                        page_num, attempt, exc, wait)
            time.sleep(wait)
            continue

        if not isinstance(payload, dict):
            log.error("第 %s 页返回的不是 JSON 对象，可能被封禁或接口已变更", page_num)
            return []

        records = (payload.get("data") or {}).get("records") or []
        if not records:
            log.warning("第 %s 页（%s）没有返回数据（code=%s, msg=%s），可能已到榜单末尾",
                        page_num, gender, payload.get("code"), payload.get("msg") or payload.get("message") or "")
            return []

        rows = parse_records(records)
        log.info("第 %s 页（%s）抓取成功：%s 条", page_num, gender, len(rows))
        return rows

    return []


def load_existing(path):
    """读取已有 CSV（--append 用），返回行列表。"""
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8-sig", newline="") as fp:
        reader = csv.DictReader(fp)
        if not reader.fieldnames:
            return []
        return [[row.get(key, "") for key in FIELDS] for row in reader]


def dedupe(rows):
    """按「书名 + 作者」去重，保持榜单排名顺序。"""
    seen, unique = set(), []
    for row in rows:
        key = (row[1], row[2])
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return unique


def save_csv(rows, path, raw_count):
    """按「书名 + 作者」去重后原子写入 CSV。"""
    unique = dedupe(rows)
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)

    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8-sig", newline="") as fp:
        writer = csv.writer(fp)
        writer.writerow(FIELDS)
        writer.writerows(unique)
    os.replace(tmp, path)
    log.info("已保存 %s 条数据到 %s（去重 %s 条）", len(unique), path, raw_count - len(unique))


def main():
    parser = argparse.ArgumentParser(description="起点阅读榜爬虫")
    parser.add_argument("--start-page", type=int, default=1, help="起始页码")
    parser.add_argument("--end-page", type=int, default=3, help="结束页码（含）")
    parser.add_argument("--out", default="qidian_readindex_books.csv", help="输出 CSV 路径")
    parser.add_argument("--gender", choices=GENDERS + ("all",), default="male", help="榜单频道")
    parser.add_argument("--min-delay", type=float, default=2.0, help="翻页最小休眠秒数")
    parser.add_argument("--max-delay", type=float, default=3.5, help="翻页最大休眠秒数")
    parser.add_argument("--timeout", type=float, default=10.0, help="单次请求超时秒数")
    parser.add_argument("--append", action="store_true", help="在 --out 已有数据基础上续爬")
    parser.add_argument("--verbose", action="store_true", help="输出调试日志")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    if args.start_page < 1 or args.end_page < args.start_page:
        raise SystemExit("页码范围不合法：要求 1 <= start-page <= end-page")
    if args.min_delay < 0 or args.min_delay > args.max_delay:
        raise SystemExit("休眠参数不合法：要求 0 <= min-delay <= max-delay")
    if args.timeout <= 0:
        raise SystemExit("--timeout 必须大于 0")

    cookie = os.environ.get("QD_COOKIE", "").strip()
    if not cookie:
        raise SystemExit("缺少 Cookie：请先设置环境变量 QD_COOKIE（见文件头部说明）")

    targets = GENDERS if args.gender == "all" else (args.gender,)
    session = build_session(cookie)

    all_rows = load_existing(args.out) if args.append else []
    if all_rows:
        log.info("续爬模式：已有 %s 条数据", len(all_rows))

    started = time.time()
    for gender in targets:
        for page in range(args.start_page, args.end_page + 1):
            rows = crawl_page(session, page, gender=gender, timeout=args.timeout)
            if not rows:
                break
            all_rows.extend(rows)
            time.sleep(random.uniform(args.min_delay, args.max_delay))

    if not all_rows:
        raise SystemExit("没有抓到任何数据，请检查 Cookie 是否过期")

    save_csv(all_rows, args.out, len(all_rows))
    log.info("耗时 %.1f 秒，输出文件：%s", time.time() - started, args.out)


if __name__ == "__main__":
    sys.exit(main())
