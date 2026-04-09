from dataclasses import dataclass, field, asdict
from typing import List, Optional

@dataclass
class Holding:
    symbol: str
    name: str
    weight: float 

@dataclass
class ETFData:
    """
    ETF 資料模型。
    """
    ticker: str
    name: str
    price: float
    currency: str
    
    # 核心指標 (設為 Optional 並給予 None 預設值)
    # aum: Optional[float] = None
    # expense_ratio: Optional[float] = None 
    tr_annual_yield: Optional[float] = None               
    nav: Optional[float] = None           
    latest_volume: Optional[float] = None    
    avg_volume_10d: Optional[float] = None  
    
    # 持股與時間
    # top_holdings: List[Holding] = field(default_factory=list)
    last_updated: Optional[str] = None # 👈 統一使用 Optional

    @property
    def premium_discount(self) -> float:
        """計算折溢價率 (%)"""
        if self.price and self.nav and self.nav > 0:
            return ((self.price - self.nav) / self.nav) * 100
        return None

    @property 
    def volume_ratio(self) -> float:
        """計算成交量動能倍率，確保永遠回傳 float 避免渲染出錯"""
        if self.latest_volume and self.avg_volume_10d and self.avg_volume_10d > 0:
            return float(self.latest_volume / self.avg_volume_10d)
        return 0.0  # 改回傳 0.0 而不是 None

    def to_dict(self) -> dict:
        """
        將物件轉為字典，包含計算後的屬性。
        """
        # 使用 asdict 處理 dataclass 轉換最專業
        data = asdict(self)
        data.update({
            'premium_discount': self.premium_discount,
            'volume_ratio': self.volume_ratio
        })
        return data
    