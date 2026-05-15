import ccxt  
import pandas as pd
import requests
import time
from datetime import datetime
import csv
import os
import warnings

# تجاهل التحذيرات غير الضرورية
warnings.filterwarnings('ignore')

# استدعاء الملفات (تأكد من وجودها في نفس المجلد)
from general_bot import GeneralBot
from sniper_bot import SniperBot
from volume_bot import VolumeBot
from risk_bot import RiskBot
from ai_agent import AIAgent

# ==========================================
# ⚙️ إعدادات الرادار والفلاتر الخاصة
# ========================================== 
# يجب أن تكون هذه القائمة مطابقة لقائمة config.py إذا كنت ستشغل الملف بمفرده
SYMBOLS = [
     "STX/USDT", 'SOLUSDT' 
]

# 👇 فلاترك الخاصة (لن يرسل البوت إلا إذا تحققت هذه الأرقام)
MY_MIN_AI_SCORE = 0      # أقل نسبة ذكاء اصطناعي مقبولة
MY_MIN_VOLUME = 0        # أقل قوة سيولة مقبولة
MY_MIN_SNIPER = 0        # أقل درجة قنص (دخول) مقبولة
MY_MIN_TREND = 0         # أقل قوة ترند مقبولة

TIMEFRAME = '15m'
TELEGRAM_TOKEN = "YOUR_KEY_HERE" # من config.py
TELEGRAM_CHAT_ID = "YOUR_KEY_HERE" # من config.py
BUY_THRESHOLD = 60 # درجة الدخول الكلية

# التعديل: تفعيل وضع التداول الفوري (Spot) حصراً
exchange = ccxt.bybit({
    'enableRateLimit': True,
    'options': {
        'defaultType': 'spot' 
    }
})

# ==========================================
# 🔧 دوال النظام
# ==========================================

def send_telegram(message):
    """ دالة لإرسال رسائل تيليجرام """
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"⚠️ Telegram Error: {e}")

