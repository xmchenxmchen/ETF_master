"""ETFData 計算屬性的單元測試。"""
from core.models import ETFData


def _make(**kw):
    base = dict(ticker="TEST", name="Test ETF", price=100.0, currency="USD")
    base.update(kw)
    return ETFData(**base)


class TestPremiumDiscount:
    def test_premium(self):
        # 市價高於淨值 → 正的溢價
        data = _make(price=102.0, nav=100.0)
        assert data.premium_discount == 2.0

    def test_discount(self):
        # 市價低於淨值 → 負的折價
        data = _make(price=99.0, nav=100.0)
        assert data.premium_discount == -1.0

    def test_nav_missing_returns_none(self):
        # 指數型標的常無淨值 → 不應計算，回 None
        data = _make(price=100.0, nav=None)
        assert data.premium_discount is None

    def test_nav_zero_returns_none(self):
        # 淨值為 0 不可當分母
        data = _make(price=100.0, nav=0.0)
        assert data.premium_discount is None


class TestVolumeRatio:
    def test_normal(self):
        data = _make(latest_volume=200.0, avg_volume_10d=100.0)
        assert data.volume_ratio == 2.0

    def test_missing_avg_returns_zero(self):
        # 缺資料時回 0.0（而非 None），保護 Renderer 不會炸
        data = _make(latest_volume=200.0, avg_volume_10d=None)
        assert data.volume_ratio == 0.0

    def test_zero_avg_returns_zero(self):
        data = _make(latest_volume=200.0, avg_volume_10d=0.0)
        assert data.volume_ratio == 0.0


def test_to_dict_includes_computed_props():
    data = _make(price=102.0, nav=100.0, latest_volume=200.0, avg_volume_10d=100.0)
    d = data.to_dict()
    assert d["premium_discount"] == 2.0
    assert d["volume_ratio"] == 2.0
    assert d["ticker"] == "TEST"
