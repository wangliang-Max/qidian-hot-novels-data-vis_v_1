# -*- coding: utf-8 -*-
"""数据清洗脚本

把爬虫抓下来的原始 CSV 处理成可直接用于分析的数据集：
1. 去掉字段首尾空白、全角空格；
2. 把「字数」从形如 ``639.99万字`` 的字符串转成数值型（单位：万字），无法解析的记为缺失；
3. 简介只保留第一句/前 80 字，去掉换行，避免影响 CSV 阅读；
4. 按「小说名称」去重，排名统一为整数；
5. 输出 ``clean_data.csv`` 并打印缺失值、分类分布等统计信息。

用法：python clean_data.py --input qidian_readindex_books.csv --out clean_data.csv
"""
import argparse

import pandas as pd

RAW_COLUMNS = ["排名", "小说名称", "作者", "分类", "子类", "字数", "简介"]


def load(path):
    df = pd.read_csv(path, encoding="utf-8-sig")
    missing = [c for c in RAW_COLUMNS if c not in df.columns]
    if missing:
        raise SystemExit(f"输入文件缺少字段：{missing}，当前字段：{list(df.columns)}")
    return df[RAW_COLUMNS].copy()


def clean(df):
    # 1. 文本字段去空白（含全角空格 \u3000）
    for col in ["小说名称", "作者", "分类", "子类"]:
        df[col] = df[col].astype(str).str.replace("\u3000", "", regex=False).str.strip()
    df["子类"] = df["子类"].fillna("").replace("nan", "")

    # 2. 字数字段：去掉「万字/万/字」，转成 float（单位：万字）
    word = df["字数"].astype(str).str.replace(r"[万字\s]", "", regex=True)
    df["字数(万)"] = pd.to_numeric(word, errors="coerce")

    # 3. 简介压成一行，最多 80 字
    df["简介"] = (
        df["简介"].fillna("").astype(str)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
        .str.slice(0, 80)
    )

    # 4. 排名转整数、按书名去重
    df["排名"] = pd.to_numeric(df["排名"], errors="coerce").fillna(0).astype(int)
    df = df.drop_duplicates(subset=["小说名称"]).sort_values("排名").reset_index(drop=True)

    # 5. 未知字数直接置为缺失，方便后面统计时排除
    df.loc[df["字数(万)"] <= 0, "字数(万)"] = pd.NA
    return df


def report(df, raw_count):
    print(f"原始记录：{raw_count} 条，清洗后：{len(df)} 条")
    print(f"字数缺失：{int(df['字数(万)'].isna().sum())} 条")
    print(f"字数（万字）：最小 {df['字数(万)'].min():.2f}，"
          f"中位数 {df['字数(万)'].median():.2f}，最大 {df['字数(万)'].max():.2f}")
    print("\n分类分布：")
    print(df["分类"].value_counts().to_string())
    print("\n子类 TOP5：")
    print(df[df["子类"] != ""]["子类"].value_counts().head(5).to_string())


def main():
    parser = argparse.ArgumentParser(description="起点榜单数据清洗")
    parser.add_argument("--input", default="qidian_readindex_books.csv")
    parser.add_argument("--out", default="clean_data.csv")
    args = parser.parse_args()

    raw = load(args.input)
    df = clean(raw)
    report(df, len(raw))
    df.to_csv(args.out, index=False, encoding="utf-8-sig")
    print(f"\n已输出 {args.out}")


if __name__ == "__main__":
    main()