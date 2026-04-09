import os
import sys
import argparse

# 專案路徑校正：確保核心模組可被正確導入
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from core.engine import ETFEngine
except ImportError as e:
    print(f"❌ 系統啟動失敗: 找不到核心模組 ({e})")
    sys.exit(1)

def main():
    # 定義範例清單文字
    examples = """
    常用代碼範例 (Ticker List):
    🇹🇼 台股 ETF:
    - 0050.TW  (元大台灣50)
    - 0056.TW  (元大高股息)

    🇺🇸 美股 ETF:
    - VOO  (S&P 500)
    - QQQ  (Nasdaq 100)

    📈 指數 (Index):
    - ^TWII (台股大盤)
    - ^GSPC (標普 500)

    💡 觀察列表模式 (Watchlist Mode):
    - watchlist  (自動讀取目錄下的 watchlist.txt 檔案)
    """
    # 初始化參數解析器
    parser = argparse.ArgumentParser(
        description="ETF-Master v2.0 (Lite) - 輕量級 ETF 資訊查詢工具",
        epilog=examples,
        formatter_class=argparse.RawTextHelpFormatter  # 確保範例文字能正確換行
    )
    subparsers = parser.add_subparsers(dest="command", help="可用指令")

    # 1. info 指令：獲取基本面資訊
    info_parser = subparsers.add_parser("info", help="顯示 ETF 基本資訊")
    info_parser.add_argument("--tk", required=True, nargs="+", help="輸入股票或清單查看基本資訊 (例: 0050.TW)")

    # 2. pd 指令：折溢價分析
    pd_parser = subparsers.add_parser("pd", help="計算折溢價率")
    pd_parser.add_argument("--tk", required=True, nargs="+", help="輸入股票或清單查看折溢價 (例: 0050.TW)")
    
    # 3. vol 指令：交易量與流動性分析
    vol_parser = subparsers.add_parser("vol", help="分析交易量與流動性")
    vol_parser.add_argument("--tk", required=True, nargs="+", help="輸入股票或清單查看交易量 (例: 0050.TW)")

    # 4. div 指令：股息資訊分析
    div_parser = subparsers.add_parser("div", help="查詢 ETF 歷史配息紀錄")
    div_parser.add_argument("--tk", required=True, nargs="+", help="標的代碼 (可多個) 或輸入 'watchlist'")
    div_parser.add_argument("--limit", type=int, default=5, help="顯示最近幾筆配息 (預設 5 筆)")
    
    # 5. history 指令：查詢歷史紀錄 (注意這裡改成 history_parser)
    history_parser = subparsers.add_parser("history", help="查詢標的的本地歷史紀錄")
    history_parser.add_argument("--tk", nargs="+", help="標的代碼或輸入 'watchlist'")


    args = parser.parse_args() 
    engine = ETFEngine()

    # 1. 統一解析代碼
    ticker_list = engine.prepare_tickers(args.tk or [])

    # 2. 確保所有指令都在同一個判斷鏈條內，避免重複執行
    if args.command == "info":
        engine.run_info(ticker_list)
    elif args.command == "pd":
        engine.run_pd(ticker_list)
    elif args.command == "vol":
        engine.run_vol(ticker_list)
    elif args.command == "div":
        engine.run_div(ticker_list, limit=args.limit)
    elif args.command == "history":
        engine.run_history(ticker_list)
    else:
        parser.print_help()

# 當前模組是直接執行（而非被 import）時才會執行以下程式
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n使用者中斷程式執行。")
        sys.exit(0)