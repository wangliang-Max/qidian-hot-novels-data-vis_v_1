# 起点中文网热搜小说数据可视化

对起点中文网「阅读榜（热搜）」做一次完整的 **采集 → 清洗 → 可视化** 小实践：
用 Python 抓取榜单 JSON，清洗成规范数据集，再用 matplotlib 输出一组中文统计图。

仓库自带一份 **60 条**榜单数据快照（`qidian_readindex_books.csv`），
即使没有 Cookie，也能直接复现全部图表。

## 目录结构

```text
qidian-hot-novels/
├── run_all.py                    # 一键流水线：采集 → 清洗 → 出图
├── requirements.txt              # 依赖清单
├── README.md
└── qnv-python/
    ├── qidian_spider.py          # ① 爬虫：分页抓取榜单 JSON 接口
    ├── clean_data.py             # ② 清洗：统一字段、字数值、去重、篇幅分级
    ├── data_visualization.py     # ③ 可视化：一次生成 7 张图表
    ├── qidian_readindex_books.csv # 原始数据（仓库自带快照）
    ├── clean_data.csv             # 清洗后数据（运行后生成，已 gitignore）
    ├── clean_summary.json         # 统计摘要（运行后生成，仓库保留一份快照）
    ├── 01_分类数量分布.png
    ├── 02_TOP15热度排名.png
    ├── 03_字数分布.png
    ├── 04_分类占比饼图.png
    ├── 05_分类平均字数.png
    ├── 06_作者上榜作品数.png
    └── 07_分类字数箱线图.png
```

## 环境依赖

- Python 3.9+（开发环境为 3.13）
- 依赖：`requests`、`pandas`、`numpy`、`matplotlib`
- 中文字体：脚本会自动探测微软雅黑 / 苹方 / 思源黑体等，找不到时会提示

```bash
pip install -r requirements.txt
```

## 快速开始

### 方式一：一键跑完整流程（需要 Cookie）

```bash
python run_all.py --pages 3
```

### 方式二：不重新采集，直接用仓库自带数据出图

```bash
python run_all.py --skip-crawl
```

几秒钟后，7 张 PNG 会生成在 `qnv-python/` 下。

### 方式三：分步执行

```bash
cd qnv-python

# 1. 采集（需要先设置 QD_COOKIE）
python qidian_spider.py --start-page 1 --end-page 3

# 2. 清洗
python clean_data.py

# 3. 出图（可调条数 / 分辨率 / 输出目录）
python data_visualization.py --topn 15 --dpi 300 --outdir .
```

### 获取 Cookie

1. 浏览器登录起点，按 `F12` 打开开发者工具；
2. 切到 **Network**，刷新任意移动端页面（或直接打开 `https://m.qidian.com/rank/readindex/`）；
3. 复制任意请求头里的 `Cookie`，设置到环境变量：

```powershell
# PowerShell
$env:QD_COOKIE = "……"
```

```bash
# bash
export QD_COOKIE="……"
```

> Cookie 是个人凭据，项目只从环境变量读取，不会写进代码或提交到仓库。

## 数据字段

| 字段 | 说明 |
| --- | --- |
| 排名 | 榜单名次，1 为最高 |
| 小说名称 | 书名 |
| 作者 | 作者名 |
| 分类 | 一级分类（玄幻、仙侠、都市……） |
| 子类 | 二级分类（如 东方玄幻、修真文明） |
| 字数 | 原始文本，如 `639.99万字` |
| 简介 | 作品简介，清洗时压成一行并截断到 80 字 |
| 字数(万) | 清洗后新增，数值型，单位「万字」 |
| 字数等级 | 清洗后新增：短篇 / 中篇 / 长篇 / 超长篇 |

## 图表说明

| 文件 | 内容 | 说明 |
| --- | --- | --- |
| `01_分类数量分布.png` | 各分类上榜作品数 | 柱状图，标注数量与占比，看题材集中度 |
| `02_TOP15热度排名.png` | 榜单前 15 名 | 横轴为名次且反向排列，颜色越深名次越高 |
| `03_字数分布.png` | 字数直方图 | 同时标注中位数与平均值，看热门篇幅区间 |
| `04_分类占比饼图.png` | 分类占比 | 占比不足 3% 的小类合并为「其他」 |
| `05_分类平均字数.png` | 各分类平均字数 | 只统计作品数 ≥ 3 的分类，并标注样本量 |
| `06_作者上榜作品数.png` | 上榜最多的作者 TOP10 | 横向柱状图，看头部作者集中度 |
| `07_分类字数箱线图.png` | 分类字数分布 | 箱线图展示中位数、四分位与离群值 |

所有图默认 300 DPI，可直接放进报告或 PPT；`--topn`、`--dpi`、`--outdir` 均可调整。

## 统计口径

- **去重**：爬虫与清洗统一按「书名 + 作者」去重，避免同名不同书被误删；
- **字数**：统一换算成「万字」，兼容 `12345`、`3000字`、`1.2亿字` 等写法；
- **平均字数**：样本量小于 3 的分类不参与平均，避免单本书拉高整体；
- **饼图**：占比小于 3% 的分类合并为「其他」，防止图例过于零碎。

## 代码设计要点

- **凭据不入库**：Cookie 从环境变量 `QD_COOKIE` 读取，仓库里只有占位说明；
- **失败重试**：单页请求失败按 2s、4s 退避重试，页间随机休眠 2–3.5s，降低风控概率；
- **三步解耦**：爬虫只负责抓、清洗只负责算、可视化只负责画，可单独运行、单独替换；
- **一键流水线**：`run_all.py` 串起三步，支持 `--skip-crawl`、`--append`、`--pages` 等参数；
- **健壮性**：缺文件、缺字段、空数据、Cookie 失效都会给出明确提示，而不是抛一堆堆栈；
- **图表可复现**：固定配色与字体探测逻辑，无界面后端（Agg）在服务器 / CI 上也能出图；
- **统计摘要**：`clean_summary.json` 汇总记录数、字数分位数、分类分布、作者榜，方便直接引用。

## 常见问题

**Q：运行爬虫提示「没有返回数据」或 401 / 403？**
Cookie 过期了，重新按上面的步骤复制一份；另外确认请求的是移动端接口 `m.qidian.com`。

**Q：图表里的中文变成方块？**
系统缺少中文字体。Windows 一般自带微软雅黑；Linux 可安装 `fonts-noto-cjk`，macOS 自带苹方。

**Q：`matplotlib` 报 `boxplot() got an unexpected keyword argument 'labels'`？**
这是旧版本脚本在新版 matplotlib（≥ 3.11）下的问题，当前代码已改用 `set_xticklabels`，升级到本版本即可。

**Q：`ModuleNotFoundError: No module named 'pandas'`？**
没有安装依赖或没激活虚拟环境，先执行 `pip install -r requirements.txt`。

**Q：翻页翻到后面没有数据了？**
榜单页数有限，接口返回空时爬虫会自动停止，属于正常现象。

## 数据说明

- 仓库内的 `qidian_readindex_books.csv` 是某次采集的 **60 条快照**，仅用于演示与复现；
- 重新采集会覆盖该文件，图表与 `clean_summary.json` 也会随之更新；
- 数据版权归起点中文网及原作者所有，本项目仅用于学习与技术交流。
