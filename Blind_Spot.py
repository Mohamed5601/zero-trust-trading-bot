import ccxt
import pandas as pd
import time
import os
from colorama import init, Fore, Style

init(autoreset=True)

# --- إعدادات الماسح ---
SYMBOL = 'BTC/USDT'
TIMEFRAME = '5m'      # الفريم الجراحي
LIMIT = 100           # عدد الشموع للتحليل
REFRESH_RATE = 5      # تحديث كل 5 ثواني (لا يحتاج سرعة فائقة)

exchange = ccxt.bybit({'enableRateLimit': True, 'options': {'defaultType': 'linear'}})

def fetch_ohlcv_data():
    try:
        # جلب بيانات الشموع
        ohlcv = exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=LIMIT)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        return df
    except Exception:
        return None

def find_fvgs(df):
    # قائمة الفجوات
    bullish_fvgs = []
    bearish_fvgs = []
    
    current_price = df['close'].iloc[-1]

    # المنطق الرياضي للفجوة (ICT Concepts)
    # الفجوة تحدث عندما لا تتلامس ذيول الشموع (الشمعة 1 والشمعة 3)
    for i in range(len(df) - 3, 0, -1): # نبدأ من الأحدث للأقدم
        
        # 1. Bullish FVG (فجوة شرائية - دعم)
        # شرط: قاع الشمعة (i) أعلى من قمة الشمعة (i-2)
        if df['low'].iloc[i] > df['high'].iloc[i-2]:
            top = df['low'].iloc[i]
            bottom = df['high'].iloc[i-2]
            avg = (top + bottom) / 2
            
            # فلتر: هل السعر الحالي قريب منها؟ (نهمنا الفجوات القريبة فقط)
            if current_price > bottom * 0.99: 
                # هل تم ملؤها؟ (Mitigated)
                # نفحص الشموع التي جاءت بعد الشمعة i
                is_filled = False
                for j in range(i+1, len(df)):
                    if df['low'].iloc[j] <= bottom: # السعر نزل وغطى الفجوة
                        is_filled = True
                        break
                
                if not is_filled:
                    bullish_fvgs.append({'top': top, 'bottom': bottom, 'avg': avg, 'index': i})

        # 2. Bearish FVG (فجوة بيعية - مقاومة)
        # شرط: قمة الشمعة (i) أقل من قاع الشمعة (i-2)
        elif df['high'].iloc[i] < df['low'].iloc[i-2]:
            top = df['low'].iloc[i-2]
            bottom = df['high'].iloc[i]
            avg = (top + bottom) / 2
            
            if current_price < top * 1.01:
                is_filled = False
                for j in range(i+1, len(df)):
                    if df['high'].iloc[j] >= top:
                        is_filled = True
                        break
                
                if not is_filled:
                    bearish_fvgs.append({'top': top, 'bottom': bottom, 'avg': avg, 'index': i})
        
        # نكتفي بآخر 3 فجوات فقط لعدم التشتت
        if len(bullish_fvgs) >= 3 and len(bearish_fvgs) >= 3:
            break
            
    return bullish_fvgs, bearish_fvgs, current_price

def print_scanner(bull_fvgs, bear_fvgs, price):
    os.system('cls' if os.name == 'nt' else 'clear')
    print(Style.BRIGHT + Fore.YELLOW + f"🗺️  PRICE ACTION SCANNER (FVG Map) | {SYMBOL} [{TIMEFRAME}]")
    print(f"📍 Current Price: {Fore.WHITE}{price}")
    print("=" * 60)

    # 1. المقاومات (المغناطيس العلوي)
    print(f"\n{Fore.RED}🔴 BEARISH MAGNETS (Resistance/Targets):")
    if not bear_fvgs:
        print("   No immediate resistance gaps.")
    else:
        for fvg in bear_fvgs:
            dist = ((fvg['bottom'] - price) / price) * 100
            status = "NEAR" if dist < 0.2 else "FAR"
            print(f"   📉 GAP: {fvg['bottom']} - {fvg['top']} | Dist: {dist:.2f}% [{status}]")

    # 2. المنطقة الحالية
    print(f"\n{Fore.CYAN}      ---------- YOU ARE HERE ----------      ")

    # 3. الدعوم (المغناطيس السفلي)
    print(f"\n{Fore.GREEN}🟢 BULLISH MAGNETS (Support/Entries):")
    if not bull_fvgs:
        print("   No immediate support gaps.")
    else:
        for fvg in bull_fvgs:
            dist = ((price - fvg['top']) / price) * 100
            status = "NEAR" if dist < 0.2 else "FAR"
            print(f"   📈 GAP: {fvg['bottom']} - {fvg['top']} | Dist: {dist:.2f}% [{status}]")
            
    print("-" * 60)
    
    # التشخيص
    print(f"{Style.BRIGHT}🧠 SCANNER LOGIC:")
    if len(bear_fvgs) > 0 and price > bear_fvgs[0]['bottom'] - 50:
        print(Fore.RED + "   ⚠️  WARNING: Price approaching RESISTANCE GAP. Watch for Rejection!")
    elif len(bull_fvgs) > 0 and price < bull_fvgs[0]['top'] + 50:
        print(Fore.GREEN + "   ✅  OPPORTUNITY: Price approaching SUPPORT GAP. Watch for Bounce!")
    else:
        print(Fore.WHITE + "   Price is in equilibrium (No immediate magnets).")
        
    print(f"\nScan Time: {time.strftime('%H:%M:%S')}")

if __name__ == "__main__":
    while True:
        data = fetch_ohlcv_data()
        if data is not None:
            bull, bear, curr = find_fvgs(data)
            print_scanner(bull, bear, curr)
        time.sleep(REFRESH_RATE)