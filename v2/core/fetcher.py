import yfinance as yf
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from core.models import ETFData

class Fetcher:
    def __init__(self, ticker_symbol: str):
        self.ticker_symbol = ticker_symbol.upper()
        self.ticker = yf.Ticker(self.ticker_symbol)
        # 配息資料快取：同一個 Fetcher 物件上，dividends 只向 yfinance 抓一次，
        # 供 fetch() 的 Smart Yield 計算與 fetch_dividends() 共用，避免重複 HTTP 請求。
        self._dividends_cache = None

    @property
    def dividends(self):
        """惰性載入並快取該標的的配息 Series。"""
        if self._dividends_cache is None:
            self._dividends_cache = self.ticker.dividends
        return self._dividends_cache

    def fetch(self) -> ETFData:
        # 核心抓取邏輯：不靜音，保留最原始的報錯資訊供開發參考。
        # 1. 抓取原始資料 (若代碼錯誤，這裡會直接噴出 yfinance 的 404 訊息)
        hist = self.ticker.history(period="1mo")
        info = self.ticker.info or {}
        # 2. 核心存在性判定：優先從歷史資料拿價格
        # hist_price 是最穩定的數據源
        hist_price = hist['Close'].iloc[-1] if not hist.empty else None
        info_price = info.get('regularMarketPrice') or info.get('previousClose')
        
        final_price = info_price or hist_price
        if final_price is None:
            raise ValueError(f"找不到標的 '{self.ticker_symbol}'，或該時段無交易價格，請檢查代碼。")
        final_price = float(final_price)

        # 3. 成交量計算 (防彈處理：避免指數型標的回傳 None)
        # 結合 hist 與 info，取最大值以確保抓到最即時的量
        hist_vol = float(hist['Volume'].iloc[-1]) if not hist.empty else 0.0
        info_vol = float(info.get('regularMarketVolume') or info.get('volume') or 0.0)
        latest_vol = max(hist_vol, info_vol)
        
        # 計算前 10 個交易日的平均 (不含今日最後一筆)
        if len(hist) > 1:
            avg_vol_10d = float(hist['Volume'].iloc[:-1].tail(10).mean())
        else:
            avg_vol_10d = latest_vol if latest_vol > 0 else 1.0 # 避免除以 0    
        
        # 4. 殖利率計算 (Smart Yield 邏輯)
        tr_annual_yield = None
        if info.get('trailingAnnualDividendYield') is not None:
            # yfinance 原始資料為 0.015 格式，需轉換為 1.5 (%)
            tr_annual_yield = float(info['trailingAnnualDividendYield'] * 100)
        else:
            # 針對台股 (如 0050) 或指數進行手動計算
            # print(f"⚠️ {self.ticker_symbol} 採手動計算實質殖利率...")
            one_year_ago = datetime.now() - timedelta(days=365)
            divs = self.dividends

            if not divs.empty:
                # 處理時區問題：將 divs 的時區抹除 (Naive) 以便與 datetime.now() 比較
                if getattr(divs.index, 'tz', None) is not None:
                    divs = divs.copy()
                    divs.index = divs.index.tz_localize(None)
                
                yearly_div_sum = float(divs[divs.index >= one_year_ago].sum())
                if final_price > 0:
                    tr_annual_yield = (yearly_div_sum / final_price) * 100
            
            # 若最終還是沒資料，設為 0.0 而非 None，保護 Renderer
            if tr_annual_yield is None:
                tr_annual_yield = 0.0

        # 5. 封裝數據
        # 這裡會觸發 models.py 裡的 volume_ratio() 方法
        return ETFData(
            ticker=self.ticker_symbol,
            name=info.get('longName') or info.get('shortName') or self.ticker_symbol,
            price=final_price,
            currency=info.get('currency', 'USD'),
            nav=float(info.get('navPrice')) if info.get('navPrice') else None,
            tr_annual_yield=tr_annual_yield,
            latest_volume=latest_vol,
            avg_volume_10d=avg_vol_10d,
            last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    

    @classmethod
    def fetch_many(cls, symbols: list, max_workers: int = 8):
        """併發抓取多檔標的。

        回傳 list[(symbol, result)]，順序與輸入一致；result 為 ETFData，
        若該檔抓取失敗則為對應的 Exception。呼叫端負責決定如何處理錯誤，
        維持「單一失敗不中斷全域」的非阻斷式 UX。
        """
        if not symbols:
            return []

        def _one(sym):
            try:
                return sym, cls(sym).fetch()
            except Exception as e:  # noqa: BLE001 — 交由呼叫端分類處理
                return sym, e

        # I/O 密集（等 yfinance HTTP），用執行緒池把牆鐘時間從「相加」變「取最大」
        workers = min(max_workers, len(symbols))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            # executor.map 保證回傳順序與輸入一致
            return list(pool.map(_one, symbols))

    def fetch_dividends(self, limit=10):
        """抓取該標的的歷史配息紀錄"""
        # yfinance 的 dividends 回傳的是一個 Series，索引為日期（走共用快取）
        divs = self.dividends

        if divs.empty:
            return []

        # 由新到舊排序，並取最近的 N 筆
        latest_divs = divs.sort_index(ascending=False).head(limit)
        
        results = []
        for date, amount in latest_divs.items():
            results.append({
                "date": date.strftime('%Y-%m-%d'),
                "amount": float(amount)
            })
        return results
    