# -*- coding: utf-8 -*-
"""巨潮资讯网数据源（主源）：证监会指定披露平台，数据权威、结构化。

接口：POST http://www.cninfo.com.cn/new/hisAnnouncement/query
关键参数：column=sse（上交所）、searchkey=600519、tabName=fulltext
"""

import datetime as dt
from typing import List, Dict

import config
from .base import BaseCrawler, polite_sleep


class CninfoCrawler(BaseCrawler):
    name = "cninfo"

    def fetch(self) -> List[Dict]:
        # 先访问首页拿 Cookie，否则查询接口可能返回空
        try:
            self.session.get("http://www.cninfo.com.cn/new/index", timeout=config.REQUEST_TIMEOUT)
        except Exception:  # noqa: BLE001 - 首页拿 Cookie 失败不致命
            pass

        headers = {"Referer": config.CNINFO_REFERER, "X-Requested-With": "XMLHttpRequest"}
        collected: List[Dict] = []
        seen = set()

        for page in range(1, config.MAX_PAGES + 1):
            payload = {
                "pageNum": page,
                "pageSize": config.PAGE_SIZE,
                "column": "sse",
                "tabName": "fulltext",
                "searchkey": config.STOCK_CODE,
                "secid": "",
                "plate": "",
                "category": "",
                "trade": "",
                "seDate": f"{config.DATE_FROM}~{config.DATE_TO}",
                "sortName": "",
                "sortType": "",
                "isHLtitle": "true",
            }
            resp = self.post(config.CNINFO_QUERY_URL, headers=headers, data=payload)
            data = resp.json()
            anns = data.get("announcements") or []

            if page == 1:
                total = data.get("totalRecordNum", 0)
                self.logger(f"    巨潮返回 totalRecordNum={total}，开始分页抓取...")

            if not anns:
                break

            for a in anns:
                item = self._parse(a)
                if not item:
                    continue
                key = (item["title"], item["publish_date"])
                if key in seen:
                    continue
                seen.add(key)
                collected.append(item)

            self.logger(f"    第 {page} 页解析 {len(anns)} 条，累计 {len(collected)} 条")

            if len(anns) < config.PAGE_SIZE:
                break
            polite_sleep()

        return collected

    def _parse(self, a: Dict):
        title = (a.get("announcementTitle") or "").strip()
        if not title:
            return None

        ts = a.get("announcementTime")
        if ts:
            date = dt.datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d")
        else:
            return None

        adjunct = a.get("adjunctUrl") or ""
        url = config.CNINFO_STATIC_PREFIX + adjunct if adjunct else ""

        return self.normalize({
            "title": title,
            "publish_date": date,
            "doc_type": a.get("adjunctType") or "PDF",
            "url": url,
            "stock_code": a.get("secCode") or config.STOCK_CODE,
            "stock_name": a.get("secName") or config.STOCK_NAME,
        })
