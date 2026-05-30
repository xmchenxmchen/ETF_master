import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify, render_template
from core.fetcher import Fetcher
from core.storage import HistoryManager
from core.engine import ETFEngine

app = Flask(__name__)

WATCHLIST_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "watchlist.txt")


def read_watchlist():
    engine = ETFEngine(watchlist_file=WATCHLIST_FILE)
    return engine.prepare_tickers(["watchlist"])


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/watchlist")
def api_watchlist():
    tickers = read_watchlist()
    results = []
    for symbol in tickers:
        try:
            data = Fetcher(symbol).fetch()
            results.append({
                "ticker": data.ticker,
                "name": data.name,
                "price": round(data.price, 2),
                "currency": data.currency,
                "nav": round(data.nav, 2) if data.nav is not None else None,
                "pd": round(data.premium_discount, 2) if data.premium_discount is not None else None,
                "yield": round(data.tr_annual_yield, 2) if data.tr_annual_yield is not None else None,
                "vol_ratio": round(data.volume_ratio, 2),
                "updated": data.last_updated,
            })
        except Exception as e:
            results.append({"ticker": symbol, "error": str(e)})
    return jsonify(results)


@app.route("/api/history/<ticker>")
def api_history(ticker):
    records = HistoryManager.get_history(ticker.upper())
    return jsonify(records)


if __name__ == "__main__":
    app.run(debug=True, port=5001)
