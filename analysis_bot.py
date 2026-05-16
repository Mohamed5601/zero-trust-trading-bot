import ccxt
import pandas as pd
import requests
import time
from datetime import datetime
import csv
import os
import sqlite3
import warnings

# تجاهل التحذيرات غير الضرورية
warnings.filterwarnings('ignore')

# استدعاء الملفات (تأكد من وجودها في نفس المجلد)
from general_bot import GeneralBot
from sniper_bot import SniperBot
from volume_bot import VolumeBot
from risk_bot import RiskBot
from ai_agent import AIAgent
from config import DB_NAME, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, TRADE_AMOUNT_USDT

# ==========================================
# ⚙️ إعدادات الرادار والفلاتر
# ==========================================
SYMBOLS = [
     'SOL/USDT', 'BTC/USDT', 'ETH/USDT', 'XRP/USDT', 'BNB/USDT'
]

# الفلاتر الصارمة (لن يرسل البوت إلا إذا تحققت)
MY_MIN_AI_SCORE = 50       # الذكاء الاصطناعي يجب أن يكون محايداً أو إيجابياً
MY_MIN_SNIPER = 40         # لا تدخل إذا كان السعر متضخماً جداً
BUY_THRESHOLD = 60         # الدرجة النهائية المطلوبة للدخول (تم تعديلها لتناسب الـ 5 مؤشرات)

TIMEFRAME = '15m'

# إعداد المنصة (Spot للتداول الآمن)
exchange = ccxt.binance({
    'enableRateLimit': True,
    'options': {'defaultType': 'spot'}
})

# تتبع الصفقات المفتوحة
positions = {}  # symbol: {'entry_price': float, 'amount': float, 'tp': float, 'sl': float, 'entry_time': str, 'fee_entry': float}

# تتبع الرصيد لكل رمز (بالدولار)
balances = {symbol: TRADE_AMOUNT_USDT for symbol in SYMBOLS}

def log_trade_to_csv(trade_data):
    file_exists = os.path.isfile('trades_log.csv')
    try:
        with open('trades_log.csv', 'a', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Symbol', 'Entry_Time', 'Entry_Price', 'Amount', 'TP', 'SL', 'Fee_Entry', 'Exit_Time', 'Exit_Price', 'Fee_Exit', 'Profit_Loss', 'Balance']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if not file_exists: writer.writeheader()
            writer.writerow(trade_data)
    except Exception as e:
        print(f"⚠️ Trade CSV Error: {e}")

# ==========================================
# 🔧 دوال النظام
# ==========================================

def get_db_connection():
    """ إنشاء اتصال آمن بقاعدة البيانات لقراءة بيانات الحيتان """
    try:
        conn = sqlite3.connect(DB_NAME, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"⚠️ DB Connection Error: {e}")
        return None

def get_whale_score_from_db(symbol):
    """
    سحب بيانات الحيتان (L/S Ratio, Funding, OI) وتحويلها لدرجة من 0-100
    """
    score = 50 # درجة محايدة مبدئياً
    market_state = "Neutral"
    
    conn = get_db_connection()
    if not conn:
        return 50, "DB Error"

    try:
        cursor = conn.cursor()
        # تنظيف الرمز ليتطابق مع تخزين قاعدة البيانات (مثلاً STX/USDT -> STXUSDT)
        clean_symbol = symbol.replace('/', '')
        
        # سحب أحدث قراءة
        cursor.execute("""
            SELECT * FROM market_metrics 
            WHERE symbol = ? 
            ORDER BY timestamp DESC LIMIT 1
        """, (clean_symbol,))
        
        row = cursor.fetchone()
        
        if row:
            ls_ratio = row['long_short_ratio']
            funding = row['funding_rate']
            
            # --- منطق تقييم الحيتان ---
            
            # 1. تحليل نسبة اللونج/شورت (وزن كبير)
            if ls_ratio > 1.2: 
                score += 15  # تفاؤل
            elif ls_ratio > 2.0:
                score += 25  # تفاؤل قوي جداً (انتبه من الانعكاس أحياناً)
            elif ls_ratio < 0.8:
                score -= 15  # تشاؤم
                
            # 2. معدل التمويل (Funding Rate)
            # إيجابي يعني اللونج يدفع للشورت (طلب شراء عالي)
            if funding > 0.005: 
                score += 10
            elif funding < 0:
                score -= 10
            
            # تحديد حالة الحيتان للنص
            if score >= 65: market_state = "Whales Buying 🟢"
            elif score <= 35: market_state = "Whales Selling 🔴"
            else: market_state = "Neutral ⚖️"
            
        else:
            # لو مفيش داتا، نرجع محايد
            market_state = "No Data 🤷‍♂️"
            
    except Exception as e:
        print(f"⚠️ Whale Data Error: {e}")
    finally:
        conn.close()
        
    return max(0, min(100, score)), market_state

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"⚠️ Telegram Error: {e}")

