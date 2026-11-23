# -*- coding: utf-8 -*-
"""一键跑完整流程：采集 → 清洗 → 可视化

用法
----
    # 完整流程（需要先设置环境变量 QD_COOKIE）
    python run_all.py --pages 3

    # 跳过采集，直接用已有 CSV 重新清洗并出图（改图表样式时最常用）
    python run_all.py --skip-crawl

    # 指定输出目录、展示条数、分辨率
    python run_all.py --skip-crawl --outdir . --topn 20 --dpi 200

说明
----
所有相对路径（--raw / --out / --summary / --outdir）都相对于 qnv-python/ 目录，
保持与单独运行三个脚本时一致。
"""
import argparse
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PYDIR = os.path.join(HERE, "qnv-python")
VERSION = "1.1.0"


def run(script, args):
    """调用 qnv-python 下的脚本，失败即中断整个流水线。"""
    cmd = [sys.executable, os.path.join(PYDIR, script)] + args
    print(f"\n>>> {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd, cwd=PYDIR)
    if result.returncode != 0:
        raise SystemExit(f"{script} 执行失败，退出码 {result.returncode}")


def main():
    parser = argparse.ArgumentParser(description="起点榜单数据可视化：一键流水线")
    parser.add_argument("--pages", type=int, default=3, help="采集页数（每页约 20 条）")
    parser.add_argument("--gender", choices=["male", "female", "all"], default="male", help="榜单频道")
    parser.add_argument("--raw", default="qidian_readindex_books.csv", help="原始数据文件名")
    parser.add_argument("--out", default="clean_data.csv", help="清洗后数据文件名")
    parser.add_argument("--summary", default="clean_summary.json", help="统计摘要文件名")
    parser.add_argument("--outdir", default=".", help="图表输出目录（相对 qnv-python/）")
    parser.add_argument("--topn", type=int, default=15, help="TOP 排名图展示条数")
    parser.add_argument("--dpi", type=int, default=300, help="图片分辨率")
    parser.add_argument("--append", action="store_true", help="采集时在已有 CSV 上续爬")
    parser.add_argument("--skip-crawl", action="store_true", help="跳过采集，只用已有 CSV")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}", help="显示版本号后退出")
    args = parser.parse_args()

    if not os.path.isdir(PYDIR):
        raise SystemExit(f"找不到脚本目录：{PYDIR}")
    if args.pages < 1:
        raise SystemExit("--pages 必须大于 0")
    if args.topn < 1:
        raise SystemExit("--topn 必须大于 0")
    if args.dpi < 72:
        raise SystemExit("--dpi 不能小于 72")

    print(f"起点榜单流水线 v{VERSION}：采集={'是' if not args.skip_crawl else '否'}，"
          f"页数={args.pages}，TOP={args.topn}，DPI={args.dpi}")
    started = time.time()
    if not args.skip_crawl:
        if not os.environ.get("QD_COOKIE", "").strip():
            raise SystemExit("缺少 Cookie：请先设置环境变量 QD_COOKIE，或加 --skip-crawl 使用已有数据")
        crawl_args = [
            "--start-page", "1",
            "--end-page", str(args.pages),
            "--gender", args.gender,
            "--out", args.raw,
        ]
        if args.append:
            crawl_args.append("--append")
        run("qidian_spider.py", crawl_args)
    else:
        print("已跳过采集，使用 qnv-python/ 下的已有数据")

    run("clean_data.py", ["--input", args.raw, "--out", args.out, "--summary", args.summary])
    run("data_visualization.py", [
        "--input", args.out,
        "--outdir", args.outdir,
        "--topn", str(args.topn),
        "--dpi", str(args.dpi),
    ])
    print(f"\n全部完成，耗时 {time.time() - started:.1f} 秒。")


if __name__ == "__main__":
    main()
