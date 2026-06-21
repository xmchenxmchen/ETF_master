"""集中管理散落各處的設定常數，避免 magic number 四散難維護。"""
import os

# --- 抓取層 (Fetcher) ---
HISTORY_PERIOD = "1mo"            # yfinance 歷史資料抓取區間
AVG_VOLUME_WINDOW = 10            # 計算均量所用的近 N 個交易日
SMART_YIELD_LOOKBACK_DAYS = 365   # Smart Yield 手動回溯加總的天數
DEFAULT_MAX_WORKERS = 6           # fetch_many 併發數（保守設定，降低限流風險）
DEFAULT_MAX_RETRIES = 2           # 暫時性錯誤的重試次數

# --- 重試 (Retry) ---
RETRY_BASE_DELAY = 0.5            # 指數退避的基準秒數

# --- 持久化層 (Storage) ---
MAX_RECORDS_PER_TICKER = 20       # 每檔標的在 history.json 保留的最大筆數

# --- Web Dashboard ---
WEB_PORT = int(os.environ.get("ETF_WEB_PORT", "5001"))
# 預設關閉 debug，避免不慎對外開放時洩漏堆疊資訊；需要時以環境變數開啟。
WEB_DEBUG = os.environ.get("ETF_WEB_DEBUG") == "1"
WATCHLIST_CACHE_TTL = int(os.environ.get("ETF_CACHE_TTL", "300"))  # 即時資料快取秒數
