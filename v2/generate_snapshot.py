import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.fetcher import Fetcher
from core.engine import ETFEngine
from core.storage import HistoryManager

WATCHLIST_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "watchlist.txt")
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS_DIR = os.path.join(REPO_ROOT, "docs")
TEMPLATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "index.html")
OUT_HTML = os.path.join(DOCS_DIR, "index.html")
OUT_SUMMARY = os.path.join(DOCS_DIR, "summary.json")


def fetch_watchlist():
    engine = ETFEngine(watchlist_file=WATCHLIST_FILE)
    tickers = engine.prepare_tickers(["watchlist"])
    results = []
    for symbol, outcome in Fetcher.fetch_many(tickers):
        if isinstance(outcome, Exception):
            results.append({"ticker": symbol, "error": str(outcome)})
            print(f"  err {symbol}: {outcome}")
            continue
        data = outcome
        results.append({
            "ticker": data.ticker,
            "name": data.name,
            "price": round(data.price, 2),
            "currency": data.currency,
            "nav": round(data.nav, 2) if data.nav is not None else None,
            "pd": round(data.premium_discount, 2) if data.premium_discount is not None else None,
            "yield": round(data.tr_annual_yield, 2) if data.tr_annual_yield is not None else None,
            "vol_ratio": round(data.volume_ratio, 2),
        })
        print(f"  ok  {symbol}")
    return results


def build_summary(data, generated_at):
    ok = [d for d in data if "error" not in d]
    summary = {
        "generated_at": generated_at,
        "total": len(data),
        "ok": len(ok),
        "errors": len(data) - len(ok),
    }
    pd_items = [d for d in ok if d.get("pd") is not None]
    vol_items = [d for d in ok if d.get("vol_ratio")]
    if pd_items:
        td = min(pd_items, key=lambda x: x["pd"])
        tp = max(pd_items, key=lambda x: x["pd"])
        summary["top_discount"] = {"ticker": td["ticker"], "pd": td["pd"]}
        summary["top_premium"] = {"ticker": tp["ticker"], "pd": tp["pd"]}
    if vol_items:
        tv = max(vol_items, key=lambda x: x["vol_ratio"])
        summary["top_vol"] = {"ticker": tv["ticker"], "vol_ratio": tv["vol_ratio"]}
    return summary


if __name__ == "__main__":
    os.makedirs(DOCS_DIR, exist_ok=True)

    generated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    print(f"Fetching watchlist data ({generated_at}) ...")

    watchlist = fetch_watchlist()
    history = HistoryManager._load_all()
    summary = build_summary(watchlist, generated_at)

    with open(OUT_SUMMARY, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        html = f.read()

    # Inject static data before </head> so the JS can read it without an API call
    payload = json.dumps(
        {"watchlist": watchlist, "history": history, "generated_at": generated_at},
        ensure_ascii=False,
    )
    injection = f'<script type="application/json" id="__sd">{payload}</script>'
    html = html.replace("</head>", injection + "\n</head>", 1)

    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Dashboard  -> {OUT_HTML}")
    print(f"Summary    -> {OUT_SUMMARY}")
    print(f"Result: {summary['ok']}/{summary['total']} tickers ok")
