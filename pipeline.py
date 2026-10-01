# -*- coding: utf-8 -*-
"""流水线编排：采集 → 清洗 → 导出 → 入库，一步跑通完整闭环。"""

import time
from typing import Dict

import pandas as pd

from crawler import crawl
from cleaner import clean
from exporter import export
from storage import database as db
import config


def run(sources=None, do_export=True, logger=print) -> Dict:
    """执行完整数据流水线。

    Args:
        sources: 指定数据源顺序，默认取 config.DATA_SOURCES
        do_export: 是否导出 Excel/CSV
        logger: 日志函数（Flask 中可传入重定向到前端的回调）

    Returns:
        包含统计信息的字典
    """
    t0 = time.time()
    result: Dict = {"ok": False}

    # ---------------- 1. 采集 ----------------
    logger("[1/4] 开始采集公告数据...")
    items = crawl(sources=sources, logger=logger)
    result["raw_count"] = len(items)
    if not items:
        logger("采集失败：未获得任何数据")
        return result

    # ---------------- 2. 清洗 ----------------
    logger("[2/4] 开始清洗数据...")
    df, stats = clean(items, logger=logger)
    result.update(stats)
    if df.empty:
        logger("清洗失败：无有效数据")
        return result

    # ---------------- 3. 导出 ----------------
    if do_export:
        logger("[3/4] 导出 Excel / CSV...")
        csv_path, xlsx_path = export(df, logger=logger)
        result["csv_path"] = csv_path
        result["excel_path"] = xlsx_path
    else:
        logger("[3/4] 跳过导出")

    # ---------------- 4. 入库 ----------------
    logger("[4/4] 写入 SQLite...")
    db.init_db()
    inserted, updated = db.save_dataframe(df)
    result["inserted"] = inserted
    result["updated"] = updated
    result["total"] = db.count_all()
    logger(f"  入库完成：新增 {inserted} 条，更新 {updated} 条，库内共 {result['total']} 条")

    result["seconds"] = round(time.time() - t0, 2)
    result["ok"] = True
    logger(f"流水线完成，耗时 {result['seconds']} 秒")
    return result


def load_from_disk() -> pd.DataFrame:
    """从已存在的 CSV 读回数据（网络不可用时的替代入口）。"""
    import os
    if not os.path.exists(config.CSV_PATH):
        return pd.DataFrame()
    return pd.read_csv(config.CSV_PATH, encoding="utf-8-sig")
