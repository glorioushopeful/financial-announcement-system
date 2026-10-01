# -*- coding: utf-8 -*-
"""命令行入口：一键跑通采集 → 清洗 → 导出 → 入库，或直接启动 Web 服务。

用法：
    python run.py              采集数据并启动 Web 服务
    python run.py crawl        仅采集（不启动服务）
    python run.py serve        仅启动服务（用已有数据）
"""

import argparse
import sys

import config
import pipeline
from storage import database as db


def main() -> int:
    parser = argparse.ArgumentParser(description="金融行业公告数据采集与可视化系统")
    parser.add_argument("command", nargs="?", default="all",
                        choices=["all", "crawl", "serve"],
                        help="all=采集并启动服务(默认) / crawl=仅采集 / serve=仅启动服务")
    parser.add_argument("--sources", default=None,
                        help="逗号分隔指定数据源顺序，如 cninfo,sina,mock")
    parser.add_argument("--host", default=config.HOST)
    parser.add_argument("--port", type=int, default=config.PORT)
    args = parser.parse_args()

    print("=" * 60)
    print(f"  {config.STOCK_NAME}({config.STOCK_CODE}) 公告数据采集与可视化系统")
    print("=" * 60)

    if args.command in ("all", "crawl"):
        sources = args.sources.split(",") if args.sources else None
        result = pipeline.run(sources=sources)
        print("-" * 60)
        if not result.get("ok"):
            print("流水线未完成，请检查上方日志")
            return 1
        print(f"原始 {result['raw_count']} 条 → 有效 {result['cleaned']} 条 "
              f"→ 新增 {result['inserted']} / 更新 {result['updated']} 条")

    if args.command in ("all", "serve"):
        db.init_db()
        print("-" * 60)
        print(f" * 大屏地址: http://{args.host}:{args.port}")
        print(" * 按 Ctrl+C 停止服务")
        from app import app as flask_app
        flask_app.run(host=args.host, port=args.port, debug=config.DEBUG)

    return 0


if __name__ == "__main__":
    sys.exit(main())
