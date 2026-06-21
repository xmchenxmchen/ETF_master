"""抓取層的錯誤分類與重試工具。

設計動機：自從抓取改為併發（Fetcher.fetch_many），同時對 yfinance 發出多個
請求會提高被 rate-limit 的機率。若把「暫時性錯誤（限流/逾時/連線抖動）」與
「永久性錯誤（代碼不存在）」一視同仁，使用者會誤以為代碼打錯。

因此這裡：
1. 定義例外階層，明確區分可重試與不可重試。
2. 提供 is_transient() 分類器，判斷一個例外是否值得重試。
3. 提供 call_with_retry()，對暫時性錯誤做指數退避 + 抖動重試。

所有函式都不依賴網路，方便單元測試。
"""

import random
import time

from core import config


class FetchError(Exception):
    """抓取層錯誤的基底類別。"""


class TickerNotFoundError(FetchError):
    """永久性錯誤：代碼不存在或查無價格，重試也沒用。"""


class TransientFetchError(FetchError):
    """暫時性錯誤：限流、逾時、連線抖動等，值得重試。"""


# yfinance / requests 在限流或暫時性故障時，訊息中常出現的關鍵字
_TRANSIENT_MARKERS = (
    "too many requests",
    "rate limit",
    "rate-limit",
    "timed out",
    "timeout",
    "temporarily unavailable",
    "connection reset",
    "connection aborted",
    "max retries",
    "service unavailable",
    "bad gateway",
)

# 視為暫時性、值得重試的 HTTP 狀態碼
_TRANSIENT_STATUS = {429, 500, 502, 503, 504}


def is_transient(exc: Exception) -> bool:
    """判斷例外是否為暫時性（值得重試）。"""
    # 1. 明確標記的自訂例外優先
    if isinstance(exc, TickerNotFoundError):
        return False
    if isinstance(exc, TransientFetchError):
        return True

    # 2. requests 的網路層例外（延遲匯入，避免硬相依）
    try:
        import requests

        if isinstance(exc, (requests.exceptions.ConnectionError,
                            requests.exceptions.Timeout)):
            return True
        if isinstance(exc, requests.exceptions.HTTPError):
            status = getattr(getattr(exc, "response", None), "status_code", None)
            return status in _TRANSIENT_STATUS
    except ImportError:
        pass

    # 3. 退而求其次：用訊息關鍵字判斷
    msg = str(exc).lower()
    return any(marker in msg for marker in _TRANSIENT_MARKERS)


def call_with_retry(fn, *, max_retries: int = config.DEFAULT_MAX_RETRIES,
                    base_delay: float = config.RETRY_BASE_DELAY,
                    sleep=time.sleep, rng: random.Random = random):
    """執行 fn()，遇到暫時性錯誤時以指數退避 + 抖動重試。

    - 永久性錯誤（如 TickerNotFoundError）立即往外拋，不重試。
    - 退避時間為 base_delay * 2**attempt，再加上 [0, base_delay) 的隨機抖動，
      避免多個併發請求的重試在同一時間點同步打爆對方（thundering herd）。
    - sleep / rng 可注入，方便測試時不真的等待。
    """
    attempt = 0
    while True:
        try:
            return fn()
        except Exception as e:  # noqa: BLE001 — 由 is_transient 決定是否吞下重試
            if attempt >= max_retries or not is_transient(e):
                raise
            delay = base_delay * (2 ** attempt) + rng.uniform(0, base_delay)
            sleep(delay)
            attempt += 1
