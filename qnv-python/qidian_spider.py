# -*- coding: utf-8 -*-
"""起点中文网阅读榜（热搜榜）数据采集脚本

功能说明
--------
1. 分页请求起点移动端的榜单 JSON 接口，逐页解析榜单小说信息；
2. Cookie 从环境变量 ``QD_COOKIE`` 读取，不把个人凭据写死在代码里（可公开提交）；
3. 单页请求失败自动重试（指数退避），页与页之间随机休眠，降低触发风控的概率；
4. 结果按「书名 + 作者」去重后写入 CSV，编码 utf-8-sig，Excel 可直接打开。

使用示例
--------
    # PowerShell 里先设置 Cookie（浏览器 F12 -> Network -> 任意请求 -> Cookie 复制）
    $env:QD_COOKIE = "……"
    python qidian_spider.py --start-page 1 --end-page 3 --out qidian_readindex_books.csv
"""
import argparse
import csv
import logging
import os
import random
import re
import time

import requests

API_URL = "https://m.qidian.com/webcommon/rank/readIndexlist"
FIELDS = ["排名", "小说名称", "作者", "分类", "子类", "字数", "简介"]

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
    return session


def crawl_page(session, page_num, retries=3):
    """抓取单页榜单，返回 [排名, 书名, 作者, 分类, 子类, 字数, 简介] 列表。"""
    params = {
        "gender": "male",
        "pageNum": page_num,
        "catId": "-1",
        "_csrfToken": session.csrf_token,
    }
    for attempt in range(1, retries + 1):
        try:
            resp = session.get(API_URL, params=params, timeout=10)
            resp.raise_for_status()
            payload = resp.json()
        except Exception as exc:  # 网络错误 / JSON 解析错误统一重试
            wait = attempt * 2
            log.warning("第 %s 页第 %s 次请求失败：%s，%s 秒后重试", page_num, attempt, exc, wait)
            time.sleep(wait)
            continue

        records = (payload.get("data") or {}).get("records") or []
        if not records:
            log.warning("第 %s 页没有返回数据，可能已到榜单末尾或 Cookie 失效", page_num)
            return []

        rows = []
        for book in records:
            rows.append([
                book.get("rankNum", 0),
                book.get("bName", "未知"),
                book.get("bAuth", "未知"),
                book.get("cat", "未知"),
                book.get("subCat", ""),
                book.get("cnt", "未知"),
                (book.get("desc") or "").replace("\n", " ").strip(),
            ])
        log.info("第 %s 页抓取成功：%s 条", page_num, len(rows))
        return rows

    log.error("第 %s 页重试 %s 次仍失败，跳过", page_num, retries)
    return []


def save_csv(rows, path):
    """保存为 CSV，按「书名 + 作者」去重，保持榜单排名顺序。"""
    seen, unique = set(), []
    for row in rows:
        key = (row[1], row[2])
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    with open(path, "w", encoding="utf-8-sig", newline="") as fp:
        writer = csv.writer(fp)
        writer.writerow(FIELDS)
        writer.writerows(unique)
    log.info("已保存 %s 条数据到 %s（去重 %s 条）", len(unique), path, len(rows) - len(unique))


def main():
    parser = argparse.ArgumentParser(description="起点阅读榜爬虫")
    parser.add_argument("--start-page", type=int, default=1, help="起始页码")
    parser.add_argument("--end-page", type=int, default=3, help="结束页码（含）")
    parser.add_argument("--out", default="qidian_readindex_books.csv", help="输出 CSV 路径")
    parser.add_argument("--min-delay", type=float, default=2.0, help="翻页最小休眠秒数")
    parser.add_argument("--max-delay", type=float, default=3.5, help="翻页最大休眠秒数")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    cookie = os.environ.get("QD_COOKIE", "").strip()
    if not cookie:
        raise SystemExit("缺少 Cookie：请先设置环境变量 QD_COOKIE（见文件头部说明）")

    session = build_session(cookie)
    all_rows = []
    for page in range(args.start_page, args.end_page + 1):
        rows = crawl_page(session, page)
        if not rows:
            break
        all_rows.extend(rows)
        time.sleep(random.uniform(args.min_delay, args.max_delay))

    if not all_rows:
        raise SystemExit("没有抓到任何数据，请检查 Cookie 是否过期")
    save_csv(all_rows, args.out)


if __name__ == "__main__":
    main()