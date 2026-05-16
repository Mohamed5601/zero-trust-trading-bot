import ccxt
import pandas as pd
import pandas_ta as ta
import requests
import time
import warnings
import sys

# تجاهل التحذيرات غير المهمة
warnings.filterwarnings("ignore")

# ==========================================
# 🔗 ربط بوت التحليل العميق
# ==========================================
try:
    # نقوم باستيراد دالة التحليل من الملف الثاني
    # ملاحظة: تأكد أنك قمت بتسمية الملف الثاني: analysis_bot.py
    from analysis_bot import analyze_symbol
    print("✅ تم ربط بوت التحليل (5 Bots) بنجاح!")
except ImportError:
    print("❌ خطأ: لم يتم العثور على ملف 'analysis_bot.py'")
    print("⚠️ يرجى تغيير اسم ملف '5_bots_working.py' إلى 'analysis_bot.py' ليعمل النظام.")
    sys.exit()
except SyntaxError:
    print("❌ خطأ في الاسم: لا يمكن لبايثون قراءة ملف يبدأ برقم.")
    print("⚠️ يرجى تغيير اسم ملف '5_bots_working.py' إلى 'analysis_bot.py'")
    sys.exit()

# --- 1. إعدادات التليجرام ---
TELEGRAM_TOKEN = "8464093213:AAGUE7q_ZdzeSLC_INsgR35bvWa8HkfrB9s"
TELEGRAM_CHAT_ID = "-1003484158830"

# --- 2. إعداد الاتصال بالمنصة ---
exchange = ccxt.binance({
    'options': {'defaultType': 'future'},
    'enableRateLimit': True
})

# دالة إرسال الرسائل
def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"⚠️ Error sending msg: {e}")

# دالة جلب أقوى العملات سيولة
def get_top_volume_coins(limit=30):
    print("🔄 تحديث قائمة السيولة...")
    try:
        tickers = exchange.fetch_tickers()
        pairs = []
        for symbol, ticker in tickers.items():
            if '/USDT' in symbol and 'USDC' not in symbol and '_' not in symbol:
                vol = ticker.get('quoteVolume')
                if vol:
                    pairs.append((symbol, vol))
        
        pairs.sort(key=lambda x: x[1], reverse=True)
        return [p[0] for p in pairs[:limit]]
    except Exception as e:
        print(f"Error tickers: {e}")
        return []

# --- 3. الدماغ المحلل (الذكاء + التوقع) ---
def analyze_coin(symbol):
    try:
        # نجلب آخر 100 شمعة ساعة
        bars = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=100)
        if not bars: return None

        df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        
        # --- المؤشرات ---
        df['rsi'] = ta.rsi(df['close'], length=14)
        df['ema_50'] = ta.ema(df['close'], length=50)
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        
        current = df.iloc[-1]
        prev = df.iloc[-2]
        
        # فلتر السعر: هل بدأت الحركة؟
        price_change = ((current['close'] - prev['close']) / prev['close']) * 100
        
        if not (0.2 <= price_change <= 3.5):
            return None 

        atr_value = current['atr']
        projected_move = atr_value * 2.5 
        
        target_price = current['close'] + projected_move
        potential_gain_percent = ((target_price - current['close']) / current['close']) * 100
        
        # حساب نسبة الثقة
        confidence = 0
        vol_avg = df['volume'].rolling(20).mean().iloc[-1]
        if current['volume'] > vol_avg: confidence += 30
        elif current['volume'] > (vol_avg * 0.7): confidence += 15
            
        if current['close'] > current['ema_50']: confidence += 20
            
        if 50 <= current['rsi'] <= 70: confidence += 20
        elif current['rsi'] < 50: confidence += 10
            
        candle_range = current['high'] - current['low']
        if candle_range > 0:
            close_pos = (current['close'] - current['low']) / candle_range
            if close_pos > 0.7: confidence += 30
            elif close_pos > 0.5: confidence += 15

        if confidence >= 50:
            return {
                'symbol': symbol,
                'price': current['close'],
                'change': price_change,
                'confidence': confidence,
                'potential_gain': potential_gain_percent,
                'target': target_price,
                'rsi': current['rsi']
            }
        
        return None

    except Exception as e:
        return None

# --- 4. الرادار المتكامل ---
def start_radar():
    print(f"🦅 رادار عين الصقر + لجنة التحليل (AI Full Mode) يعمل...")
    send_telegram_msg("🦅 *تم دمج الأنظمة!* \nالرادار يبحث، وبوت التحليل ينتظر الإشارة...")
    
    processed_coins = [] 

    while True:
        try:
            coins = get_top_volume_coins(limit=80)
            print(f"🔎 فحص {len(coins)} عملة...")
            
            for symbol in coins:
                time.sleep(2) 
                
                data = analyze_coin(symbol) 
                
                # إذا وجدنا فرصة ولم نرسلها من قبل
                if data and symbol not in processed_coins:
                    
                    # 1. إرسال تنبيه الرادار (الخطوة الأولى)
                    if data['confidence'] >= 80: conf_icon = "🔥 قوة قصوى"
                    elif data['confidence'] >= 65: conf_icon = "✅ قوية"
                    else: conf_icon = "🤔 متوسطة"
                    
                    msg = (
                        f"🦅 **رصد فرصة ذكية!**\n"
                        f"💎 **العملة:** `{symbol}`\n"
                        f"💰 **السعر:** `{data['price']}`\n"
                        f"📈 **التحرك:** {data['change']:.2f}%\n"
                        f"🔮 **التوقع:** `+{data['potential_gain']:.2f}%`\n"
                        f"🛡 **الثقة:** {data['confidence']}% ({conf_icon})\n"
                        f"⏳ **جاري تحويلها للتحليل العميق...**"
                    )
                    
                    print(f"Found: {symbol} | Triggering Deep Analysis...")
                    send_telegram_msg(msg)
                    processed_coins.append(symbol)
                    
                    # 2. تشغيل البوت الثاني أوتوماتيكياً (الخطوة الثانية)
                    print(f"⚙️ تشغيل لجنة التحليل (5 Bots) على: {symbol}")
                    print("-" * 40)
                    try:
                        # هنا يتم استدعاء دالة التحليل من الملف الآخر فوراً
                        analyze_symbol(symbol)
                    except Exception as e:
                        print(f"❌ خطأ أثناء تشغيل التحليل العميق: {e}")
                    print("-" * 40)

            if len(processed_coins) > 50:
                processed_coins.clear()
            
            print("💤 استراحة 60 ثانية...")
            time.sleep(30)
            
        except Exception as e:
            print(f"Error Loop: {e}")
            time.sleep(30)

if __name__ == "__main__":
    start_radar()