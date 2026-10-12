import pandas as pd
import matplotlib.pyplot as plt

# 解决matplotlib中文乱码
plt.rcParams["font.sans-serif"] = ["SimHei"]
plt.rcParams["axes.unicode_minus"] = False

# 1. 读取数据 - 修正为阅读榜的文件名
df = pd.read_csv("qidian_readindex_books.csv", encoding="utf-8-sig")

# 2. 数据清洗
# 清洗字数字段：去掉"万字"，转换为数值
df["字数(万)"] = df["字数"].str.replace("万字", "").astype(float)

# 打印数据概览
print("数据基本信息：")
print(df.info())
print("\n数据前5行预览：")
print(df.head())

# 3. 图表1：小说分类数量分布柱状图
plt.figure(figsize=(10, 6))
category_count = df["分类"].value_counts().sort_values(ascending=False)
plt.bar(category_count.index, category_count.values, color="#4A90E2")
plt.title("起点阅读榜小说分类数量分布", fontsize=14)
plt.xlabel("小说分类", fontsize=12)
plt.ylabel("数量（本）", fontsize=12)
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig("01_分类数量分布.png", dpi=300)
plt.show()

# 4. 图表2：TOP15小说排名条形图
plt.figure(figsize=(10, 7))
top15 = df.head(15).sort_values("排名", ascending=False)
plt.barh(top15["小说名称"], top15["排名"], color="#FF6B6B")
plt.title("起点阅读榜TOP15小说", fontsize=14)
plt.xlabel("排名（数字越小排名越高）", fontsize=12)
plt.gca().invert_xaxis()
plt.tight_layout()
plt.savefig("02_TOP15热度排名.png", dpi=300)
plt.show()

# 5. 图表3：小说字数分布直方图
plt.figure(figsize=(10, 6))
plt.hist(df["字数(万)"], bins=10, color="#50C878", edgecolor="black", alpha=0.7)
plt.title("起点阅读榜小说字数分布", fontsize=14)
plt.xlabel("字数（万字）", fontsize=12)
plt.ylabel("小说数量（本）", fontsize=12)
plt.grid(axis="y", linestyle="--", alpha=0.5)
plt.tight_layout()
plt.savefig("03_字数分布.png", dpi=300)
plt.show()

# 6. 图表4：小说分类占比饼图
plt.figure(figsize=(9, 9))
plt.pie(
    category_count.values,
    labels=category_count.index,
    autopct="%1.1f%%",
    startangle=90,
    colors=plt.cm.Set3.colors
)
plt.title("起点阅读榜小说分类占比", fontsize=14)
plt.tight_layout()
plt.savefig("04_分类占比饼图.png", dpi=300)
plt.show()

print("\n所有图表已生成并保存！")
