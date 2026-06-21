"""ETFEngine.prepare_tickers 的 watchlist 解析、去重與大寫正規化測試。"""
from core.engine import ETFEngine


def _engine(tmp_path, lines):
    wl = tmp_path / "watchlist.txt"
    wl.write_text("\n".join(lines), encoding="utf-8")
    return ETFEngine(watchlist_file=str(wl))


def test_direct_symbols_uppercased(tmp_path):
    engine = _engine(tmp_path, [])
    assert engine.prepare_tickers(["voo", "qqq"]) == ["VOO", "QQQ"]


def test_dedup_preserves_order(tmp_path):
    engine = _engine(tmp_path, [])
    assert engine.prepare_tickers(["VOO", "voo", "QQQ"]) == ["VOO", "QQQ"]


def test_watchlist_filters_comments_and_blanks(tmp_path):
    engine = _engine(tmp_path, [
        "# 這是註解",
        "",
        "0050.tw",
        "   ",
        "voo",
        "# 又一個註解",
    ])
    assert engine.prepare_tickers(["watchlist"]) == ["0050.TW", "VOO"]


def test_watchlist_keyword_merges_with_direct(tmp_path):
    engine = _engine(tmp_path, ["0050.TW"])
    assert engine.prepare_tickers(["VOO", "watchlist"]) == ["VOO", "0050.TW"]


def test_watchlist_read_only_once(tmp_path):
    # 重複輸入 watchlist 不應重複展開清單
    engine = _engine(tmp_path, ["0050.TW", "0056.TW"])
    assert engine.prepare_tickers(["watchlist", "watchlist"]) == ["0050.TW", "0056.TW"]


def test_missing_watchlist_file_returns_empty(tmp_path):
    engine = ETFEngine(watchlist_file=str(tmp_path / "nope.txt"))
    assert engine.prepare_tickers(["watchlist"]) == []
