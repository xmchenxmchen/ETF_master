class ETFRenderer:

    @classmethod
    def render_history(cls, ticker: str, records: list):
        if not records:
            print(f"📌 標的 [{ticker}] 尚無歷史紀錄。")
            return

        print(f"\n" + "═" * 75)
        print(f"📂 標的歷史檔案：{ticker}")
        print("═" * 75)
        print(f"{'查詢時間':<18} | {'類型':<6} | {'當前市價':>10} | {'數據詳情'}")
        print("─" * 75)
    
        for r in records:
            t = r.get('type', 'info')
            price = r.get('price', 0)
            
            # --- 關鍵防呆：使用 .get(key, 0) 並判斷是否為 None ---
            # 找到處理 detail 的邏輯部分
            if t == "pd":
                val = r.get('pd_rate')
                detail = f"折溢價: {val:>+7.2f}%" if val is not None else "折溢價:    N/A"
            elif t == "vol":
                val = r.get('vol_ratio')
                detail = f"量能比: {val:>7.2f}x" if val is not None else "量能比:    N/A"
            elif t == "div":
                # 專為 div 類型顯示配息金額，使用 4 位小數
                val = r.get('yield')
                detail = f"末次配息: {val:>7.4f}" if val is not None else "末次配息:    N/A"
            elif t == "info":
                val = r.get('yield')
                detail = f"殖利率: {val:>7.2f}%" if val is not None else "殖利率:    N/A"

            print(f"{r['timestamp']:<18} | {t:<6} | {price:>10.2f} | {detail}")
                
        print("═" * 75 + "\n")
    
    @staticmethod
    def get_pd_status(pd_val: float) -> str:
        """集中管理折溢價的診斷文字與 Emoji"""
        if pd_val is None: return "數據缺失"
        if pd_val < -0.5: return "🔥 顯著折價"
        if pd_val > 0.5: return "⚠️ 顯著溢價"
        if -0.1 <= pd_val <= 0.1: return "⚖️ 價格精準"
        return "✅ 正常波動"

    @classmethod
    def render_single_pd(cls, data):
        """垂直詳細報告格式"""
        pd_val = data.premium_discount
        status = cls.get_pd_status(pd_val)
        
        print("=" * 45)
        print(f"💎 [ETF 折溢價分析] {data.ticker}")
        print("=" * 45)
        print(f"  當前市價: {data.price:.2f} {data.currency}")
        print(f"  官方淨值: {data.nav:.2f} {data.currency}")
        print(f"  折溢價率: {pd_val:+.2f}%") 
        print(f"  專業評估: {status}")
        print("=" * 45 + "\n")

    @classmethod
    def render_comparison_pd(cls, data_list):
        """需求 1：橫向比較表格格式"""
        # 依折價程度排序
        sorted_list = sorted(data_list, key=lambda x: x.premium_discount or 0)
        
        print("\n" + "═" * 90)
        print(f"📊 [ETF 折溢價橫向比較模式] 共 {len(data_list)} 檔標的")
        print("─" * 90)
        print(f"{'代碼':<12} | {'市價':>10} | {'淨值':>10} | {'折溢價%':>10} | {'專業評估'}")
        print("─" * 90)
        
        for i, data in enumerate(sorted_list):
            pd_val = data.premium_discount
            status = cls.get_pd_status(pd_val)

            # 視覺強化：標註極值
            extrema = ""
            if i == 0 and pd_val < -0.3: 
                extrema = " ✨ [最具安全邊際]"
            elif i == len(sorted_list) - 1 and pd_val > 0.3: 
                extrema = " ⚠️ [溢價幅度最高]"
            
            print(f"{data.ticker:<12} | {data.price:>10.2f} | {data.nav:>10.2f} | {pd_val:>+9.2f}% | {status}{extrema}")
            
        print("═" * 90)
        print("💡 投資小提示：表格已按『折價程度』排序。負值愈大代表目前市價低於淨值。\n")
    
    # core/renderer.py 內新增

    @staticmethod
    def get_vol_status(ratio: float) -> str:
        """集中管理量能動能的診斷文字"""
        if ratio is None: return "數據缺失"
        return "🔥 爆量演出" if ratio > 2.0 else \
               "💤 交易冷清" if ratio < 0.7 else "⚖️ 動能正常"

    @classmethod
    def render_single_vol(cls, data):
        """單一標的：垂直詳細成交量分析"""
        ratio = data.volume_ratio
        status = cls.get_vol_status(ratio)
        
        print("-" * 45)
        print(f"📊 [成交量分析] {data.name} ({data.ticker})")
        print("-" * 45)
        print(f"  今日成交量: {data.latest_volume:,.0f} 股")
        print(f"  10日平均量: {data.avg_volume_10d:,.0f} 股")
        print(f"  量能噴發比: {ratio:.2f}x")
        print(f"  動能診斷: {status}")
        print("-" * 45 + "\n")

    @classmethod
    def render_comparison_vol(cls, data_list):
        """比較模式：成交量動能橫向表格"""
        # 排序：由動能最強到最弱排序 (看誰在爆量)
        sorted_list = sorted(data_list, key=lambda x: x.volume_ratio or 0, reverse=True)
        
        print("\n" + "═" * 95)
        print(f"📈 [ETF 量能噴發比較模式] 共 {len(data_list)} 檔標的")
        print("─" * 95)
        print(f"{'代碼':<12} | {'今日成交量':>15} | {'10日均量':>15} | {'量能比':>10} | {'動能診斷'}")
        print("─" * 95)
        
        for i, data in enumerate(sorted_list):
            ratio = data.volume_ratio
            status = cls.get_vol_status(ratio)
            
            # 視覺強化：標註爆量冠軍
            extrema = ""
            if i == 0 and ratio > 1.5:
                extrema = " 🏆 [今日人氣王]"
            
            print(f"{data.ticker:<12} | {data.latest_volume:>15,.0f} | {data.avg_volume_10d:>15,.0f} | {ratio:>9.2f}x | {status}{extrema}")
            
        print("═" * 95)
        print("💡 提示：量能噴發比 > 1.0 代表今日成交量高於平均；> 2.0 屬於顯著爆量。\n")
    
    # core/renderer.py

    @classmethod
    def render_dividends(cls, ticker: str, div_list: list):
        """渲染配息歷史列表"""
        print(f"\n" + "═" * 40)
        print(f"📅 {ticker} 歷史配息紀錄 (最近 {len(div_list)} 筆)")
        print("─" * 40)
        print(f"{'除息日期':<15} | {'配息金額':>10}")
        print("─" * 40)
        
        if not div_list:
            print(f"{'尚無配息資料':^40}")
        else:
            for d in div_list:
                print(f"{d['date']:<15} | {d['amount']:>10.4f}")
        
        print("═" * 40 + "\n")
        # 在 render_dividends 結尾加入

        if len(div_list) >= 2:
            # 簡單計算兩次配息之間的天數
            import datetime
            d1 = datetime.datetime.strptime(div_list[0]['date'], '%Y-%m-%d')
            d2 = datetime.datetime.strptime(div_list[1]['date'], '%Y-%m-%d')
            days_diff = abs((d1 - d2).days)
            
            if 25 <= days_diff <= 35:
                freq = "月配息 (Monthly)"
            elif 80 <= days_diff <= 100:
                freq = "季配息 (Quarterly)"
            elif 170 <= days_diff <= 190:
                freq = "半年配 (Semi-Annually)"
            elif 350 <= days_diff <= 380:
                freq = "年配息 (Annually)"
            else:
                freq = "不定期配息"
                
            print(f"💡 配息頻率觀測：此標的近期表現趨近於「{freq}」。")