# 基金数据爬取（独立子项目）

从天天基金（东方财富）抓取 **全量基金列表** 与 **基金历史净值**，清洗后输出 CSV / SQLite，
并附带一套完全离线的单元测试。原仓库 `qsxj/python-demo` 中的 `fund/` 子项目，已单独拆出。

## 环境

- Python 3.9+（实测 3.12 / 3.13）
- 运行只需 `requests`；跑测试再加 `pytest`

```bash
pip install -r requirements.txt
```

## 快速开始

```bash
python -m fund debug          # 1. 自检：联网 / 编码 / 缓存 / 数据库
python -m fund list           # 2. 抓全量基金列表（约 2.8 万只）
python -m fund nav 000001     # 3. 抓指定基金的历史净值
python -m fund sync           # 4. 列表 + 默认几只基金，一条龙
python -m fund stats          # 5. 看库里现在有什么
python -m fund clean          # 清空缓存
```

常用参数：`--refresh` 忽略缓存重下，`--no-cache` 完全不落盘，
`nav --pages N` 限制翻页数（每页 20 条）。

## 目录

```
基金/
├── fund/                  # 包：config / client / eastmoney / encoding / models / store / cli
├── data/fund/             # 样例数据（fund_list_sample.csv、fund_nav_sample.csv）
├── tests/                 # 32 个离线单元测试（编码、解析、存储）
├── docs/基金数据爬取.md     # 完整设计说明：数据源、字段口径、编码坑、测试
├── conftest.py            # 让 tests/ 能直接 import fund
└── requirements.txt
```

## 测试

```bash
python -m pytest -q
```

## 说明

- 数据源：`fund.eastmoney.com`（基金列表 JS，带 BOM）与 `api.fund.eastmoney.com`（净值 JSON，需 Referer）。
- `data/fund/` 里的两个 CSV 是抓取结果样例，方便离线查看字段格式；真实抓取会生成
  `fund_list.csv` / `fund_nav.csv` / `fund.db`（已在 `.gitignore` 中忽略）。
- 更完整的字段说明、编码问题与设计取舍见 [docs/基金数据爬取.md](docs/基金数据爬取.md)。

> 代码来自 gitee 仓库 `qsxj/python-demo` 的 `fund/` 子项目，本次仅做拆分整理，未改业务逻辑。
