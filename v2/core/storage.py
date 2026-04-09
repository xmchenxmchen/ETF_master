import json
import os
from datetime import datetime

class HistoryManager:
    FILE_PATH = "data/history.json"
    MAX_RECORDS_PER_TICKER = 20  # 限制每檔標的只留最近 20 筆

    @classmethod
    def save_record(cls, data_list: list, cmd_type: str):
        """將執行結果存入快取"""
        if not os.path.exists("data"):
            os.makedirs("data")

        history = cls._load_all()
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        for data in data_list:
            ticker = data.ticker
            record = {
                "timestamp": now,
                "type": cmd_type,
                "price": data.price,
                # 不管現在是什麼指令，只要 data 裡有值就存下來
                "pd_rate": getattr(data, 'premium_discount', None),
                "vol_ratio": getattr(data, 'volume_ratio', None),
                "yield": getattr(data, 'tr_annual_yield', None)
            }
            
            if ticker not in history:
                history[ticker] = []
            
            # 插入新紀錄並維持數量限制
            history[ticker].insert(0, record)
            history[ticker] = history[ticker][:cls.MAX_RECORDS_PER_TICKER]

        with open(cls.FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=4, ensure_ascii=False)

    @classmethod
    def get_history(cls, ticker: str):
        history = cls._load_all()
        return history.get(ticker.upper(), [])

    @staticmethod
    def _load_all():
        if not os.path.exists(HistoryManager.FILE_PATH):
            return {}
        with open(HistoryManager.FILE_PATH, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}