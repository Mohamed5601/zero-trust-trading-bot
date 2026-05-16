import pandas as pd
import pandas_ta as ta

class GeneralBot:
    def __init__(self, dataframe):
        self.df = dataframe
        
    def get_trend_score(self):
        # سكالبينج: متوسطات سريعة (20 و 50)
        ema_fast = ta.ema(self.df['Close'], length=20)
        ema_slow = ta.ema(self.df['Close'], length=50)
        adx = ta.adx(self.df['High'], self.df['Low'], self.df['Close'], length=14)
        
        if ema_fast is None or ema_slow is None or adx is None:
            return 50

        current_price = self.df['Close'].iloc[-1]
        last_ema_fast = ema_fast.iloc[-1]
        last_ema_slow = ema_slow.iloc[-1]
        
        current_adx = 0
        if not adx.empty and 'ADX_14' in adx.columns:
            current_adx = adx['ADX_14'].iloc[-1]
            if pd.isna(current_adx): current_adx = 0
        
        score = 50 
        
        # تقاطع المتوسطات
        if last_ema_fast > last_ema_slow:
            score += 10
            if current_price > last_ema_fast:
                score += 10
            if current_adx > 25:
                score += (current_adx / 2) 
                
        elif last_ema_fast < last_ema_slow:
            score -= 10
            if current_price < last_ema_fast:
                score -= 10
            if current_adx > 25:
                score -= (current_adx / 2)
        
        return round(max(0, min(100, score)), 2)