# -*- coding: utf-8 -*-
"""爬虫包：每个数据源一个模块，对外统一暴露 fetch() -> List[dict]。"""

from .base import BaseCrawler, build_session, polite_sleep, strip_html_tags
from .cninfo import CninfoCrawler
from .sina import SinaCrawler
from .mock import MockCrawler
from .manager import crawl

__all__ = [
    "BaseCrawler",
    "build_session",
    "polite_sleep",
    "strip_html_tags",
    "CninfoCrawler",
    "SinaCrawler",
    "MockCrawler",
    "crawl",
]
