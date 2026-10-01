# -*- coding: utf-8 -*-
"""Flask 服务：对外提供公告数据 API，并托管 ECharts 可视化大屏。"""

import os
import threading
import datetime as dt

from flask import Flask, jsonify, request, send_file, render_template

import config
import pipeline
from storage import database as db

app = Flask(__name__, template_folder=config.WEB_DIR,
            static_folder=config.WEB_DIR, static_url_path="/static")
# 保证中文不被转义为 \uXXXX
app.json.ensure_ascii = False

# 刷新任务状态（避免并发重复触发）
_refresh_lock = threading.Lock()
_refresh_state = {"running": False, "last_result": None, "log": []}


def _ok(data, **extra):
    payload = {"code": 0, "msg": "success", "data": data}
    payload.update(extra)
    return jsonify(payload)


def _fail(msg, code=1):
    return jsonify({"code": code, "msg": msg, "data": None}), 400


# ================================================================= 页面
@app.route("/")
def index():
    return render_template("index.html")


# ================================================================= 数据接口
@app.route("/api/overview")
def api_overview():
    """总览：总量、分类数、覆盖时间、来源分布。"""
    total = db.count_all()
    start, end = db.min_max_date()
    categories = db.group_count("category")
    sources = db.group_count("source")

    days = 0
    if start and end:
        try:
            days = (dt.date.fromisoformat(end) - dt.date.fromisoformat(start)).days + 1
        except ValueError:
            days = 0

    return _ok({
        "stock_name": config.STOCK_NAME,
        "stock_code": config.STOCK_CODE,
        "total": total,
        "category_count": len(categories),
        "date_start": start,
        "date_end": end,
        "span_days": days,
        "sources": sources,
        "updated_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })


@app.route("/api/category")
def api_category():
    """公告分类分布（饼图）。"""
    return _ok(db.group_count("category"))


@app.route("/api/trend")
def api_trend():
    """月度公告数量趋势（折线图）。"""
    return _ok(db.trend_by_month())


@app.route("/api/year")
def api_year():
    """年度公告数量（柱状图）。"""
    rows = db.group_count("year")
    rows.sort(key=lambda x: x["name"])
    return _ok(rows)


@app.route("/api/quarter")
def api_quarter():
    """季度分布（柱状图）。"""
    rows = db.group_count("quarter")
    rows.sort(key=lambda x: x["name"])
    return _ok(rows)


@app.route("/api/weekday")
def api_weekday():
    """星期分布（雷达图）。"""
    names = {0: "周一", 1: "周二", 2: "周三", 3: "周四", 4: "周五", 5: "周六", 6: "周日"}
    rows = db.group_count("weekday")
    filled = {names[i]: 0 for i in range(7)}
    for r in rows:
        key = names.get(r["name"], str(r["name"]))
        filled[key] = r["value"]
    return _ok([{"name": k, "value": v} for k, v in filled.items()])


@app.route("/api/recent")
def api_recent():
    """最新公告列表（滚动播报）。"""
    limit = request.args.get("limit", 12, type=int)
    limit = max(1, min(limit, 100))
    return _ok(db.recent(limit))


@app.route("/api/list")
def api_list():
    """公告分页查询，支持分类与关键词过滤。"""
    page = max(1, request.args.get("page", 1, type=int))
    size = max(1, min(request.args.get("size", 20, type=int), 200))
    category = request.args.get("category", "").strip()
    keyword = request.args.get("keyword", "").strip()

    where, args = [], []
    if category:
        where.append("category = ?")
        args.append(category)
    if keyword:
        where.append("title LIKE ?")
        args.append(f"%{keyword}%")
    sql_where = (" WHERE " + " AND ".join(where)) if where else ""

    with db.connect() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) FROM announcements{sql_where}", args
        ).fetchone()[0]
        cur = conn.execute(
            f"SELECT title, category, publish_date, doc_type, url, source "
            f"FROM announcements{sql_where} "
            f"ORDER BY publish_date DESC, id DESC LIMIT ? OFFSET ?",
            args + [size, (page - 1) * size],
        )
        rows = [dict(r) for r in cur.fetchall()]

    return _ok(rows, total=total, page=page, size=size,
               pages=(total + size - 1) // size)


# ================================================================= 运维接口
@app.route("/api/refresh", methods=["POST", "GET"])
def api_refresh():
    """重新触发一次「采集 → 清洗 → 导出 → 入库」流水线。"""
    if _refresh_state["running"]:
        return _fail("采集任务正在运行中，请稍后再试", code=2)

    sources = request.args.get("sources") or (request.json or {}).get("sources")

    def _job():
        log_lines = []

        def logger(msg):
            log_lines.append(str(msg))
            print(msg, flush=True)

        try:
            res = pipeline.run(
                sources=sources.split(",") if sources else None,
                logger=logger,
            )
        except Exception as exc:  # noqa: BLE001
            res = {"ok": False, "error": str(exc)}
            logger(f"流水线异常: {exc}")
        _refresh_state["last_result"] = res
        _refresh_state["log"] = log_lines
        _refresh_state["running"] = False

    with _refresh_lock:
        _refresh_state["running"] = True
    threading.Thread(target=_job, daemon=True).start()

    return _ok({"started": True}, msg="采集任务已启动，请轮询 /api/refresh/status 查看进度")


@app.route("/api/refresh/status")
def api_refresh_status():
    """查询采集任务状态。"""
    return _ok({
        "running": _refresh_state["running"],
        "result": _refresh_state["last_result"],
        "log": _refresh_state["log"][-30:],
    })


@app.route("/api/download")
def api_download():
    """下载 CSV / Excel 数据文件。"""
    fmt = request.args.get("format", "csv").lower()
    path = config.EXCEL_PATH if fmt == "xlsx" else config.CSV_PATH
    if not os.path.exists(path):
        return _fail("数据文件不存在，请先执行采集")
    mime = ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            if fmt == "xlsx" else "text/csv")
    return send_file(path, as_attachment=True,
                     download_name=os.path.basename(path), mimetype=mime)


@app.errorhandler(404)
def not_found(_e):
    return jsonify({"code": 404, "msg": "接口不存在", "data": None}), 404


if __name__ == "__main__":
    db.init_db()
    print(f" * 服务地址: http://{config.HOST}:{config.PORT}")
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
