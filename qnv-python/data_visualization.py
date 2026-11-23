# -*- coding: utf-8 -*-
"""榜单数据可视化脚本

基于 clean_data.py 输出的清洗数据生成 7 张统计图表：

    01_分类数量分布.png      各分类上榜作品数量（标注占比）
    02_TOP15热度排名.png     榜单前 N 名（横轴为名次，颜色按名次渐变）
    03_字数分布.png          字数（万字）直方图（标注中位数与平均值）
    04_分类占比饼图.png      各分类占比（不足 3% 的小类合并为「其他」）
    05_分类平均字数.png      作品数不少于 3 的分类的平均字数（附样本量）
    06_作者上榜作品数.png    上榜作品最多的作者 TOP10
    07_分类字数箱线图.png    主要分类的字数分布箱线图

设计要点：
- 使用 Agg 无界面后端，服务器 / CI 环境也能稳定出图；
- 中文字体自动探测（Windows / macOS / Linux），换机器不会出现方块；
- 统一配色、网格与留白，默认 300 DPI，可直接放进报告或 PPT。

用法：
    python data_visualization.py --input clean_data.csv --outdir . --topn 15 --dpi 300
"""
import argparse
import os

import matplotlib

matplotlib.use("Agg")  # 必须在 pyplot 之前设置，保证无显示器环境也能出图

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import font_manager, ticker

# 中文字体候选：Windows / macOS / Linux 各取若干，按优先级挑选
CANDIDATES = [
    "Microsoft YaHei",
    "SimHei",
    "PingFang SC",
    "Hiragino Sans GB",
    "Noto Sans CJK SC",
    "Source Han Sans SC",
    "WenQuanYi Micro Hei",
]

# 统一配色，保证 7 张图视觉一致
COLOR_MAIN = "#4A90E2"
COLOR_HOT = "#E74C3C"
COLOR_MID = "#2ECC71"
COLOR_LONG = "#7B68EE"
COLOR_AUTHOR = "#16A085"
COLOR_SET = [
    "#4A90E2", "#E74C3C", "#2ECC71", "#7B68EE", "#F5A623",
    "#16A085", "#9B59B6", "#E67E22", "#34495E", "#95A5A6",
]

SMALL_SLICE = 0.03   # 饼图中占比小于该阈值的分类合并为「其他」
MIN_GROUP = 3        # 平均字数 / 箱线图只统计作品数不少于该值的分类

REQUIRED_COLUMNS = ["排名", "小说名称", "作者", "分类", "字数(万)"]


def setup_style():
    """挑选系统中可用的中文字体，并统一图表样式。"""
    installed = {f.name for f in font_manager.fontManager.ttflist}
    for name in CANDIDATES:
        if name in installed:
            plt.rcParams["font.sans-serif"] = [name, "DejaVu Sans"]
            print(f"使用中文字体：{name}")
            break
    else:
        print("警告：未找到中文字体，图表中的中文可能显示为方块（可安装微软雅黑或思源黑体）")

    plt.rcParams.update({
        "axes.unicode_minus": False,
        "font.family": "sans-serif",
        "axes.titlesize": 15,
        "axes.titleweight": "bold",
        "axes.labelsize": 11,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
    })


def save(fig, outdir, name, dpi):
    """统一保存：紧凑布局 + 白底 + 指定分辨率。"""
    fig.tight_layout()
    path = os.path.join(outdir, name)
    fig.savefig(path, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"已保存 {path}")


def style_axis(ax, grid_axis="y"):
    """统一坐标轴样式：浅色虚线网格，置于图形下方。"""
    ax.grid(axis=grid_axis, linestyle="--", alpha=0.35)
    ax.set_axisbelow(True)


def merge_small(counts, threshold=SMALL_SLICE):
    """把占比过小的分类合并成「其他」，避免饼图碎成一片。"""
    total = counts.sum()
    keep = counts[counts / total >= threshold]
    rest = counts[counts / total < threshold].sum()
    if rest:
        keep = pd.concat([keep, pd.Series({"其他": rest})])
    return keep


def load_data(path):
    """读取并校验清洗后的数据集。"""
    if not os.path.exists(path):
        raise SystemExit(f"找不到输入文件：{path}（请先运行 clean_data.py）")

    df = pd.read_csv(path, encoding="utf-8-sig")
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise SystemExit(f"输入文件缺少字段：{missing}，当前字段：{list(df.columns)}")

    df = df[df["小说名称"].notna()].copy()
    if df.empty:
        raise SystemExit("数据集为空，没有可绘制的记录")

    # 兼容手工整理的 CSV：文本字段补「未知」，数值字段强制转成数字
    for col in ("小说名称", "作者", "分类"):
        df[col] = df[col].astype("string").fillna("未知").str.strip()
    df["排名"] = pd.to_numeric(df["排名"], errors="coerce").fillna(0).astype(int)
    df["字数(万)"] = pd.to_numeric(df["字数(万)"], errors="coerce")
    return df


