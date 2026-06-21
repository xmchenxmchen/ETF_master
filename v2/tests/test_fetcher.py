"""Fetcher.fetch_many 的併發、順序保留與錯誤捕捉測試（不觸網）。"""
from core.fetcher import Fetcher
from core.models import ETFData
from core.retry import TickerNotFoundError, TransientFetchError


def _data(ticker):
    return ETFData(ticker=ticker, name=ticker, price=10.0, currency="USD")


def test_empty_input_returns_empty():
    assert Fetcher.fetch_many([]) == []


def test_preserves_input_order(monkeypatch):
    # 以 ticker 為準回傳，驗證即使併發完成順序不定，輸出仍與輸入一致
    monkeypatch.setattr(Fetcher, "fetch", lambda self: _data(self.ticker_symbol))
    out = Fetcher.fetch_many(["VOO", "QQQ", "0050.TW"])
    assert [sym for sym, _ in out] == ["VOO", "QQQ", "0050.TW"]
    assert all(isinstance(res, ETFData) for _, res in out)


def test_single_failure_does_not_break_batch(monkeypatch):
    def fake_fetch(self):
        if self.ticker_symbol == "BAD":
            raise TickerNotFoundError("查無此代碼")
        return _data(self.ticker_symbol)

    monkeypatch.setattr(Fetcher, "fetch", fake_fetch)
    out = dict(Fetcher.fetch_many(["VOO", "BAD", "QQQ"]))
    assert isinstance(out["VOO"], ETFData)
    assert isinstance(out["QQQ"], ETFData)
    assert isinstance(out["BAD"], TickerNotFoundError)


def test_transient_error_is_retried(monkeypatch):
    # 第一次拋暫時性錯誤、第二次成功 → fetch_many 應透過 call_with_retry 救回來
    state = {"calls": 0}

    def flaky_fetch(self):
        state["calls"] += 1
        if state["calls"] == 1:
            raise TransientFetchError("限流")
        return _data(self.ticker_symbol)

    monkeypatch.setattr(Fetcher, "fetch", flaky_fetch)
    # 退避只會 sleep 一次（約 0.5s），測試可接受
    out = dict(Fetcher.fetch_many(["VOO"], max_retries=2))
    assert isinstance(out["VOO"], ETFData)
    assert state["calls"] == 2


def test_dividends_cache_single_fetch(monkeypatch):
    # dividends property 應只向底層抓一次，之後走快取
    import pandas as pd

    calls = {"n": 0}

    class FakeTicker:
        @property
        def dividends(self):
            calls["n"] += 1
            return pd.Series(dtype=float)

    f = Fetcher("0056.TW")
    f.ticker = FakeTicker()
    _ = f.dividends
    _ = f.dividends
    _ = f.dividends
    assert calls["n"] == 1
