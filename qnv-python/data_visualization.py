# -*- coding: utf-8 -*-
"""榜单数据可视化脚本

基于清洗后的数据集生成 5 张统计图表（默认输出到当前目录）：
    01_分类数量分布.png   各分类上榜小说数量柱状图
    02_TOP15热度排名.png  榜单前 15 名条形图（排名越小越靠前）
    03_字数分布.png       上榜小说字数（万字）分布直方图
    04_分类占比饼图.png   各分类占比
    05_分类平均字数.png   各分类上榜作品的平均字数（新增：反映分类的篇幅特征）

用法：python data_visualization.py --input clean_data.csv --outdir . --topn 15
"""
import argparse
import os

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import font_manager

# 中文字体候选：Windows / macOS / Linux 各取一个，避免换机器就出现方块
CANDIDATES = ["Microsoft YaHei", "SimHei", "PingFang SC", "Noto Sans CJK SC", "WenQuanYi Micro Hei"]


def setup_font():
    """从系统已安装字体里挑选第一个可用的中文字体。"""
    installed = {f.name for f in font_manager.fontManager.ttflist}
    for name in CANDIDATES:
        if name in installed:
            matplotlib.rcParams["font.sans-serif"] = [name]
            print(f"使用中文字体：{name}")
            break
    else:
        print("警告：未找到中文字体，图表中的中文可能显示为方块")
    matplotlib.rcParams["axes.unicode_minus"] = False


def save(fig, outdir, name):
    path = os.path.join(outdir, name)
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"已保存 {path}")


def main():
    parser = argparse.ArgumentParser(description="起点榜单一键出图")
    parser.add_argument("--input", default="clean_data.csv")
    parser.add_argument("--outdir", default=".")
    parser.add_argument("--topn", type=int, default=15)
    args = parser.parse_args()

    setup_font()
    os.makedirs(args.outdir, exist_ok=True)
    df = pd.read_csv(args.input, encoding="utf-8-sig")

    cat_count = df["分类"].value_counts()
    words = df["字数(万)"].dropna()

    # 图 1：分类数量分布
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(cat_count.index, cat_count.values, color="#4A90E2")
    ax.set_title(f"起点阅读榜小说分类数量分布（共 {len(df)} 本）", fontsize=14)
    ax.set_xlabel("小说分类")
    ax.set_ylabel("数量（本）")
    ax.tick_params(axis="x", rotation=45)
    for x, y in zip(cat_count.index, cat_count.values):
        ax.text(x, y + 0.2, str(y), ha="center", fontsize=10)
    save(fig, args.outdir, "01_分类数量分布.png")

    # 图 2：TOP N 排名
    top = df.nsmallest(args.topn, "排名").sort_values("排名", ascending=False)
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.barh(top["小说名称"], top["排名"], color="#FF6B6B")
    ax.set_title(f"起点阅读榜 TOP{args.topn} 小说", fontsize=14)
    ax.set_xlabel("排名（数字越小排名越高）")
    ax.invert_xaxis()
    for y, x in zip(top["小说名称"], top["排名"]):
        ax.text(x - 0.2, y, str(x), va="center", ha="right", fontsize=9)
    save(fig, args.outdir, "02_TOP15热度排名.png")

    # 图 3：字数分布
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(words, bins=10, color="#50C878", edgecolor="black", alpha=0.75)
    ax.set_title("起点阅读榜小说字数分布", fontsize=14)
    ax.set_xlabel("字数（万字）")
    ax.set_ylabel("小说数量（本）")
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    save(fig, args.outdir, "03_字数分布.png")

    # 图 4：分类占比
    fig, ax = plt.subplots(figsize=(9, 9))
    ax.pie(cat_count.values, labels=cat_count.index, autopct="%1.1f%%",
           startangle=90, colors=plt.cm.Set3.colors)
    ax.set_title("起点阅读榜小说分类占比", fontsize=14)
    save(fig, args.outdir, "04_分类占比饼图.png")

    # 图 5：各分类平均字数（新增维度：篇幅特征）
    avg = df.groupby("分类")["字数(万)"].mean().sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(avg.index, avg.values, color="#7B68EE")
    ax.set_title("各分类上榜作品平均字数", fontsize=14)
    ax.set_xlabel("小说分类")
    ax.set_ylabel("平均字数（万字）")
    ax.tick_params(axis="x", rotation=45)
    for x, y in zip(avg.index, avg.values):
        ax.text(x, y + 1, f"{y:.0f}", ha="center", fontsize=9)
    save(fig, args.outdir, "05_分类平均字数.png")


if __name__ == "__main__":
    main()