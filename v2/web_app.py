import os
import sys
import time
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify, render_template, request
from core.fetcher import Fetcher
from core.storage import HistoryManager
from core.engine import ETFEngine
from core import config

app = Flask(__name__)

WATCHLIST_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "watchlist.txt")

# Watchlist 即時資料的記憶體快取：避免每次重整都同步硬抓 yfinance（10–20 秒）。
# 在 TTL 內重複請求直接回傳上次結果；?refresh=1 可強制重抓。
WATCHLIST_CACHE_TTL = config.WATCHLIST_CACHE_TTL  # 秒
_watchlist_cache = {"data": None, "ts": 0.0}
_cache_lock = threading.Lock()


def read_watchlist():
    engine = ETFEngine(watchlist_file=WATCHLIST_FILE)
    return engine.prepare_tickers(["watchlist"])


def _serialize(data):
    return {
        "ticker": data.ticker,
        "name": data.name,
        "price": round(data.price, 2),
        "currency": data.currency,
        "nav": round(data.nav, 2) if data.nav is not None else None,
        "pd": round(data.premium_discount, 2) if data.premium_discount is not None else None,
        "yield": round(data.tr_annual_yield, 2) if data.tr_annual_yield is not None else None,
        "vol_ratio": round(data.volume_ratio, 2),
        "updated": data.last_updated,
    }


def _fetch_watchlist():
    """併發抓取 watchlist 所有標的並序列化（順序與 watchlist 一致）。"""
    tickers = read_watchlist()
    results = []
    for symbol, outcome in Fetcher.fetch_many(tickers):
        if isinstance(outcome, Exception):
            results.append({"ticker": symbol, "error": str(outcome)})
        else:
            results.append(_serialize(outcome))
    return results


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/watchlist")
def api_watchlist():
    force_refresh = request.args.get("refresh") == "1"
    now = time.time()

    with _cache_lock:
        fresh = (
            _watchlist_cache["data"] is not None
            and (now - _watchlist_cache["ts"]) < WATCHLIST_CACHE_TTL
        )
        if fresh and not force_refresh:
            return jsonify({"cached": True, "items": _watchlist_cache["data"]})

    # 抓取放在鎖外，避免長達十幾秒的網路請求阻塞其他路由
    items = _fetch_watchlist()
    with _cache_lock:
        _watchlist_cache["data"] = items
        _watchlist_cache["ts"] = time.time()
    return jsonify({"cached": False, "items": items})


@app.route("/api/history/<ticker>")
def api_history(ticker):
    records = HistoryManager.get_history(ticker.upper())
    return jsonify(records)


if __name__ == "__main__":
    # debug 預設關閉（見 config.WEB_DEBUG），需要時設環境變數 ETF_WEB_DEBUG=1
    app.run(debug=config.WEB_DEBUG, port=config.WEB_PORT)
