import json
import os
from datetime import datetime

from core import config

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class HistoryManager:
    FILE_PATH = os.path.join(BASE_DIR, "data", "history.json")
    MAX_RECORDS_PER_TICKER = config.MAX_RECORDS_PER_TICKER  # 每檔標的保留的最大筆數

    @classmethod
    def save_record(cls, data_list: list, cmd_type: str):
        """將執行結果存入快取"""
        data_dir = os.path.dirname(cls.FILE_PATH)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        history = cls._load_all()
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        for data in data_list:
            ticker = data.ticker
            record = {
                "timestamp": now,
                "type": cmd_type,
                "price": data.price,
                # 每個欄位語意單一：yield 永遠是殖利率、div_amount 永遠是配息金額，
                # 不再用同一個 key 在不同指令下表達兩種意思。
                "pd_rate": getattr(data, 'premium_discount', None),
                "vol_ratio": getattr(data, 'volume_ratio', None),
                "yield": getattr(data, 'tr_annual_yield', None),
                "div_amount": getattr(data, 'last_div_amount', None),
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