def log_to_csv(data_dict):
    """ دالة لتسجيل البيانات في ملف Journal """
    file_exists = os.path.isfile('trading_journal.csv')
    try:
        with open('trading_journal.csv', 'a', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Time', 'Symbol', 'Price', 'Score', 'Decision', 'Trend', 'Sniper', 'Volume', 'AI', 'Risk_Status', 'Exp_Duration']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if not file_exists: writer.writeheader()
            writer.writerow(data_dict)
    except Exception as e:
        print(f"⚠️ CSV Error: {e}")

def get_data(symbol):
    """ جلب بيانات الشموع من المنصة """
    try:
        bars = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=500)
        df = pd.DataFrame(bars, columns=['Time', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df['Time'] = pd.to_datetime(df['Time'], unit='ms')
        df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
        return df
    except Exception as e:
        print(f"❌ Connection Error {symbol}: {e}")
        return pd.DataFrame()

def analyze_symbol(symbol):
    """ الوظيفة الرئيسية: تحليل الرمز وإصدار القرار """
    try:
        df = get_data(symbol)
        if df.empty or len(df) < 50: return

        current_price = df['Close'].iloc[-1]
        
        # 1. تجميع نتائج البوتات الخمسة
        try:
            general = GeneralBot(df)
            trend_score = general.get_trend_score()
            
            sniper = SniperBot(df)
            entry_score = sniper.get_entry_score()
            
            volume = VolumeBot(df)
            vol_score = volume.get_confirmation_score()
            
            ai = AIAgent(df)
            ai_score = ai.get_ai_score()
            
            risk = RiskBot(df)
            risk_metrics = risk.get_risk_metrics()
            risk_score = risk_metrics['score']
            
        except Exception as e:
            print(f"❌ Error inside bots logic for {symbol}: {e}")
            return

        # 2. حساب الدرجة النهائية
        final_score = (trend_score * 0.30) + (ai_score * 0.30) + (entry_score * 0.25) + (vol_score * 0.15)
        final_score = round(final_score, 2)
        
        # 3. منطق القرار والفلترة
        decision = "WAIT ⏳"
        is_safe = True
        
        if final_score >= 80:
            emoji = "💎🔥"
            signal_strength = "STRONG BUY"
        elif final_score >= BUY_THRESHOLD:
            emoji = "✅⚡"
            signal_strength = "BUY SIGNAL"
        else:
            emoji = "💤"
            signal_strength = "WAIT"

        if risk_score < 30:
            decision = "⛔ RISK BLOCK"
            final_score = 0 
            is_safe = False
        
        # طباعة التقرير في التيرمينال للمتابعة
        print(f"📊 {symbol:<10} | Score: {final_score:<5} | AI: {ai_score}% | Sniper: {entry_score}% | Vol: {vol_score}%")
        
        # 4. تسجيل البيانات
        log_data = {
            'Time': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'Symbol': symbol,
            'Price': current_price, 'Score': final_score, 'Decision': signal_strength,
            'Trend': trend_score, 'Sniper': entry_score, 'Volume': vol_score, 
            'AI': ai_score, 'Risk_Status': risk.get_advice(risk_metrics),
            'Exp_Duration': risk_metrics.get('expected_duration', 0)
        }
        log_to_csv(log_data)
        
        # 5. بناء وإرسال الرسالة الشاملة (مع تطبيق الفلترة الصارمة)
        
        # --- 🛡️ الفلترة الخاصة بك (Custom Filters Logic) ---
        # هذا الشرط يتأكد من أن كل مؤشر لوحده محقق الرقم اللي انت عايزه
        passes_my_filters = (
            ai_score >= MY_MIN_AI_SCORE and
            vol_score >= MY_MIN_VOLUME and
            entry_score >= MY_MIN_SNIPER and
            trend_score >= MY_MIN_TREND
        )

        # التحقق النهائي: الدرجة الكلية + الأمان + فلاترك الخاصة
        if final_score >= BUY_THRESHOLD and is_safe and passes_my_filters:
            
            roi = ((risk_metrics['take_profit'] - risk_metrics['current_price']) / risk_metrics['current_price']) * 100
            
            # حساب نسبة المخاطرة للعائد
            rr_ratio = risk_metrics.get('risk_reward_ratio', 0)
            
            msg = f"""
{emoji} *SPOT SIGNAL: {symbol}* {emoji}
───────────────────
🎯 *QUICK ACTION (للمبتدئين):*
🛒 *Buy Now:* ${risk_metrics['current_price']}
✅ *Target:* ${risk_metrics['take_profit']} (+{roi:.2f}%)
🛑 *Stop Loss:* ${risk_metrics['stop_loss']}

───────────────────
🧠 *ADVANCED DATA (للمحللين):*
🏆 *Total Score:* `{final_score}/100` ({signal_strength})

📊 *Technical Breakdown:*
🤖 *AI Confidence:* `{ai_score}%`
🔫 *Sniper Entry:* `{entry_score}%` (Timing)
🌊 *Volume Strength:* `{vol_score}%`
📈 *Trend Power:* `{trend_score}%`

⚖️ *Risk Analysis:*
• R:R Ratio: `1:{rr_ratio}`
• Market State: `{risk_metrics.get('market_state', 'Normal')}`
• Volatility (ATR): `{risk_metrics.get('current_atr', 0):.4f}`

⏳ *Time Factors (معدّل):*
• Exp. Duration: ~{int(risk_metrics.get('expected_duration', 0) * 1.5)} mins
• Max Hold: {int(risk_metrics.get('max_hold_time', 0) * 1.5)} mins

⚠️ *System Advice:* {risk.get_advice(risk_metrics)}
───────────────────
            """
            send_telegram(msg)
            
            print(f"✅ TELEGRAM ALERT SENT FOR {symbol}")
            
            return {
                "is_signal": True,
                "symbol": symbol,
                "score": final_score,
                "ai_score": ai_score,
                "trend_score": trend_score,
                "vol_score": vol_score,
                "entry_score": entry_score,
                "target": risk_metrics['take_profit'],
                "stop_loss": risk_metrics['stop_loss']
            }
            
        # إذا لم يتحقق الشرط، نرجع إشارة كاذبة
        return {"is_signal": False}
            
    except Exception as e:
        print(f"❌ Critical Error analyzing {symbol}: {e}")
        return {"is_signal": False}

# ===============================================
# 🛡️ نقطة البداية (Entry Point) لمنع التعارضات
# ===============================================

def start_standalone_scanner():
    """ تبدأ حلقة الفحص الأبدية لملف analysis_bot.py بمفرده (للاختبار/المراقبة). """
    print(f"📡 STANDALONE SCANNER ACTIVATED")
    send_telegram(f"🟢 *STANDALONE SCANNER ONLINE*\n🎯 Threshold: > {BUY_THRESHOLD}%")
    try:
        while True:
            print("\n" + "="*50)
            print(f"🕒 Scan Cycle: {datetime.now().strftime('%H:%M:%S')}")
            # حلقة الفحص تستدعي دالة analyze_symbol
            for sym in SYMBOLS:
                analyze_symbol(sym)
                time.sleep(0.5) 
            print("="*50)
            time.sleep(30) 
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped.")


if __name__ == "__main__":
    start_standalone_scanner()
