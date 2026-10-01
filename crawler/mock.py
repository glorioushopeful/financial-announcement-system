# -*- coding: utf-8 -*-
"""本地兜底数据源：网络不可用时使用，生成贴近真实分布的贵州茅台公告样例。

生成的数据完全离线，但保留了真实公告的「类型分布」与「时间分布」特征，
用于保证「采集 → 清洗 → 存储 → 接口 → 大屏」整条链路随时可演示。
"""

import datetime as dt
import random
from typing import List, Dict

import config
from .base import BaseCrawler

# 定期报告：按固定节奏出现
_PERIODIC = [
    # (月份, 日, 标题模板)
    (3, 31, "{name}{year}年年度报告"),
    (4, 28, "{name}{year}年第一季度报告"),
    (8, 30, "{name}{year}年半年度报告"),
    (10, 28, "{name}{year}年第三季度报告"),
]

# 不定期公告：随机抽取
_EVENTS = [
    "{name}关于利润分配方案的公告",
    "{name}关于召开{year}年年度股东大会的通知",
    "{name}{year}年年度权益分派实施公告",
    "{name}关于回购股份进展的公告",
    "{name}关于独立董事辞职的公告",
    "{name}关于聘任高级管理人员的公告",
    "{name}关于控股股东增持公司股份的公告",
    "{name}关于修订公司章程的公告",
    "{name}关于日常关联交易的公告",
    "{name}股票交易异常波动公告",
    "{name}关于收到监管问询函的公告",
    "{name}关于对外投资的公告",
    "{name}关于董事会决议的公告",
    "{name}关于监事会决议的公告",
    "{name}关于使用闲置资金进行现金管理的公告",
    "{name}关于会计政策变更的公告",
    "{name}关于预计{year}年度日常关联交易的公告",
]


class MockCrawler(BaseCrawler):
    name = "mock"

    def __init__(self, session=None, logger=print, count: int = 120, seed: int = 20240101):
        super().__init__(session=session, logger=logger)
        self.count = count
        self.seed = seed

    def fetch(self) -> List[Dict]:
        random.seed(self.seed)
        name = config.STOCK_NAME
        y0 = int(config.DATE_FROM[:4])
        y1 = int(config.DATE_TO[:4])
        today = dt.date.today()

        items: List[Dict] = []

        # 1) 定期报告：每个财年 4 份
        for year in range(y0, y1 + 1):
            for month, day, tpl in _PERIODIC:
                try:
                    d = dt.date(year, month, day)
                except ValueError:
                    continue
                if not (dt.date(y0, 1, 1) <= d <= min(dt.date(y1, 12, 31), today)):
                    continue
                items.append(self.normalize({
                    "title": tpl.format(name=name, year=year),
                    "publish_date": d.isoformat(),
                    "doc_type": "PDF",
                    "url": "",
                }))

        # 2) 不定期公告：在窗口内随机撒点，补足数量
        start = dt.date(y0, 1, 1)
        end = min(dt.date(y1, 12, 31), today)
        span = (end - start).days
        need = max(0, self.count - len(items))
        for _ in range(need):
            d = start + dt.timedelta(days=random.randint(0, span))
            # 周末顺延到周一，贴近真实披露节奏
            if d.weekday() >= 5:
                d += dt.timedelta(days=7 - d.weekday())
            if d > end:
                d = end
            tpl = random.choice(_EVENTS)
            items.append(self.normalize({
                "title": tpl.format(name=name, year=d.year),
                "publish_date": d.isoformat(),
                "doc_type": "PDF",
                "url": "",
            }))

        items.sort(key=lambda x: x["publish_date"], reverse=True)
        self.logger(f"    本地样例生成 {len(items)} 条（离线兜底）")
        return items
