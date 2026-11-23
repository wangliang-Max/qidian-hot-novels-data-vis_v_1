# -*- coding: utf-8 -*-
"""数据清洗脚本

把爬虫抓下来的原始 CSV 处理成可直接分析的数据集：

1. 文本字段去掉首尾空白与全角空格，缺失值补「未知」；
2. 把「字数」从 ``639.99万字`` 转成数值列「字数(万)」，
   兼容 ``12345``、``3000字``、``1.2亿字`` 等写法，无法解析记为缺失；
3. 简介压成一行并截断到 80 字，避免撑爆 CSV 单元格；
4. 排名转整数，按「书名 + 作者」去重（与爬虫口径一致），并新增「字数等级」；
5. 输出 ``clean_data.csv`` 与 ``clean_summary.json``（统计摘要，可直接写进报告）。

用法：
    python clean_data.py --input qidian_readindex_books.csv --out clean_data.csv
"""
import argparse
import json
import os
import re

import numpy as np
import pandas as pd

RAW_COLUMNS = ["排名", "小说名称", "作者", "分类", "子类", "字数", "简介"]
TEXT_COLUMNS = ["小说名称", "作者", "分类", "子类"]

WORD_RE = re.compile(r"(\d+(?:\.\d+)?)")

# 字数分级（单位：万字），用于给作品贴「篇幅标签」
LEVEL_BINS = [
    (0, 100, "短篇"),
    (100, 300, "中篇"),
    (300, 1000, "长篇"),
    (1000, float("inf"), "超长篇"),
]


def load(path):
    """读取原始 CSV，并校验必需字段。"""
    if not os.path.exists(path):
        raise SystemExit(f"找不到输入文件：{path}（请先运行 qidian_spider.py 或准备一份 CSV）")

    try:
        df = pd.read_csv(path, encoding="utf-8-sig")
    except pd.errors.EmptyDataError:
        raise SystemExit(f"输入文件为空：{path}")

    missing = [c for c in RAW_COLUMNS if c not in df.columns]
    if missing:
        raise SystemExit(f"输入文件缺少字段：{missing}，当前字段：{list(df.columns)}")
    return df[RAW_COLUMNS].copy()


def parse_words(value):
    """把「639.99万字」这类文本解析成以「万字」为单位的浮点数。"""
    if pd.isna(value):
        return np.nan

    text = str(value).strip().replace(",", "").replace("\u3000", " ")
    match = WORD_RE.search(text)
    if not match:
        return np.nan

    number = float(match.group(1))
    if "亿" in text:          # 1.2亿字 -> 12000 万字
        number *= 10000
    elif "万" not in text:    # 3000字 -> 0.3 万字
        number /= 10000

    return number if number > 0 else np.nan


def word_level(words):
    """按字数打篇幅标签。"""
    for low, high, label in LEVEL_BINS:
        if low <= words < high:
            return label
    return "未知"


def clean(df):
    """执行清洗，返回（清洗后的 DataFrame, 去重条数）。"""
    df = df.copy()

    # 1. 文本字段去空白（含全角空格 \u3000），空值统一补「未知」
    for col in TEXT_COLUMNS:
        df[col] = (
            df[col].astype("string")
            .str.replace("\u3000", "", regex=False)
            .str.strip()
            .fillna("")
        )
    for col in ("小说名称", "作者", "分类"):
        df[col] = df[col].replace("", "未知")

    # 2. 字数字段：解析成数值（万字），保留两位小数
    df["字数(万)"] = df["字数"].map(parse_words).astype("float64").round(2)

    # 3. 简介压成一行，最多 80 字
    df["简介"] = (
        df["简介"].astype("string").fillna("")
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
        .str.slice(0, 80)
    )

    # 4. 排名转整数
    df["排名"] = pd.to_numeric(df["排名"], errors="coerce").fillna(0).astype(int)

    # 5. 按「书名 + 作者」去重（与爬虫一致），无名次的记录排在最后
    before = len(df)
    df = df.drop_duplicates(subset=["小说名称", "作者"], keep="first")
    duplicates = before - len(df)

    order = df["排名"].where(df["排名"] > 0, 10 ** 6)
    df = (
        df.assign(_order=order)
        .sort_values(["_order", "小说名称"], kind="stable")
        .drop(columns="_order")
        .reset_index(drop=True)
    )

    # 6. 新增篇幅等级标签
    df["字数等级"] = df["字数(万)"].map(
        lambda value: word_level(value) if pd.notna(value) else "未知"
    )
    return df, duplicates


def build_summary(df, raw_count, duplicates):
    """生成统计摘要（JSON），便于直接引用到报告 / PPT。"""
    words = df["字数(万)"].dropna()
    categories = df["分类"].value_counts()
    authors = df["作者"].value_counts()

    def stat(func):
        return round(float(func(words)), 2) if len(words) else None

    return {
        "原始记录数": int(raw_count),
        "清洗后记录数": int(len(df)),
        "重复记录数": int(duplicates),
        "字数缺失数": int(df["字数(万)"].isna().sum()),
        "分类数": int(df["分类"].nunique()),
        "字数统计(万字)": {
            "最小": stat(np.min),
            "中位数": stat(np.median),
            "平均": stat(np.mean),
            "最大": stat(np.max),
        },
        "分类分布": {str(k): int(v) for k, v in categories.items()},
        "篇幅等级分布": {str(k): int(v) for k, v in df["字数等级"].value_counts().items()},
        "作者上榜数TOP10": {str(k): int(v) for k, v in authors.head(10).items()},
        "TOP3分类": [str(x) for x in categories.head(3).index],
    }


def report(df, summary):
    """在终端打印一份可读的统计报告。"""
    stats = summary["字数统计(万字)"]
    print(f"原始记录：{summary['原始记录数']} 条，清洗后：{summary['清洗后记录数']} 条"
          f"（去重 {summary['重复记录数']} 条）")
    print(f"字数缺失：{summary['字数缺失数']} 条；分类数：{summary['分类数']} 个")
    print(f"字数（万字）：最小 {stats['最小']}，中位数 {stats['中位数']}，"
          f"平均 {stats['平均']}，最大 {stats['最大']}")
    print("\n分类分布：")
    print(df["分类"].value_counts().to_string())
    print("\n篇幅等级分布：")
    print(df["字数等级"].value_counts().to_string())
    print("\n上榜作品最多的作者 TOP5：")
    print(df["作者"].value_counts().head(5).to_string())


def ensure_parent(path):
    """确保输出文件的父目录存在。"""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)


def main():
    parser = argparse.ArgumentParser(description="起点榜单数据清洗")
    parser.add_argument("--input", default="qidian_readindex_books.csv", help="原始 CSV")
    parser.add_argument("--out", default="clean_data.csv", help="清洗后 CSV")
    parser.add_argument("--summary", default="clean_summary.json", help="统计摘要 JSON")
    args = parser.parse_args()

    raw = load(args.input)
    df, duplicates = clean(raw)
    summary = build_summary(df, len(raw), duplicates)
    report(df, summary)

    ensure_parent(args.out)
    ensure_parent(args.summary)
    df.to_csv(args.out, index=False, encoding="utf-8-sig")
    with open(args.summary, "w", encoding="utf-8") as fp:
        json.dump(summary, fp, ensure_ascii=False, indent=2)

    print(f"\n已输出 {args.out}")
    print(f"已输出 {args.summary}")


if __name__ == "__main__":
    main()
