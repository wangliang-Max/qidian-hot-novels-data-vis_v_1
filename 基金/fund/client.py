# -*- coding: utf-8 -*-
"""HTTP 客户端：重试、限速、缓存、编码解码，都在这里收口。

要点
----
* 每次请求之间 ``sleep`` 一小会儿，别把对方服务器打挂。
* 超时/5xx/连接错误按指数退避重试；4xx 直接失败（重试也没用）。
* 原始字节落盘到 ``cache/fund/``，调试时可以直接对着缓存文件复现，
  不用反复联网。``--refresh`` 或删除 cache 目录即可强制重下。
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import requests

from fund import config
from fund.encoding import decode_bytes


class FetchError(RuntimeError):
    """抓取失败（重试用尽或遇到不可重试的状态码）。"""


class Client:
    """带重试和文件缓存的极简客户端。"""

    def __init__(self, delay: float | None = None, max_retry: int | None = None,
                 timeout: int | None = None, use_cache: bool = True):
        self.delay = config.REQUEST_DELAY if delay is None else delay
        self.max_retry = config.MAX_RETRY if max_retry is None else max_retry
        self.timeout = config.REQUEST_TIMEOUT if timeout is None else timeout
        self.use_cache = use_cache
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": config.USER_AGENT,
            "Referer": config.REFERER,     # 净值接口不带 Referer 会返回空列表
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9",
        })
        self._last_request_at = 0.0

    # ------------------------------------------------------------------ #
    # 底层
    # ------------------------------------------------------------------ #
    def _throttle(self) -> None:
        gap = time.monotonic() - self._last_request_at
        if gap < self.delay:
            time.sleep(self.delay - gap)
        self._last_request_at = time.monotonic()

    def get_bytes(self, url: str, params: dict | None = None,
                  cache_key: str | None = None) -> bytes:
        """GET 一个 URL，返回原始字节；命中缓存时直接读盘。"""
        if self.use_cache and cache_key:
            cached = config.CACHE_DIR / cache_key
            if cached.exists() and cached.stat().st_size > 0:
                return cached.read_bytes()

        last_error: Exception | None = None
        for attempt in range(self.max_retry + 1):
            try:
                self._throttle()
                resp = self.session.get(url, params=params, timeout=self.timeout)
            except requests.RequestException as exc:
                last_error = exc
            else:
                if resp.status_code < 400:
                    data = resp.content
                    if self.use_cache and cache_key:
                        config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
                        (config.CACHE_DIR / cache_key).write_bytes(data)
                    return data
                if 400 <= resp.status_code < 500:
                    # 客户端错误，重试无意义
                    raise FetchError("HTTP %d：%s" % (resp.status_code, url))
                last_error = FetchError("HTTP %d：%s" % (resp.status_code, url))

            if attempt < self.max_retry:
                backoff = 2 ** attempt * 0.5      # 0.5s, 1s, 2s, 4s
                time.sleep(backoff)

        raise FetchError("重试 %d 次仍失败：%s（%s）"
                         % (self.max_retry, url, last_error))

    def get_text(self, url: str, params: dict | None = None,
                 cache_key: str | None = None) -> tuple[str, str]:
        """返回 ``(文本, 编码名)``，编码由 :func:`decode_bytes` 自动判断。"""
        return decode_bytes(self.get_bytes(url, params=params, cache_key=cache_key))

    def get_json(self, url: str, params: dict | None = None,
                 cache_key: str | None = None) -> dict:
        """取 JSON。

        注意：响应头没写 charset 时 ``requests`` 会猜成 ISO-8859-1，
        所以这里一定先拿字节、自己按 UTF-8 解码，再 ``json.loads``。
        """
        raw = self.get_bytes(url, params=params, cache_key=cache_key)
        text, used = decode_bytes(raw)
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise FetchError("JSON 解析失败（编码 %s）：%s" % (used, exc)) from exc

    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> "Client":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()


def clear_cache() -> int:
    """删除缓存目录，返回删掉的文件数。"""
    if not config.CACHE_DIR.exists():
        return 0
    count = 0
    for path in config.CACHE_DIR.rglob("*"):
        if path.is_file():
            path.unlink()
            count += 1
    return count
