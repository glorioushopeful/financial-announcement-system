# -*- coding: utf-8 -*-
"""SQLite 读写封装。

表 announcements 以 (title, publish_date) 作为业务唯一键，
重复入库时执行 UPSERT，保证多次跑流水线不会产生重复数据。
"""

import sqlite3
from typing import List, Dict, Tuple

import pandas as pd

import config
from cleaner import COLUMNS

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS announcements (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code    TEXT NOT NULL,
    stock_name    TEXT NOT NULL,
    title         TEXT NOT NULL,
    category      TEXT NOT NULL,
    publish_date  TEXT NOT NULL,
    year          INTEGER,
    month         INTEGER,
    quarter       INTEGER,
    weekday       INTEGER,
    doc_type      TEXT,
    title_length  INTEGER,
    url           TEXT,
    source        TEXT,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(title, publish_date)
);
"""

_INDEX_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_ann_date ON announcements(publish_date);",
    "CREATE INDEX IF NOT EXISTS idx_ann_category ON announcements(category);",
    "CREATE INDEX IF NOT EXISTS idx_ann_year ON announcements(year);",
]


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """建表与索引。"""
    with connect() as conn:
        conn.execute(_CREATE_SQL)
        for sql in _INDEX_SQL:
            conn.execute(sql)
        conn.commit()


def save_dataframe(df: pd.DataFrame) -> Tuple[int, int]:
    """把清洗后的 DataFrame 写入数据库（UPSERT）。

    Returns:
        (插入条数, 更新条数)
    """
    init_db()
    if df.empty:
        return 0, 0

    cols = [c for c in COLUMNS if c in df.columns]
    holders = ", ".join(["?"] * len(cols))
    updates = ", ".join(f"{c}=excluded.{c}" for c in cols if c not in ("title", "publish_date"))
    sql = (
        f"INSERT INTO announcements ({', '.join(cols)}) VALUES ({holders}) "
        f"ON CONFLICT(title, publish_date) DO UPDATE SET {updates}"
    )

    rows = [
        tuple(int(r[c]) if c in ("year", "month", "quarter", "weekday", "title_length") else r[c]
              for c in cols)
        for _, r in df.iterrows()
    ]

    inserted = updated = 0
    with connect() as conn:
        # 逐条执行以便区分 insert / update（changes() 为 1 表示插入或更新）
        for row in rows:
            before = _exists(conn, row[cols.index("title")], row[cols.index("publish_date")])
            conn.execute(sql, row)
            if before:
                updated += 1
            else:
                inserted += 1
        conn.commit()
    return inserted, updated


def _exists(conn: sqlite3.Connection, title: str, date: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM announcements WHERE title=? AND publish_date=? LIMIT 1", (title, date)
    )
    return cur.fetchone() is not None


def fetch_all(limit: int = 1000) -> List[Dict]:
    """按日期倒序取出公告。"""
    with connect() as conn:
        cur = conn.execute(
            "SELECT * FROM announcements ORDER BY publish_date DESC, id DESC LIMIT ?", (limit,)
        )
        return [dict(r) for r in cur.fetchall()]


def count_all() -> int:
    with connect() as conn:
        return conn.execute("SELECT COUNT(*) FROM announcements").fetchone()[0]


def group_count(field: str, limit: int = 50) -> List[Dict]:
    """按字段分组计数，例如 category / year / quarter / weekday。"""
    if field not in COLUMNS:
        return []
    with connect() as conn:
        cur = conn.execute(
            f"SELECT {field} AS name, COUNT(*) AS value FROM announcements "
            f"GROUP BY {field} ORDER BY value DESC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in cur.fetchall()]


def trend_by_month() -> List[Dict]:
    """按月统计公告数量（YYYY-MM）。"""
    with connect() as conn:
        cur = conn.execute(
            "SELECT strftime('%Y-%m', publish_date) AS month, COUNT(*) AS value "
            "FROM announcements GROUP BY month ORDER BY month"
        )
        return [dict(r) for r in cur.fetchall()]


def recent(limit: int = 10) -> List[Dict]:
    """最近发布的若干条公告。"""
    with connect() as conn:
        cur = conn.execute(
            "SELECT title, category, publish_date, url, doc_type "
            "FROM announcements ORDER BY publish_date DESC, id DESC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in cur.fetchall()]


def min_max_date() -> Tuple[str, str]:
    """数据覆盖的起止日期。"""
    with connect() as conn:
        row = conn.execute(
            "SELECT MIN(publish_date), MAX(publish_date) FROM announcements"
        ).fetchone()
        return (row[0] or "", row[1] or "")
