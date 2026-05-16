import pandas as pd
import numpy as np
import pandas_ta as ta
from xgboost import XGBClassifier

class AIAgent:
    def __init__(self, dataframe):
        self.df = dataframe.copy()
        
    def prepare_features(self):
        df = self.df
        # Momentum & Trend
        df['RSI'] = ta.rsi(df['Close'], length=14)
        stoch = ta.stoch(df['High'], df['Low'], df['Close'])
        df['Stoch_K'] = stoch.iloc[:, 0]
        df['EMA_20'] = ta.ema(df['Close'], length=20)
        df['EMA_50'] = ta.ema(df['Close'], length=50)
        mac = ta.macd(df['Close'])
        df['MACD'] = mac.iloc[:, 0]
        
        # Volatility & Lags
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        bb = ta.bbands(df['Close'], length=20)
        df['BB_Width'] = (bb.iloc[:, 2] - bb.iloc[:, 0]) / bb.iloc[:, 1]
        
        df['Log_Ret'] = np.log(df['Close'] / df['Close'].shift(1))
        df['Lag_1'] = df['Log_Ret'].shift(1)
        df['Lag_2'] = df['Log_Ret'].shift(2)
        df['Vol_Change'] = df['Volume'].pct_change()
        
        # تنظيف البيانات (الخطوة الأهم)
        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        df.dropna(inplace=True)
        return df

    def get_ai_score(self):
        try:
            full_df = self.prepare_features()
            if len(full_df) < 50: return 50
                
            full_df['Target'] = (full_df['Close'].shift(-1) > full_df['Close']).astype(int)
            train_df = full_df[:-1]
            current_candle = full_df.iloc[[-1]]
            
            features = ['RSI', 'Stoch_K', 'EMA_20', 'EMA_50', 'MACD', 'ATR', 'BB_Width', 'Lag_1', 'Lag_2', 'Vol_Change']
            X = train_df[features]
            y = train_df['Target']
            
            model = XGBClassifier(n_estimators=100, max_depth=4, learning_rate=0.05, random_state=42, n_jobs=-1, eval_metric='logloss')
            model.fit(X, y)
            
            prediction_prob = model.predict_proba(current_candle[features])[0][1]
            return round(prediction_prob * 100, 2)
        except:
            return 50 # في حالة حدوث أي خطأ، نرجع محايد