def main():
    parser = argparse.ArgumentParser(description="起点榜单数据可视化（一键出 7 张图）")
    parser.add_argument("--input", default="clean_data.csv", help="清洗后的 CSV")
    parser.add_argument("--outdir", default=".", help="图表输出目录")
    parser.add_argument("--topn", type=int, default=15, help="TOP 排名图展示的条数")
    parser.add_argument("--dpi", type=int, default=300, help="输出图片分辨率")
    args = parser.parse_args()

    if args.topn < 1:
        raise SystemExit("--topn 必须大于 0")
    if args.dpi < 72:
        raise SystemExit("--dpi 不能小于 72")

    setup_style()
    os.makedirs(args.outdir, exist_ok=True)
    df = load_data(args.input)

    counts = df["分类"].value_counts()
    total = int(counts.sum())
    words = df["字数(万)"].dropna()
    if words.empty:
        print("警告：没有有效的字数数据，将跳过 03 / 05 / 07 三张图")

    # ---------------------------------------------------------------- 图 1
    # 分类数量分布：看清题材集中度
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(counts.index, counts.values, color=COLOR_MAIN, width=0.62)
    ax.set_title(f"起点阅读榜小说分类数量分布（共 {total} 本）", pad=14)
    ax.set_xlabel("小说分类")
    ax.set_ylabel("数量（本）")
    plt.setp(ax.get_xticklabels(), rotation=40, ha="right")
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax.set_ylim(0, counts.max() * 1.2)
    style_axis(ax)
    for bar, value in zip(bars, counts.values):
        ax.text(
            bar.get_x() + bar.get_width() / 2, value,
            f"{value}（{value / total:.1%}）",
            ha="center", va="bottom", fontsize=9,
        )
    save(fig, args.outdir, "01_分类数量分布.png", args.dpi)

    # ---------------------------------------------------------------- 图 2
    # TOP N 排名：条形长度即名次，颜色越深名次越高
    top = df.nsmallest(args.topn, "排名").sort_values("排名", ascending=False)
    ranks = top["排名"].astype(int).tolist()
    lo, hi = min(ranks), max(ranks)
    span = max(hi - lo, 1)
    cmap = matplotlib.colormaps["Reds"]
    colors = [cmap(0.85 - 0.55 * (r - lo) / span) for r in ranks]

    fig, ax = plt.subplots(figsize=(10, 7))
    bars = ax.barh(top["小说名称"], ranks, color=colors, height=0.62)
    ax.set_title(f"起点阅读榜 TOP{len(top)} 小说", pad=14)
    ax.set_xlabel("名次（越靠右排名越高）")
    # 左端大于右端即为反转：名次 1 落在最右侧，符合「越高越靠右」的直觉
    ax.set_xlim(hi + max(2, hi * 0.08), 0)
    ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    for bar, rank in zip(bars, ranks):
        ax.annotate(
            str(rank),
            (rank, bar.get_y() + bar.get_height() / 2),
            xytext=(-6, 0), textcoords="offset points",
            va="center", ha="right", fontsize=9, color="#333333",
        )
    save(fig, args.outdir, f"02_TOP{len(top)}热度排名.png", args.dpi)

    # ---------------------------------------------------------------- 图 3
    # 字数分布：热门作品的篇幅集中在哪个区间
    if not words.empty:
        fig, ax = plt.subplots(figsize=(10, 6))
        heights, bins, _ = ax.hist(
            words, bins=12, color=COLOR_MID, edgecolor="white", linewidth=0.8,
        )
        median, mean = float(words.median()), float(words.mean())
        ax.axvline(median, color=COLOR_HOT, linestyle="--", linewidth=1.6,
                   label=f"中位数 {median:.1f} 万字")
        ax.axvline(mean, color="#E67E22", linestyle=":", linewidth=1.6,
                   label=f"平均值 {mean:.1f} 万字")
        ax.set_title("起点阅读榜小说字数分布", pad=14)
        ax.set_xlabel("字数（万字）")
        ax.set_ylabel("小说数量（本）")
        ax.set_ylim(0, max(heights) * 1.18)
        style_axis(ax)
        for count, left, right in zip(heights, bins[:-1], bins[1:]):
            if count:
                ax.text((left + right) / 2, count, f"{int(count)}",
                        ha="center", va="bottom", fontsize=8, color="#444444",
                        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.8, "pad": 0.8})
        ax.legend(frameon=False)
        save(fig, args.outdir, "03_字数分布.png", args.dpi)

    # ---------------------------------------------------------------- 图 4
    # 分类占比：小类合并，避免饼图过于零碎
    pie_data = merge_small(counts)
    fig, ax = plt.subplots(figsize=(9, 9))
    ax.pie(
        pie_data.values,
        labels=pie_data.index,
        autopct=lambda p: f"{p:.1f}%" if p >= 4 else "",
        startangle=90,
        counterclock=False,
        colors=COLOR_SET[: len(pie_data)],
        wedgeprops={"edgecolor": "white", "linewidth": 1.2},
        textprops={"fontsize": 11},
    )
    ax.set_title(f"起点阅读榜小说分类占比（共 {total} 本）", pad=20)
    save(fig, args.outdir, "04_分类占比饼图.png", args.dpi)

    # ---------------------------------------------------------------- 图 5
    # 各分类平均字数：样本太少的分类没有统计意义，直接排除
    if not words.empty:
        stats = (
            df.groupby("分类")["字数(万)"]
            .agg(["mean", "count"])
            .dropna(subset=["mean"])
        )
        stats = stats[stats["count"] >= MIN_GROUP].sort_values("mean", ascending=False)
        if stats.empty:
            print(f"警告：没有作品数 ≥ {MIN_GROUP} 的分类，跳过 05 图")
        else:
            positions = range(len(stats))
            fig, ax = plt.subplots(figsize=(10, 6))
            bars = ax.bar(positions, stats["mean"], color=COLOR_LONG, width=0.6)
            ax.set_title(f"各分类上榜作品平均字数（作品数 ≥ {MIN_GROUP} 的分类）", pad=14)
            ax.set_xlabel("小说分类")
            ax.set_ylabel("平均字数（万字）")
            ax.set_xticks(list(positions))
            ax.set_xticklabels(
                [f"{cat}\n(n={int(n)})" for cat, n in zip(stats.index, stats["count"])],
                rotation=20, ha="right",
            )
            ax.set_ylim(0, stats["mean"].max() * 1.18)
            style_axis(ax)
            baseline = float(words.mean())
            ax.axhline(baseline, color="#95A5A6", linestyle=":", linewidth=1.4,
                       label=f"全站均值 {baseline:.1f} 万字")
            for bar, value in zip(bars, stats["mean"]):
                ax.text(bar.get_x() + bar.get_width() / 2, value,
                        f"{value:.0f}", ha="center", va="bottom", fontsize=9)
            ax.legend(frameon=False, loc="upper right")
            save(fig, args.outdir, "05_分类平均字数.png", args.dpi)

    # ---------------------------------------------------------------- 图 6
    # 作者上榜作品数：头部作者的榜单集中度
    author = df["作者"].value_counts().head(10).sort_values()
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(author.index, author.values, color=COLOR_AUTHOR, height=0.6)
    ax.set_title("上榜作品最多的作者 TOP10", pad=14)
    ax.set_xlabel("上榜作品数（本）")
    ax.set_xlim(0, author.max() * 1.18)
    ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    style_axis(ax, grid_axis="x")
    for bar, value in zip(bars, author.values):
        ax.annotate(
            str(value),
            (value, bar.get_y() + bar.get_height() / 2),
            xytext=(4, 0), textcoords="offset points",
            va="center", ha="left", fontsize=9,
        )
    save(fig, args.outdir, "06_作者上榜作品数.png", args.dpi)

    # ---------------------------------------------------------------- 图 7
    # 主要分类的字数箱线图：比较篇幅的离散程度
    if not words.empty:
        main_cats = [c for c in counts.index if int((df["分类"] == c).sum()) >= MIN_GROUP][:8]
        data, labels = [], []
        for cat in main_cats:
            values = df.loc[df["分类"] == cat, "字数(万)"].dropna().to_numpy()
            if len(values) >= MIN_GROUP:
                data.append(values)
                labels.append(cat)

        if not data:
            print(f"警告：没有作品数 ≥ {MIN_GROUP} 的分类，跳过 07 图")
        else:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.boxplot(
                data,
                patch_artist=True,
                widths=0.55,
                boxprops={"facecolor": "#BFD7F3", "color": "#2C3E50"},
                medianprops={"color": COLOR_HOT, "linewidth": 2},
                whiskerprops={"color": "#2C3E50"},
                capprops={"color": "#2C3E50"},
                flierprops={
                    "marker": "o", "markersize": 3, "linestyle": "none",
                    "markerfacecolor": "#E67E22", "alpha": 0.7,
                },
            )
            ax.set_title(f"主要分类的字数分布（作品数 ≥ {MIN_GROUP}，箱线图）", pad=14)
            ax.set_xlabel("小说分类")
            ax.set_ylabel("字数（万字）")
            ax.set_xticks(range(1, len(labels) + 1))
            ax.set_xticklabels(labels, rotation=20, ha="right")
            style_axis(ax)
            save(fig, args.outdir, "07_分类字数箱线图.png", args.dpi)

    print(f"\n全部图表已输出到：{os.path.abspath(args.outdir)}")


if __name__ == "__main__":
    main()
