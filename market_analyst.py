import ccxt
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai
import time
from datetime import datetime
import os
import sys

# ==========================================
# 🔑 مفتاح API (ضعه هنا)
# ==========================================
GEMINI_API_KEY = "AIzaSyB8_1yci6_U0vUc3JKvRSOS50a-pw0EBuU"

# ==========================================
# 🛠️ إعدادات النظام
# ==========================================
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

exchange = ccxt.binance({
    'enableRateLimit': True,
    'options': {'defaultType': 'future'} 
})

def fetch_market_data(symbol):
    print(f"\n🔍 جاري سحب البيانات الكاملة (200 شمعة + عمق السوق) لـ {symbol}...")
    try:
        # 1. سحب بيانات الشموع (تاريخ طويل للمقارنة)
        timeframes = ['15m', '1h', '4h', '12h', '1d', '1w', '1M']
        data = {}
        
        for tf in timeframes:
            try:
                bars = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=200) # 200 شمعة للتحليل التاريخي
                if not bars:
                    data[tf] = "No Data"
                    continue
                    
                df = pd.DataFrame(bars, columns=['Time', 'Open', 'High', 'Low', 'Close', 'Volume'])
                
                # المؤشرات الفنية
                df['RSI'] = ta.rsi(df['Close'], length=14)
                df['EMA_50'] = ta.ema(df['Close'], length=50)
                df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
                
                # حساب نسبة التغير
                change_pct = ((df['Close'].iloc[-1] - df['Open'].iloc[-1]) / df['Open'].iloc[-1]) * 100
                
                data[tf] = {
                    'Close': df['Close'].iloc[-1],
                    'High': df['High'].iloc[-1],
                    'Low': df['Low'].iloc[-1],
                    'RSI': round(df['RSI'].iloc[-1], 2) if pd.notna(df['RSI'].iloc[-1]) else "N/A",
                    'ATR': round(df['ATR'].iloc[-1], 4) if pd.notna(df['ATR'].iloc[-1]) else "N/A",
                    'Change_%': round(change_pct, 2),
                    'Volume': df['Volume'].iloc[-1],
                    'Trend': "صاعد 🟢" if df['Close'].iloc[-1] > df['EMA_50'].iloc[-1] else "هابط 🔴"
                }
            except Exception as e:
                data[tf] = f"Error: {str(e)}"

        # 2. سحب دفتر الأوامر (Whale Data)
        try:
            print("🐳 جاري استجواب الحيتان وسحب دفتر الأوامر...")
            orderbook = exchange.fetch_order_book(symbol, limit=20) 
            data['order_book'] = {
                'bids': orderbook['bids'][:7], # أقوى 7 طلبات شراء
                'asks': orderbook['asks'][:7]  # أقوى 7 طلبات بيع
            }
        except Exception as e:
            data['order_book'] = "بيانات الحيتان غير متاحة"
            
        return data
    except Exception as e:
        print(f"❌ خطأ عام: {e}")
        return None

