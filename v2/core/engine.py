import sys, os
from core.fetcher import Fetcher
from core.validator import DataValidator
from core.renderer import ETFRenderer
from core.storage import HistoryManager

class ETFEngine:
    def __init__(self, watchlist_file="watchlist.txt"):
        self.watchlist_file = watchlist_file

# 解析輸入 ticker 清單（支援 watchlist.txt），統一大寫，並去重，供 info/pd/vol 使用
    def prepare_tickers(self, ticker_symbols: list) -> list:
        processed_list = []
        found_watchlist = False  # 標記是否已經處理過 watchlist，避免重複讀取

        for sym in ticker_symbols:
            if sym.lower() == "watchlist":
                if found_watchlist:
                    continue
                
                if os.path.exists(self.watchlist_file):
                    file_tickers = []
                    with open(self.watchlist_file, "r", encoding="utf-8") as f:
                        for line in f:
                            clean_line = line.strip()
                            # 支援註解與空白行過濾
                            if clean_line and not clean_line.startswith("#"):
                                file_tickers.append(clean_line.upper())
                    
                    if not file_tickers:
                        print(f"ℹ️ 提示: 觀察列表檔案 [{self.watchlist_file}] 內容為空。")
                    else:
                        processed_list.extend(file_tickers)
                        found_watchlist = True
                else:
                    print(f"⚠️ 錯誤: 找不到觀察列表檔案 [{self.watchlist_file}]，請確認檔案是否存在。")
            else:
                processed_list.append(sym.upper())

        # 統一直覺去重並保持順序
        final_list = list(dict.fromkeys(processed_list))
        
        # 需求 4：若最終清單為空，給予明確提示
        if not final_list and ticker_symbols:
            print("❌ 錯誤: 未能從輸入或檔案中取得任何有效的標的代碼。")
            
        return final_list

    def _scan(self, ticker_symbols: list, validator) -> list:
        """共用收集邏輯：併發抓取所有標的、逐檔驗證，並維持輸入順序。

        - 抓取階段交給 Fetcher.fetch_many() 併發處理（I/O 密集）。
        - 驗證階段在主執行緒序列執行，確保錯誤輸出順序穩定、可預測。
        - 採非阻斷式 UX：單一標的失敗只印錯誤標記，不影響其他標的。
        回傳通過驗證的 ETFData 清單。
        """
        results = []
        for symbol, outcome in Fetcher.fetch_many(ticker_symbols):
            if isinstance(outcome, Exception):
                print(f"❌ 標的 [{symbol}] 分析失敗: {outcome}")
                continue
            try:
                validator(outcome)
                results.append(outcome)
            except Exception as e:
                print(f"❌ 標的 [{symbol}] 分析失敗: {e}")
        return results

    def run_info(self, ticker_symbols: list):
        results = self._scan(ticker_symbols, DataValidator.validate_for_info)

        for data in results:
            print("-" * 45)
            print(f"📊 [ETF 基本面掃描] {data.name}")
            print("-" * 45)
            print(f"  標的代碼: {data.ticker}")
            print(f"  目前市價: {data.price:.2f} {data.currency}")

            # 優化顯示：如果殖利率是 0，顯示 N/A 或 0.00%
            y_val = f"{data.tr_annual_yield:.2f}%" if data.tr_annual_yield > 0 else "N/A (無發股紀錄)"
            print(f"  過去一年殖利率: {y_val}")

            print(f"  更新時間: {data.last_updated}")
            print("-" * 45 + "\n")

        if not results:
            return
        HistoryManager.save_record(results, "info")

    def run_pd(self, ticker_symbols: list):
        results = self._scan(ticker_symbols, DataValidator.validate_for_pd)
        if not results:
            return

        HistoryManager.save_record(results, "pd")

        # 交給渲染器決定怎麼畫圖
        if len(results) == 1:
            ETFRenderer.render_single_pd(results[0])
        else:
            ETFRenderer.render_comparison_pd(results)

    def run_vol(self, ticker_symbols: list):
        results = self._scan(ticker_symbols, DataValidator.validate_for_vol)
        if not results:
            return

        HistoryManager.save_record(results, "vol")

        # 分流給渲染器
        if len(results) == 1:
            ETFRenderer.render_single_vol(results[0])
        else:
            ETFRenderer.render_comparison_vol(results)
    
# core/engine.py

    def run_div(self, ticker_symbols: list, limit=5):
        """執行配息查詢指令"""
        for symbol in ticker_symbols:
            try:
                fetcher = Fetcher(symbol)
                div_history = fetcher.fetch_dividends(limit=limit)
                basic_data = fetcher.fetch() # 這是 ETFData 物件

                ETFRenderer.render_dividends(symbol, div_history)

                if div_history:
                    basic_data.last_div_amount = div_history[0]['amount']
                
                # 儲存紀錄
                HistoryManager.save_record([basic_data], "div")
                
            except Exception as e:
                print(f"❌ 標的 [{symbol.upper()}] 配息查詢失敗: {e}")
    
    def run_history(self, ticker_symbols: list):
        """處理 history 指令"""
        for symbol in ticker_symbols:
            records = HistoryManager.get_history(symbol)
            ETFRenderer.render_history(symbol.upper(), records)