# -*- coding: utf-8 -*-
"""数据清洗模块：用 Pandas 把原始抓取结果规整为可直接入库/分析的结构化表格。

清洗流水线：
    1. 构建 DataFrame 并统一列名
    2. 文本清洗：去 HTML 标签、压缩空白、剔除空标题（覆盖 title/stock_name/stock_code）
    3. 日期清洗：统一为 datetime，剔除非法/未来日期
    4. 去重：按 (标题, 日期) 组合去重
    5. 分类：依据标题关键词打业务标签
    6. 派生字段：年月、季度、星期、标题长度
"""

import datetime as dt
from typing import List, Dict, Tuple

import pandas as pd

import config

# 最终输出的列顺序（同时约束入库字段）
COLUMNS = [
    "stock_code", "stock_name", "title", "category",
    "publish_date", "year", "month", "quarter", "weekday",
    "doc_type", "title_length", "url", "source",
]


def classify(title: str) -> str:
    """按标题关键词归类公告类型，命中第一条规则即返回。"""
    for category, keywords in config.CATEGORY_RULES:
        for kw in keywords:
            if kw in title:
                return category
    return config.DEFAULT_CATEGORY


def build_dataframe(items: List[Dict]) -> pd.DataFrame:
    """原始字典列表 -> 初步 DataFrame。"""
    df = pd.DataFrame(items)
    if df.empty:
        return pd.DataFrame(columns=COLUMNS)

    for col in ("stock_code", "stock_name", "title", "category",
                "publish_date", "doc_type", "url", "source"):
        if col not in df.columns:
            df[col] = ""
    return df


def clean(items: List[Dict], logger=print) -> Tuple[pd.DataFrame, Dict]:
    """执行完整清洗流程。

    Returns:
        (清洗后的 DataFrame, 清洗统计字典)
    """
    stats: Dict = {"raw": len(items)}
    df = build_dataframe(items)

    if df.empty:
        stats.update({"cleaned": 0, "removed": len(items)})
        logger("  清洗结果：0 条（原始数据为空）")
        return pd.DataFrame(columns=COLUMNS), stats

    # ---------- 1. 文本清洗 ----------
    # 巨潮等接口会在标题与 secName 中插入 <em> 高亮标签，
    # 这里统一剥离，保证所有文本列输出干净，不依赖上游爬虫是否已处理。
    for col in ("title", "stock_name", "stock_code"):
        df[col] = (
            df[col].astype(str)
            .str.replace(r"<[^>]+>", "", regex=True)     # 去 HTML 标签
            .str.replace(r"\s+", " ", regex=True)        # 压缩空白
            .str.replace(r"[　\xa0]", " ", regex=True)   # 去全角/不间断空格
            .str.strip()
        )
    before = len(df)
    df = df[df["title"].str.len() >= 4]              # 剔除空标题/噪声
    stats["drop_empty_title"] = before - len(df)

    # ---------- 2. 日期清洗 ----------
    df["publish_date"] = pd.to_datetime(df["publish_date"], errors="coerce")
    before = len(df)
    df = df[df["publish_date"].notna()]
    stats["drop_bad_date"] = before - len(df)

    today = pd.Timestamp(dt.date.today())
    before = len(df)
    df = df[df["publish_date"] <= today]             # 剔除未来日期
    stats["drop_future_date"] = before - len(df)

    # ---------- 3. 去重 ----------
    before = len(df)
    df = df.drop_duplicates(subset=["title", "publish_date"], keep="first")
    stats["drop_duplicate"] = before - len(df)

    # ---------- 4. 分类 ----------
    df["category"] = df["title"].map(classify)

    # ---------- 5. 派生字段 ----------
    df["year"] = df["publish_date"].dt.year.astype(int)
    df["month"] = df["publish_date"].dt.month.astype(int)
    df["quarter"] = df["publish_date"].dt.quarter.astype(int)
    df["weekday"] = df["publish_date"].dt.weekday.astype(int)
    df["title_length"] = df["title"].str.len().astype(int)

    # ---------- 6. 排序 & 收尾 ----------
    df = df.sort_values("publish_date", ascending=False).reset_index(drop=True)
    df["publish_date"] = df["publish_date"].dt.strftime("%Y-%m-%d")
    df = df.reindex(columns=COLUMNS).fillna("")
    # 统一标量类型，避免入库时把 numpy int 传给 sqlite
    for col in ("year", "month", "quarter", "weekday", "title_length"):
        df[col] = df[col].astype(int)

    stats["cleaned"] = len(df)
    stats["removed"] = stats["raw"] - len(df)

    logger(
        f"  清洗完成：原始 {stats['raw']} 条 → 有效 {stats['cleaned']} 条 "
        f"(空标题 -{stats['drop_empty_title']}，非法日期 -{stats['drop_bad_date']}，"
        f"未来日期 -{stats['drop_future_date']}，重复 -{stats['drop_duplicate']})"
    )
    return df, stats
