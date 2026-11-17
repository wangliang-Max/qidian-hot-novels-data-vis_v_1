# 起点中文网热搜小说数据可视化

对起点中文网「阅读榜（热搜）」的榜单数据做一次完整的 **采集 → 清洗 → 可视化** 小实践：
用 Python 抓取榜单数据，清洗成规范数据集，再用 matplotlib 输出一组中文统计图表。

## 目录结构

```
qidian-hot-novels/
├── requirements.txt              # 依赖清单
├── qnv-python/
│   ├── qidian_spider.py          # ① 爬虫：分页抓取榜单 JSON 接口
│   ├── clean_data.py             # ② 清洗：统一字段、字数转数值、去重
│   ├── data_visualization.py     # ③ 可视化：一次生成 5 张图表
│   ├── qidian_readindex_books.csv# 原始数据（爬虫输出）
│   ├── clean_data.csv            # 清洗后数据（清洗脚本输出，已 gitignore）
│   ├── 01_分类数量分布.png
│   ├── 02_TOP15热度排名.png
│   ├── 03_字数分布.png
│   ├── 04_分类占比饼图.png
│   └── 05_分类平均字数.png
└── README.md
```

## 环境依赖

Python 3.8+（开发环境 Python 3.13），依赖见 `requirements.txt`：

```bash
pip install -r requirements.txt
```

## 快速开始

```bash
cd qnv-python

# 1) 采集：Cookie 通过环境变量传入，不要写进代码
#    PowerShell:  $env:QD_COOKIE = "……"
#    Bash:        export QD_COOKIE="……"
python qidian_spider.py --start-page 1 --end-page 3 --out qidian_readindex_books.csv

# 2) 清洗：生成 clean_data.csv，并打印缺失值、分类分布等统计
python clean_data.py --input qidian_readindex_books.csv --out clean_data.csv

# 3) 可视化：生成 5 张图（可改 --outdir / --topn）
python data_visualization.py --input clean_data.csv --outdir . --topn 15
```

`QD_COOKIE` 的获取方式：浏览器打开榜单页 → F12 → Network → 任选一个请求 → 复制请求头里的 `Cookie`。

## 数据字段

| 字段 | 说明 |
| --- | --- |
| 排名 | 榜单名次，1 为最热 |
| 小说名称 / 作者 | 书名与作者笔名 |
| 分类 / 子类 | 一级分类（玄幻、仙侠……）与细分题材 |
| 字数 | 原文形如 `639.99万字`，清洗后转成数值列 `字数(万)` |
| 简介 | 作品简介，清洗时压成一行、截断到 80 字 |

## 图表说明

| 图表 | 说明 |
| --- | --- |
| 01_分类数量分布 | 各分类上榜作品数量，看题材集中度 |
| 02_TOP15热度排名 | 榜单前 15 名，横轴为名次 |
| 03_字数分布 | 字数（万字）直方图，看热门作品的篇幅区间 |
| 04_分类占比饼图 | 各分类占比 |
| 05_分类平均字数 | 各分类上榜作品的平均字数，反映题材的篇幅差异 |

## 代码设计要点

- **凭据不入库**：Cookie 从环境变量 `QD_COOKIE` 读取，仓库里不出现任何个人凭据。
- **抓取更稳**：单页失败按指数退避重试 3 次；翻页间随机休眠，降低触发风控的概率。
- **数据可复现**：爬虫 → 清洗 → 可视化三步解耦，每一步都能单独重跑；清洗脚本会打印缺失值、分类分布，便于检查数据质量。
- **换机器可跑**：中文字体从系统已安装字体里自动挑选（微软雅黑 / 黑体 / 苹方 / Noto），不再硬编码 `SimHei`。
- **图表可配**：`--input / --outdir / --topn` 全部参数化，图表按排名真实排序，不依赖输入行序。

## 数据说明

榜单页数与内容随时间变化，仓库中的 CSV 为采集当时的快照（60 条），仅用于课程练习与图表演示。