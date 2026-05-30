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

    def run_info(self, ticker_symbols: list):
            results = []

            for symbol in ticker_symbols:
                try:
                    data = Fetcher(symbol).fetch()
                    # 這裡調用你剛才修改過的「寬鬆版」Validator
                    DataValidator.validate_for_info(data)
                    results.append(data)

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
                except Exception as e:
                    print(f"❌ 標的 [{symbol}] 分析失敗: {e}")
            
            # --- 迴圈結束後才執行儲存與返回 ---
            if not results:
                return

            from core.storage import HistoryManager
            HistoryManager.save_record(results, "info")
    
    def run_pd(self, ticker_symbols: list):
        results = []
        # 第一階段：獲取資料
        for symbol in ticker_symbols:
            try:
                data = Fetcher(symbol).fetch()
                DataValidator.validate_for_pd(data)
                results.append(data)
            except Exception as e:
                print(f"❌ 標的 [{symbol}] 分析失敗: {e}")

        if not results:
            return
        
        from core.storage import HistoryManager
        HistoryManager.save_record(results, "pd")
        
        # 第二階段：交給渲染器決定怎麼畫圖
        if len(results) == 1:
            ETFRenderer.render_single_pd(results[0])
        else:
            ETFRenderer.render_comparison_pd(results)

# core/engine.py 修改後的 run_vol
    def run_vol(self, ticker_symbols: list):
        results = []
        # 第一階段：收集資料
        for symbol in ticker_symbols:
            try:
                data = Fetcher(symbol).fetch()
                DataValidator.validate_for_vol(data)
                results.append(data)
            except Exception as e:
                print(f"❌ 標的 [{symbol}] 分析失敗: {e}")
        if not results:
            return
        from core.storage import HistoryManager
        HistoryManager.save_record(results, "vol")

        # 第二階段：分流給渲染器
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