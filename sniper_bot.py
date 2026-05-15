import pandas as pd
import pandas_ta as ta

class SniperBot:
    def __init__(self, dataframe):
        self.df = dataframe
        
    def get_entry_score(self):
        rsi = ta.rsi(self.df['Close'], length=14)
        stoch = ta.stoch(self.df['High'], self.df['Low'], self.df['Close'])
        # استخدام iloc لتجنب أخطاء الأسماء
        stoch_k = stoch.iloc[:, 0] 
        bb = ta.bbands(self.df['Close'], length=20, std=2)
        lower_band = bb.iloc[:, 0]
        upper_band = bb.iloc[:, 2]
        
        current_price = self.df['Close'].iloc[-1]
        
        # حماية من البيانات الناقصة
        if pd.isna(current_price): return 50
        current_rsi = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
        current_stoch_k = stoch_k.iloc[-1] if not pd.isna(stoch_k.iloc[-1]) else 50
        current_lower_bb = lower_band.iloc[-1] if not pd.isna(lower_band.iloc[-1]) else current_price
        current_upper_bb = upper_band.iloc[-1] if not pd.isna(upper_band.iloc[-1]) else current_price
        
        score = 50
        
        # سكالبينج: RSI تحت 40 يعتبر فرصة
        if current_rsi < 40: score += 20
        elif current_rsi > 70: score -= 20
        else:
            if current_rsi < 50: score += 5
            else: score -= 5
            
        if current_stoch_k < 20: score += 15 
        elif current_stoch_k > 80: score -= 15 
            
        if current_price <= current_lower_bb: score += 15
        elif current_price >= current_upper_bb: score -= 15
            
        return round(max(0, min(100, score)), 2)