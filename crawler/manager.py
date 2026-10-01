# -*- coding: utf-8 -*-
"""数据源调度：按优先级依次尝试，任一源成功即返回，实现自动降级。"""

from typing import List, Dict

import config
from .base import build_session
from .cninfo import CninfoCrawler
from .sina import SinaCrawler
from .mock import MockCrawler

_REGISTRY = {
    "cninfo": CninfoCrawler,
    "sina": SinaCrawler,
    "mock": MockCrawler,
}


def crawl(sources=None, logger=print) -> List[Dict]:
    """按 config.DATA_SOURCES 顺序尝试抓取，返回第一个非空结果。"""
    sources = sources or config.DATA_SOURCES
    session = build_session()

    for name in sources:
        cls = _REGISTRY.get(name)
        if cls is None:
            logger(f"  ! 未知数据源: {name}，跳过")
            continue
        logger(f"  > 尝试数据源 [{name}] ...")
        try:
            items = cls(session=session, logger=logger).fetch()
        except Exception as exc:  # noqa: BLE001 - 记录后降级
            logger(f"  ! 数据源 [{name}] 失败: {exc}")
            continue

        if items:
            logger(f"  * 数据源 [{name}] 成功，共 {len(items)} 条")
            return items

        logger(f"  ! 数据源 [{name}] 返回空，尝试下一个")

    logger("  ! 所有数据源均失败")
    return []
