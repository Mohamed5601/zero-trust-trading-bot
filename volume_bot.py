import pandas as pd
import pandas_ta as ta

class VolumeBot:
    def __init__(self, dataframe):
        self.df = dataframe
        
    def get_confirmation_score(self):
        volume_sma = ta.sma(self.df['Volume'], length=20)
        obv = ta.obv(self.df['Close'], self.df['Volume'])
        
        current_volume = self.df['Volume'].iloc[-1]
        current_vol_sma = volume_sma.iloc[-1]
        
        # حماية من القسمة على صفر
        if pd.isna(current_vol_sma) or current_vol_sma == 0: return 50
        
        price_change = self.df['Close'].pct_change().iloc[-1]
        obv_change = obv.pct_change().iloc[-1]
        
        score = 50
        
        if current_volume > (current_vol_sma * 1.5): score += 20
        elif current_volume < (current_vol_sma * 0.5): score -= 10
            
        if price_change > 0 and obv_change > 0: score += 15
        elif price_change > 0 and obv_change < 0: score -= 20
        elif price_change < 0 and obv_change < 0: score -= 10
            
        high = self.df['High'].iloc[-1]
        low = self.df['Low'].iloc[-1]
        candle_range = high - low
        atr = ta.atr(self.df['High'], self.df['Low'], self.df['Close'], length=14).iloc[-1]
        
        if candle_range > atr: score += 10
        
        return round(max(0, min(100, score)), 2)