def generate_analysis_report(symbol, market_data):
    print("🧠 جاري تشغيل المحلل الشامل (التاريخ + الحيتان + السيناريوهات)...")
    
    # تحويل بيانات الحيتان لنص
    ob = market_data.get('order_book', {})
    bids_str = str(ob.get('bids', 'N/A'))
    asks_str = str(ob.get('asks', 'N/A'))

    # ==========================================
    # 📝 الرسالة العملاقة (Mega Prompt)
    # ==========================================
    prompt = f"""
    أنت كبير المحللين الاستراتيجيين والمؤرخ المالي. لديك مهمة شاملة لتحليل عملة {symbol}.
    
    📊 **البيانات الفنية (الهيكل):**
    {market_data}
    
    🐳 **بيانات الحيتان (العمق):**
    - Bids (شراء): {bids_str}
    - Asks (بيع): {asks_str}

    **المطلوب كتابة تقرير "موسوعي" ومفصل جداً يحتوي على الأقسام التالية (لا تحذف أي قسم):**

    ### 1. 🌍 السياق العام والقصة (The Context)
    *(ابدأ بوصف حال السوق: هل هو تجميع، تصريف، خوف، أم طمع؟ اربط الفريم الشهري والأسبوعي لتعطينا الخلفية الكاملة).*

    ### 2. ⏳ التحليل التاريخي (آلة الزمن)
    *هذا القسم مهم جداً للمستخدم:*
    - **التشابه التاريخي:** هل هذا النمط الفني (مثل RSI الهابط مع تماسك السعر) تكرر سابقاً؟ (مثلاً: يشبه ما حدث في تاريخ كذا...).
    - **النتيجة السابقة:** ماذا حدث عندما تكرر هذا الشكل في الماضي؟ (هل انهار السعر أم انفجر؟).
    - **المقارنة:** هل الوضع الحالي أفضل أم أسوأ من الماضي؟

    ### 3. 🐳 تشريح تحركات الحيتان (Whale Surgery)
    *حلل أرقام دفتر الأوامر بدقة:*
    - **خريطة التمركز:** أين يقف الحيتان بالضبط؟ (اذكر الأسعار).
    - **الاتفاق:** هل هناك جدار شراء/بيع موحد أم سيولة مشتتة؟
    - **كشف الخداع (Spoofing):**
        * ما هي نسبة "صدق" هذه الأرقام؟ (مثلاً 80% حقيقية).
        * ما هي احتمالية سحب الأوامر فجأة؟ (نسبة مئوية).
        * **التأثير الزمني:** كيف ستؤثر هذه الأوامر على فريم 15 دقيقة؟ وهل ستصمد أمام فريم اليوم؟

    ### 4. 🕵️‍♂️ الأسرار والكواليس (Secrets)
    *(اكتب فقرة عن "ما لا يخبرنا به الشارت". هل هناك فخ للمتداولين الصغار؟ هل يحاول صانع السوق إشعارنا بالملل؟ تكلم عن سيكولوجية السوق).*

    ### 5. 🚦 جدول السيناريوهات التفصيلي
    | الفريم | السيناريو المرجح | نسبته % | السيناريو البديل | نسبته % | السلوك المطلوب |
    | :--- | :--- | :--- | :--- | :--- | :--- |
    | **15 دقيقة** | ... | ... | ... | ... | ... |
    | **1 ساعة** | ... | ... | ... | ... | ... |
    | **4 ساعات** | ... | ... | ... | ... | ... |
    | **12 ساعة** | ... | ... | ... | ... | ... |
    | **اليومي** | ... | ... | ... | ... | ... |

    ### 6. ⚖️ ميزان الثقة والقرار النهائي
    - **نسبة ثقة المحلل:** (من 0% لـ 100%).
    - **القرار:** (خطة عمل واضحة: دخول، خروج، تعليق أمر).

    **الأسلوب:** استخدم لغة عربية احترافية ومباشرة.
    """

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ خطأ في التوليد: {e}"

def main():
    if os.name == 'nt': os.system('cls')
    else: os.system('clear')
    
    print("="*60)
    print("💎 المحلل الشامل (Grand Master Analyst) - النسخة الكاملة")
    print("="*60)
    
    while True:
        symbol_input = input("\n📝 اكتب العملة (مثال BTC) أو q للخروج: ").upper().strip()
        
        if symbol_input == 'Q':
            break
            
        if not symbol_input: continue
        
        final_symbol = symbol_input if "/" in symbol_input else f"{symbol_input}/USDT"
        
        market_data = fetch_market_data(final_symbol)
        
        if market_data:
            report = generate_analysis_report(final_symbol, market_data)
            print("\n" + "-"*60)
            print(report)
            print("-"*60)
            
            save = input("💾 حفظ التقرير؟ (y/n): ").lower()
            if save == 'y':
                filename = f"GrandMaster_{final_symbol.replace('/','-')}_{datetime.now().strftime('%H-%M')}.md"
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(report)
                print(f"✅ تم الحفظ.")

if __name__ == "__main__":
    main()