"""錯誤分類 (is_transient) 與重試 (call_with_retry) 的單元測試。"""
import random

import pytest

from core.retry import (
    TickerNotFoundError,
    TransientFetchError,
    call_with_retry,
    is_transient,
)


class TestIsTransient:
    def test_ticker_not_found_is_permanent(self):
        assert is_transient(TickerNotFoundError("查無此代碼")) is False

    def test_transient_marker_class_is_transient(self):
        assert is_transient(TransientFetchError("限流")) is True

    @pytest.mark.parametrize("msg", [
        "Too Many Requests",
        "rate limit exceeded",
        "Read timed out",
        "Connection reset by peer",
        "Max retries exceeded",
        "503 Service Unavailable",
    ])
    def test_transient_messages(self, msg):
        assert is_transient(Exception(msg)) is True

    def test_unknown_error_is_not_transient(self):
        # 無法辨識的錯誤預設不重試，避免無謂耗時
        assert is_transient(ValueError("某種程式邏輯錯誤")) is False

    def test_requests_http_429_is_transient(self):
        requests = pytest.importorskip("requests")
        err = requests.exceptions.HTTPError()
        err.response = type("R", (), {"status_code": 429})()
        assert is_transient(err) is True

    def test_requests_http_404_is_not_transient(self):
        requests = pytest.importorskip("requests")
        err = requests.exceptions.HTTPError()
        err.response = type("R", (), {"status_code": 404})()
        assert is_transient(err) is False


class TestCallWithRetry:
    def _no_sleep(self):
        calls = []
        return (lambda d: calls.append(d)), calls

    def test_returns_on_first_success(self):
        sleep, slept = self._no_sleep()
        result = call_with_retry(lambda: "ok", sleep=sleep)
        assert result == "ok"
        assert slept == []  # 沒失敗就不該 sleep

    def test_retries_transient_then_succeeds(self):
        sleep, slept = self._no_sleep()
        attempts = {"n": 0}

        def flaky():
            attempts["n"] += 1
            if attempts["n"] < 3:
                raise TransientFetchError("限流")
            return "ok"

        result = call_with_retry(
            flaky, max_retries=2, base_delay=0.1,
            sleep=sleep, rng=random.Random(0),
        )
        assert result == "ok"
        assert attempts["n"] == 3      # 1 次原始 + 2 次重試
        assert len(slept) == 2         # 重試前 sleep 兩次

    def test_permanent_error_not_retried(self):
        sleep, slept = self._no_sleep()
        attempts = {"n": 0}

        def boom():
            attempts["n"] += 1
            raise TickerNotFoundError("查無此代碼")

        with pytest.raises(TickerNotFoundError):
            call_with_retry(boom, max_retries=3, sleep=sleep)
        assert attempts["n"] == 1      # 永久錯誤只試一次
        assert slept == []

    def test_exhausts_retries_then_reraises(self):
        sleep, slept = self._no_sleep()
        attempts = {"n": 0}

        def always_transient():
            attempts["n"] += 1
            raise TransientFetchError("一直限流")

        with pytest.raises(TransientFetchError):
            call_with_retry(
                always_transient, max_retries=2, base_delay=0.1,
                sleep=sleep, rng=random.Random(0),
            )
        assert attempts["n"] == 3      # 1 + 2 retries 後仍失敗
        assert len(slept) == 2

    def test_backoff_is_exponential(self):
        sleep, slept = self._no_sleep()

        def always_transient():
            raise TransientFetchError("限流")

        # rng 固定回 0，抖動為 0，方便驗證退避基準：base, base*2
        rng = type("R", (), {"uniform": staticmethod(lambda a, b: 0.0)})()
        with pytest.raises(TransientFetchError):
            call_with_retry(
                always_transient, max_retries=2, base_delay=0.5,
                sleep=sleep, rng=rng,
            )
        assert slept == [0.5, 1.0]
