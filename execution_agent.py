import ccxt
import time
import sys
from datetime import datetime

# استيراد إعداداتك الخاصة
from config import (
    BINANCE_API_KEY, BINANCE_SECRET_KEY, 
    TRADE_AMOUNT_USDT, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
)

# استيراد دوال التحليل والإشعارات
from analysis_bot import analyze_symbol
from notifier import send_telegram_msg

# ==========================================
# 🛡️ إعدادات الفلترة الصارمة (Quality Gate)
# ==========================================
# لن يتم تنفيذ أي صفقة إلا إذا حققت هذه الأرقام
MIN_TOTAL_SCORE = 75     # الدرجة النهائية
MIN_AI_CONFIDENCE = 60   # ثقة الذكاء الاصطناعي
MIN_TREND_POWER = 70     # قوة الاتجاه
MIN_VOLUME_STRENGTH = 70 # قوة السيولة
MIN_SNIPER_ENTRY = 50    # دقة الدخول

# ==========================================
# ⚙️ الاتصال بالمنصة (Real Account)
# ==========================================

exchange = ccxt.bybit({
    'apiKey': BINANCE_API_KEY,  
    'secret': BINANCE_SECRET_KEY, 
    'enableRateLimit': True,
    'options': {
        'defaultType': 'spot'
    }
})

def validate_signal(data):
    """
    وظيفة هذه الدالة هي تطبيق الفلاتر قبل دفع أي دولار.
    تعود بـ True إذا كانت الصفقة مثالية، و False إذا كانت ضعيفة.
    """
    reasons = []
    
    # 1. فلتر الدرجة الكلية
    if data['score'] < MIN_TOTAL_SCORE:
        reasons.append(f"Score low ({data['score']} < {MIN_TOTAL_SCORE})")
        
    # 2. فلتر الذكاء الاصطناعي (أهم فلتر)
    if data['ai_score'] < MIN_AI_CONFIDENCE:
        reasons.append(f"AI weak ({data['ai_score']}% < {MIN_AI_CONFIDENCE}%)")

    # 3. فلتر قوة الاتجاه
    if data['trend_score'] < MIN_TREND_POWER:
        reasons.append(f"Trend weak ({data['trend_score']}% < {MIN_TREND_POWER}%)")

    # 4. فلتر السيولة
    if data['vol_score'] < MIN_VOLUME_STRENGTH:
        reasons.append(f"Volume low ({data['vol_score']}% < {MIN_VOLUME_STRENGTH}%)")
        
    # 5. فلتر السنايبر
    if data['entry_score'] < MIN_SNIPER_ENTRY:
        reasons.append(f"Entry timing bad ({data['entry_score']}% < {MIN_SNIPER_ENTRY}%)")

    if reasons:
        print(f"❌ Signal Rejected for {data['symbol']}: {', '.join(reasons)}")
        return False
    
    return True

def execute_real_trade(symbol, data):
    """ تنفيذ أمر الشراء الحقيقي """
    try:
        print(f"🚀 EXECUTING BUY ORDER FOR {symbol}...")
        
        # 1. جلب السعر الحالي
        ticker = exchange.fetch_ticker(symbol)
        current_price = ticker['last']
        
        # 2. حساب الكمية بدقة
        # الكمية = المبلغ بالدولار / السعر
        amount = TRADE_AMOUNT_USDT / current_price
        
        # ضبط الكمية حسب قوانين باينانس (Precision)
        amount = exchange.amount_to_precision(symbol, amount)
        
        # -----------------------------------------------------
        # ⚠️ منطقة الخطر: هذا السطر ينفذ الشراء الحقيقي
        # لتعطيله وجعله وهمياً، ضع أمامه علامة #
        order = exchange.create_market_buy_order(symbol, amount)
        # -----------------------------------------------------
        
        # 3. حساب تفاصيل الصفقة للإشعار
        entry_price = order.get('average', current_price) if 'average' in order else current_price
        cost = float(amount) * float(entry_price)
        
        msg = f"""
✅ **ORDER FILLED (LIVE)**
🪙 **{symbol}**
💵 Cost: ${cost:.2f}
Price: ${entry_price}
Target: ${data['target']}
Stop: ${data['stop_loss']}
        """
        send_telegram_msg(msg)
        print(f"✅ Trade Successful: {symbol}")
        
    except Exception as e:
        err_msg = f"❌ Execution Failed for {symbol}: {e}"
        print(err_msg)
        send_telegram_msg(err_msg)

def start_execution_engine():
    """ المحرك الرئيسي الذي يربط التحليل بالتنفيذ """
    print("🛡️ Execution Agent Online with STRICT FILTERS")
    print(f"🎯 Filters: Score>{MIN_TOTAL_SCORE}, AI>{MIN_AI_CONFIDENCE}%, Vol>{MIN_VOLUME_STRENGTH}%")
    
    # قائمة العملات التي نراقبها (نفس قائمة الرادار)
    SYMBOLS = ['SOL/USDT', 'XRP/USDT', 'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SUI/USDT']
    
    while True:
        try:
            for symbol in SYMBOLS:
                # 1. الحصول على التحليل من البوت المحلل
                # (هذه الدالة ترسل رسالة التليجرام وتعيد البيانات لنا أيضاً)
                analysis_result = analyze_symbol(symbol)
                
                # 2. هل توجد إشارة شراء أصلاً؟
                if analysis_result and analysis_result.get('is_signal') == True:
                    
                    # 3. تطبيق الفلاتر الصارمة (Quality Gate)
                    if validate_signal(analysis_result):
                        # 4. التنفيذ إذا نجح في الاختبار
                        execute_real_trade(symbol, analysis_result)
                    else:
                        # إرسال تنبيه صامت للمطور (اختياري)
                        print(f"📉 {symbol} Signal Filtered (Low Quality).")
                
                time.sleep(2) # راحة بسيطة بين العملات
            
            print("💤 Waiting for next cycle...")
            time.sleep(60) # دورة فحص كل دقيقة
            
        except KeyboardInterrupt:
            print("🛑 Execution Agent Stopped.")
            break
        except Exception as e:
            print(f"⚠️ Error in main loop: {e}")
            time.sleep(10)

if __name__ == "__main__":
    start_execution_engine()