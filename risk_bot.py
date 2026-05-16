import pandas as pd
import pandas_ta as ta
import math  # ضرورية جداً للمعادلات الجديدة

class RiskBot:
    def __init__(self, dataframe):
        self.df = dataframe
        # تثبيت الفريم الزمني بـ 15 دقيقة لحساب الزمن
        self.timeframe_minutes = 5 
        
    def get_risk_metrics(self):
        # 1. حساب متوسط التذبذب (ATR)
        atr = ta.atr(self.df['High'], self.df['Low'], self.df['Close'], length=14)
        current_price = self.df['Close'].iloc[-1]
        
        # حماية من البيانات الفارغة
        if atr is None or pd.isna(atr.iloc[-1]):
            current_atr = current_price * 0.01
        else:
            current_atr = atr.iloc[-1]
            
        # متوسط الـ ATR لفترة أطول
        avg_atr = atr.rolling(window=50).mean().iloc[-1] if not pd.isna(atr.iloc[-1]) else current_atr

        # 2. تحديد الستوب والهدف (المنطق الديناميكي)
        stop_loss_dist = current_atr * 1.5
        stop_loss = current_price - stop_loss_dist
        risk_per_share = current_price - stop_loss
        
        # تحديد النسبة: 1:2 لو السوق قوي، 1:1.5 لو السوق ضعيف
        if current_atr > avg_atr:
            target_ratio = 2.0
            market_state = "🔥 Strong"
        else:
            target_ratio = 1.5
            market_state = "💤 Slow"
            
        take_profit = current_price + (risk_per_share * target_ratio)
        
        # 3. === الميزة الجديدة: حساب الزمن المتوقع (معامل الواقعية) ===
        dist_to_target = take_profit - current_price
        
        # التعديل هنا: معامل الواقعية (1.5 بدلاً من 1.1)
        if current_atr > 0:
            candles_needed = (dist_to_target / current_atr) * 1.5  
        else:
            candles_needed = 2 
        
        expected_candles = max(2, math.ceil(candles_needed))
        expected_time_mins = expected_candles * self.timeframe_minutes
        
        # التعديل هنا: ضرب Max Hold Time في 1.5 أيضاً
        max_hold_time = expected_time_mins * 2  
        
        # 4. الحسابات النهائية لنسبة الربح للمخاطرة
        reward_per_share = take_profit - current_price
        rr_ratio = reward_per_share / risk_per_share if risk_per_share > 0 else 0.0
        
        # إضافة نسبة العائد المئوية (ROI %)
        roi_percentage = ((take_profit - current_price) / current_price) * 100

        # تقييم المخاطرة (Score)
        risk_score = 50
        if current_atr > (avg_atr * 1.5): risk_score -= 20
        elif current_atr < (avg_atr * 0.5): risk_score -= 10
        else: risk_score += 20
            
        return {
            "score": round(max(0, min(100, risk_score)), 2),
            "current_price": round(current_price, 4),
            "current_atr": round(current_atr, 4), # أضفنا ATR لعرضه في التقرير الشامل
            "stop_loss": round(stop_loss, 4),
            "take_profit": round(take_profit, 4),
            "risk_reward_ratio": round(rr_ratio, 2),
            "market_state": market_state,
            "expected_candles": expected_candles,
            "expected_duration": expected_time_mins, 
            "max_hold_time": max_hold_time,
            "roi_pct": round(roi_percentage, 2) # نسبة العائد المئوية
        }
        
    def get_advice(self, metrics):
        score = metrics['score']
        advice = ""
        
        if score >= 60: advice = "Safe ✅"
        elif score <= 30: advice = "Danger ⛔"
        else: advice = "Moderate ⚠️"
        
        # إضافة نصيحة الوقت
        time_advice = f" | Exp Time: {metrics['expected_duration']}m"
        
        return advice + time_advice
