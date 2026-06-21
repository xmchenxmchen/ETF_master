"""DataValidator 分級驗證邏輯的單元測試。"""
import pytest

from core.models import ETFData
from core.validator import DataValidator


def _make(**kw):
    base = dict(ticker="TEST", name="Test ETF", price=100.0, currency="USD")
    base.update(kw)
    return ETFData(**base)


class TestValidateForInfo:
    def test_valid_price_passes(self):
        assert DataValidator.validate_for_info(_make(price=100.0)) is True

    def test_zero_price_raises(self):
        with pytest.raises(ValueError):
            DataValidator.validate_for_info(_make(price=0.0))

    def test_negative_yield_reset_to_zero(self):
        # info 採寬鬆驗證：負殖利率視為缺失，補 0.0 而非中斷
        data = _make(price=100.0, tr_annual_yield=-1.0)
        DataValidator.validate_for_info(data)
        assert data.tr_annual_yield == 0.0

    def test_none_yield_reset_to_zero(self):
        data = _make(price=100.0, tr_annual_yield=None)
        DataValidator.validate_for_info(data)
        assert data.tr_annual_yield == 0.0


class TestValidateForPd:
    def test_valid_passes(self):
        assert DataValidator.validate_for_pd(_make(price=100.0, nav=99.0)) is True

    def test_missing_nav_raises(self):
        # pd 採嚴格驗證：淨值是折溢價核心，缺失必須中斷
        with pytest.raises(ValueError):
            DataValidator.validate_for_pd(_make(price=100.0, nav=None))

    def test_zero_nav_raises(self):
        with pytest.raises(ValueError):
            DataValidator.validate_for_pd(_make(price=100.0, nav=0.0))


class TestValidateForVol:
    def test_valid_passes(self):
        data = _make(latest_volume=200.0, avg_volume_10d=100.0)
        assert DataValidator.validate_for_vol(data) is True

    def test_missing_volume_raises(self):
        with pytest.raises(ValueError):
            DataValidator.validate_for_vol(_make(latest_volume=None, avg_volume_10d=100.0))

    def test_zero_avg_raises(self):
        with pytest.raises(ValueError):
            DataValidator.validate_for_vol(_make(latest_volume=200.0, avg_volume_10d=0.0))
