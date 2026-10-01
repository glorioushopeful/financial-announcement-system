# -*- coding: utf-8 -*-
"""新浪财经数据源（备用源）：主源不可用时降级使用，页面为 GBK 编码。

页面结构为 div.datelist > ul > {日期文本, <a>标题</a>, <br/>}，
日期位于 <a> 之前的文本节点中，需逐个回溯提取。
"""

import re
from typing import List, Dict

from bs4 import BeautifulSoup

import config
from .base import BaseCrawler

_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


class SinaCrawler(BaseCrawler):
    name = "sina"

    def fetch(self) -> List[Dict]:
        url = config.SINA_ANNOUNCE_URL.format(code=config.STOCK_CODE)
        resp = self.get(url)
        # 新浪页面为 GBK，显式指定避免乱码
        resp.encoding = "gbk"
        soup = BeautifulSoup(resp.text, "lxml")

        box = soup.find("div", class_="datelist") or soup.find("ul", class_="datelist")
        if box is None:
            self.logger("    未找到 datelist 容器")
            return []

        collected: List[Dict] = []
        for a in box.find_all("a"):
            text = a.get_text(" ", strip=True)
            if len(text) < 6:
                continue
            # 资讯流里混有大量无关条目，只保留与标的相关的
            if not any(kw in text for kw in config.STOCK_KEYWORDS):
                continue

            # 从 <a> 之前的文本节点回溯日期
            date = ""
            node = a.previous_sibling
            for _ in range(4):
                if node is None:
                    break
                m = _DATE_RE.search(str(node))
                if m:
                    date = m.group(1)
                    break
                node = node.previous_sibling

            if not date:
                m = _DATE_RE.search(text)
                date = m.group(1) if m else ""

            href = (a.get("href") or "").strip()
            if href.startswith("//"):
                href = "https:" + href

            collected.append(self.normalize({
                "title": text,
                "publish_date": date,
                "doc_type": "HTML",
                "url": href,
            }))

        self.logger(f"    新浪解析 {len(collected)} 条")
        return collected
