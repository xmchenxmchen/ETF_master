class DataValidator:
    """
    數據驗證模組：負責過濾無效數據，確保核心功能穩定性。
    """
    
    @staticmethod
    def validate_for_info(data):
        """
        驗證 info 基本需求：必須有正數市價。
        """
        if not data.price or data.price <= 0:
            raise ValueError(f"無法獲取標的 [{data.ticker}] 的有效市場價格。")
        if not data.tr_annual_yield or data.tr_annual_yield < 0:
                    data.tr_annual_yield = 0.0
        return True

    @staticmethod
    def validate_for_pd(data):
        """
        驗證 pd 需求：市價 (呼叫 info 驗證) + 淨值。
        """
        # 🌟 優化：直接呼叫已有的驗證邏輯
        DataValidator.validate_for_info(data)
        
        if not data.nav or data.nav <= 0:
            raise ValueError(f"標的 [{data.ticker}] 目前無法抓取官方淨值 (NAV)，計算終止。")

        return True
    
    @staticmethod
    def validate_for_vol(data):
        """
        驗證 vol 數據完整性。
        """
        if data.latest_volume is None or data.avg_volume_10d is None:
            raise ValueError(f"標的 [{data.ticker}] 無法獲取完整的成交量數據。")
            
        if data.avg_volume_10d <= 0:
            raise ValueError(f"標的 [{data.ticker}] 的平均成交量異常，無法分析。")

        return True