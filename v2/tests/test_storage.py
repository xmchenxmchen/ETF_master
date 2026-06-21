"""HistoryManager 寫入 schema 與筆數上限的測試。"""
from core import config
from core.models import ETFData
from core.storage import HistoryManager


def _data(**kw):
    base = dict(ticker="TEST", name="Test", price=100.0, currency="USD")
    base.update(kw)
    return ETFData(**base)


def _point_to_tmp(monkeypatch, tmp_path):
    monkeypatch.setattr(HistoryManager, "FILE_PATH", str(tmp_path / "history.json"))


def test_yield_and_div_amount_are_separate_fields(monkeypatch, tmp_path):
    # #6：同一個 key 不再表達兩種意思 —— yield 永遠是殖利率、div_amount 永遠是配息
    _point_to_tmp(monkeypatch, tmp_path)
    data = _data(tr_annual_yield=6.8, last_div_amount=1.0)
    HistoryManager.save_record([data], "div")

    rec = HistoryManager.get_history("TEST")[0]
    assert rec["yield"] == 6.8
    assert rec["div_amount"] == 1.0
    assert rec["type"] == "div"


def test_pd_record_stores_pd_rate(monkeypatch, tmp_path):
    _point_to_tmp(monkeypatch, tmp_path)
    data = _data(nav=99.0)  # premium_discount 可算出
    HistoryManager.save_record([data], "pd")

    rec = HistoryManager.get_history("TEST")[0]
    assert rec["pd_rate"] is not None
    assert rec["type"] == "pd"


def test_records_capped_and_newest_first(monkeypatch, tmp_path):
    _point_to_tmp(monkeypatch, tmp_path)
    cap = config.MAX_RECORDS_PER_TICKER
    for i in range(cap + 5):
        HistoryManager.save_record([_data(price=float(i))], "pd")

    records = HistoryManager.get_history("TEST")
    assert len(records) == cap                       # 超出上限被裁切
    assert records[0]["price"] == float(cap + 4)     # 最新的在最前面


def test_get_history_unknown_ticker_returns_empty(monkeypatch, tmp_path):
    _point_to_tmp(monkeypatch, tmp_path)
    assert HistoryManager.get_history("NOPE") == []
