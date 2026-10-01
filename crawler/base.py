# -*- coding: utf-8 -*-
"""爬虫基类与公共工具函数。"""

import random
import re
import time
from typing import List, Dict

import requests

import config

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def strip_html_tags(text: str) -> str:
    """去掉 HTML 标签与高亮 <em>，并压缩空白字符。"""
    if not text:
        return ""
    return _WS_RE.sub(" ", _TAG_RE.sub("", str(text))).strip()


def build_session() -> requests.Session:
    """构造带完整请求头的会话。"""
    s = requests.Session()
    s.headers.update(config.REQUEST_HEADERS)
    return s


def polite_sleep() -> None:
    """请求间隔随机休眠，降低被风控的概率。"""
    time.sleep(random.uniform(*config.REQUEST_DELAY))


class BaseCrawler:
    """所有数据源爬虫的基类。

    子类只需实现 fetch()，返回标准化的公告字典列表：
        {
            "title": str,        # 公告标题
            "publish_date": str, # 发布日期 YYYY-MM-DD
            "category": str,     # 公告分类（可留空，交由清洗阶段补全）
            "doc_type": str,     # 附件类型 PDF/DOC/HTML
            "url": str,          # 附件或详情页地址
            "source": str,       # 数据源标识
            "stock_code": str,
            "stock_name": str,
        }
    """

    name = "base"

    def __init__(self, session: requests.Session = None, logger=print):
        self.session = session or build_session()
        self.logger = logger

    # ------------------------------------------------------------ 网络工具
    def get(self, url: str, **kwargs) -> requests.Response:
        """带重试的 GET。"""
        return self._request("GET", url, **kwargs)

    def post(self, url: str, **kwargs) -> requests.Response:
        """带重试的 POST。"""
        return self._request("POST", url, **kwargs)

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        kwargs.setdefault("timeout", config.REQUEST_TIMEOUT)
        last_err = None
        for i in range(1, config.REQUEST_RETRY + 1):
            try:
                resp = self.session.request(method, url, **kwargs)
                resp.raise_for_status()
                return resp
            except Exception as exc:  # noqa: BLE001 - 统一兜底重试
                last_err = exc
                self.logger(f"    [重试 {i}/{config.REQUEST_RETRY}] {url} -> {exc}")
                time.sleep(1.2 * i)
        raise RuntimeError(f"请求失败: {url} ({last_err})")

    # ------------------------------------------------------------ 标准化
    def normalize(self, item: Dict) -> Dict:
        """补齐公共字段，保证各数据源字段一致。"""
        item.setdefault("stock_code", config.STOCK_CODE)
        item.setdefault("stock_name", config.STOCK_NAME)
        item.setdefault("doc_type", "")
        item.setdefault("category", "")
        item.setdefault("source", self.name)
        item["title"] = strip_html_tags(item.get("title", ""))
        return item

    def fetch(self) -> List[Dict]:
        raise NotImplementedError
