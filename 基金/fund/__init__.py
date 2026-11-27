# -*- coding: utf-8 -*-
"""基金数据爬取（天天基金）。

模块划分::

    config.py     数据源地址、抓取参数、输出路径、字段顺序
    encoding.py   编码探测 / BOM / 乱码判定 / 名称归一化
    client.py     HTTP 客户端：限速、重试、缓存
    eastmoney.py  解析基金列表 JS、历史净值 JSON
    models.py     Fund / NavPoint / FetchStats
    store.py      CSV（utf-8-sig）+ SQLite
    cli.py        命令行

快速开始::

    python -m fund debug       # 先自检
    python -m fund list        # 抓全量列表
    python -m fund nav 000001  # 抓一只基金的净值
"""

__version__ = "1.0.0"

__all__ = ["__version__"]