def log_to_csv(data_dict):
    file_exists = os.path.isfile('trading_journal.csv')
    try:
        with open('trading_journal.csv', 'a', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Time', 'Symbol', 'Price', 'Score', 'Decision', 'Trend', 'Sniper', 'Volume', 'AI', 'Whale', 'Risk_Status']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if not file_exists: writer.writeheader()
            writer.writerow(data_dict)
    except Exception as e:
        print(f"⚠️ CSV Error: {e}")

def get_data(symbol):
    try:
        bars = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=200) # زيادة العدد لدقة الـ EMA
        df = pd.DataFrame(bars, columns=['Time', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df['Time'] = pd.to_datetime(df['Time'], unit='ms')
        return df
    except Exception as e:
        print(f"❌ Connection Error {symbol}: {e}")
        return pd.DataFrame()

def analyze_symbol(symbol):
    """ الوظيفة الرئيسية: تحليل الرمز وإصدار القرار """
    print(f"🔍 Analyzing {symbol}...")
    try:
        df = get_data(symbol)
        if df.empty or len(df) < 50: return {"is_signal": False}

        current_price = df['Close'].iloc[-1]
        
        # 1. استدعاء البوتات
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
            
            # --- الجديد: استدعاء الحيتان ---
            whale_score, whale_state = get_whale_score_from_db(symbol)
            
        except Exception as e:
            print(f"❌ Error inside bots logic for {symbol}: {e}")
            return {"is_signal": False}

        # 2. حساب الدرجة النهائية (الأوزان الجديدة المتفق عليها)
        # Trend 25%, AI 25%, Sniper 25%, Volume 15%, Whale 10%
        final_score = (trend_score * 0.25) + \
                      (ai_score * 0.25) + \
                      (entry_score * 0.25) + \
                      (vol_score * 0.15) + \
                      (whale_score * 0.10)
                      
        final_score = round(final_score, 2)
        
        # 3. منطق القرار والفلترة
        decision = "WAIT ⏳"
        is_safe = True
        signal_strength = "WAIT"
        emoji = "💤"

        if final_score >= 85:
            emoji = "💎🚀"
            signal_strength = "STRONG BUY"
        elif final_score >= BUY_THRESHOLD:
            emoji = "✅⚡"
            signal_strength = "BUY SIGNAL"

        if risk_score < 30:
            decision = "⛔ RISK BLOCK"
            final_score = 0 
            is_safe = False
        
        # طباعة التقرير المصغر
        print(f"📊 {symbol:<10} | Sc: {final_score:<5} | AI: {ai_score}% | Wh: {whale_score}% ({whale_state})")
        
        # 4. تسجيل البيانات
        log_data = {
            'Time': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'Symbol': symbol,
            'Price': current_price, 'Score': final_score, 'Decision': signal_strength,
            'Trend': trend_score, 'Sniper': entry_score, 'Volume': vol_score, 
            'AI': ai_score, 'Whale': whale_score, 'Risk_Status': risk.get_advice(risk_metrics)
        }
        log_to_csv(log_data)
        
        # 5. الفلترة والإرسال
        passes_my_filters = (
            ai_score >= MY_MIN_AI_SCORE and
            entry_score >= MY_MIN_SNIPER
        )

        if final_score >= BUY_THRESHOLD and is_safe and passes_my_filters:
            
            if symbol in positions:
                # Already in position, log but don't enter
                log_data['Decision'] = 'SKIP - Already in Position'
                log_to_csv(log_data)
                return {"is_signal": False}
            
            # Simulate buy
            amount = TRADE_AMOUNT_USDT / current_price
            fee_entry = TRADE_AMOUNT_USDT * 0.001  # 0.1% on entry value
            balances[symbol] -= TRADE_AMOUNT_USDT
            positions[symbol] = {
                'entry_price': current_price,
                'amount': amount,
                'tp': risk_metrics['take_profit'],
                'sl': risk_metrics['stop_loss'],
                'entry_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'fee_entry': fee_entry
            }
            # Log entry
            trade_data = {
                'Symbol': symbol,
                'Entry_Time': positions[symbol]['entry_time'],
                'Entry_Price': current_price,
                'Amount': amount,
                'TP': risk_metrics['take_profit'],
                'SL': risk_metrics['stop_loss'],
                'Fee_Entry': fee_entry,
                'Exit_Time': '',
                'Exit_Price': '',
                'Fee_Exit': '',
                'Profit_Loss': '',
                'Balance': balances[symbol]
            }
            log_trade_to_csv(trade_data)
            
            roi = ((risk_metrics['take_profit'] - current_price) / current_price) * 100
            rr_ratio = risk_metrics.get('risk_reward_ratio', 0)
            
            msg = f"""
{emoji} *INTEGRATED SIGNAL: {symbol}*
───────────────────
🎯 *ACTION PLAN:*
🛒 *Entry:* ${current_price}
✅ *Target:* ${risk_metrics['take_profit']} (+{roi:.8f}%)
🛑 *Stop:* ${risk_metrics['stop_loss']}

───────────────────
🧠 *DECISION MATRIX:*
🏆 *Final Score:* `{final_score}/100`

• 🐳 *Whales:* `{whale_score}%` ({whale_state})
• 🤖 *AI Model:* `{ai_score}%`
• 🔫 *Timing:* `{entry_score}%`
• 🌊 *Volume:* `{vol_score}%`
• 📈 *Trend:* `{trend_score}%`

⚖️ *RISK MGMT:*
• Ratio: `1:{rr_ratio}`
• Advice: {risk.get_advice(risk_metrics)}
───────────────────
            """
            send_telegram(msg)
            print(f"✅ ALERT SENT FOR {symbol}")
            
            return {
                "is_signal": True,
                "symbol": symbol,
                "score": final_score,
                "target": risk_metrics['take_profit'],
                "stop_loss": risk_metrics['stop_loss']
            }
            
        return {"is_signal": False}
            
    except Exception as e:
        print(f"❌ Critical Error analyzing {symbol}: {e}")
        return {"is_signal": False}

# ===============================================
# 🛡️ وضع التشغيل المنفصل (للاختبار)
# ===============================================

def start_standalone_scanner():
    print(f"📡 FULL INTEGRATED SYSTEM ONLINE")
    print(f"🎯 Threshold: {BUY_THRESHOLD} | Whale Integration: ACTIVE")
    
    # محاولة اختبار الاتصال بالقاعدة أولاً
    conn = get_db_connection()
    if conn:
        print("✅ Database Connection: OK")
        conn.close()
    else:
        print("❌ Database Connection: FAILED (Make sure collector.py is running)")
        
    try:
        while True:
            print("\n" + "="*50)
            print(f"🕒 Cycle: {datetime.now().strftime('%H:%M:%S')}")
            for sym in SYMBOLS:
                analyze_symbol(sym)
                time.sleep(1) 
            
            # Check for exits
            for sym in list(positions.keys()):
                try:
                    ticker = exchange.fetch_ticker(sym)
                    current_price = ticker['last']
                    pos = positions[sym]
                    if current_price >= pos['tp'] or current_price <= pos['sl']:
                        # Simulate sell
                        exit_price = current_price
                        fee_exit = pos['amount'] * exit_price * 0.001
                        profit_loss = (exit_price - pos['entry_price']) * pos['amount'] - pos['fee_entry'] - fee_exit
                        balances[sym] += (exit_price * pos['amount'] - fee_exit)
                        exit_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        # Update trade log
                        trade_data = {
                            'Symbol': sym,
                            'Entry_Time': pos['entry_time'],
                            'Entry_Price': pos['entry_price'],
                            'Amount': pos['amount'],
                            'TP': pos['tp'],
                            'SL': pos['sl'],
                            'Fee_Entry': pos['fee_entry'],
                            'Exit_Time': exit_time,
                            'Exit_Price': exit_price,
                            'Fee_Exit': fee_exit,
                            'Profit_Loss': profit_loss,
                            'Balance': balances[sym]
                        }
                        log_trade_to_csv(trade_data)
                        # Send telegram exit
                        msg = f"🚪 EXIT {sym}\nPrice: ${exit_price}\nP/L: ${profit_loss:.2f}"
                        send_telegram(msg)
                        # Remove position
                        del positions[sym]
                except Exception as e:
                    print(f"⚠️ Exit check error for {sym}: {e}")
            
            print("="*50)
            time.sleep(60) 
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped.")

if __name__ == "__main__":
    start_standalone_scanner()