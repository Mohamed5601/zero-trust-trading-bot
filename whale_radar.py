import time
import requests
from datetime import datetime
import sys
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

# --- إعدادات التيربو ---
WATCHLIST = [
    'SOLUSDT', 
    "STX/USDT",  
  #  'SUIUSDT',      
   # 'DOGEUSDT',   
   # 'XRPUSDT', 
   # 'SOLUSDT'     
   'BTCUSDT', 
]
WHALE_THRESHOLD_USD = 50_000 
BASE_URL = "https://fapi.binance.com"

# متغيرات التخزين اللحظي
session_stats = {symbol: {'buy': 0, 'sell': 0} for symbol in WATCHLIST}

def get_live_ratio(symbol):
    b = session_stats[symbol]['buy']
    s = session_stats[symbol]['sell']
    total = b + s
    if total == 0: return "Waiting..."
    buy_pct = (b / total) * 100
    
    if buy_pct >= 65: return f"🔥 BULLS {buy_pct:.0f}%"
    elif buy_pct <= 35: return f"❄️ BEARS {100-buy_pct:.0f}%"
    else: return f"⚖️ {buy_pct:.0f}% Buy"

def check_whales():
    print(f"🚀 TURBO RADAR ACTIVATED (Real-Time Ratio)...")
    print("-" * 50)
    
    last_trade_ids = {symbol: 0 for symbol in WATCHLIST}

    while True:
        try:
            for symbol in WATCHLIST:
                try:
                    url = f"{BASE_URL}/fapi/v1/aggTrades?symbol={symbol}&limit=50"
                    r = requests.get(url, timeout=1) # تقليل التايم أوت للسرعة
                    if r.status_code != 200: continue
                    
                    trades = r.json()
                    trades.sort(key=lambda x: x['a'])

                    for t in trades:
                        trade_id = t['a']
                        price = float(t['p'])
                        usd_value = float(t['p']) * float(t['q'])
                        is_sell = t['m'] 

                        if trade_id <= last_trade_ids[symbol]: continue
                        last_trade_ids[symbol] = trade_id

                        # تحديث الإحصائيات فوراً
                        if is_sell: session_stats[symbol]['sell'] += usd_value
                        else: session_stats[symbol]['buy'] += usd_value

                        # عرض الصفقة فوراً إذا كانت حوت
                        if usd_value >= WHALE_THRESHOLD_USD:
                            side = "SHORT 🔴" if is_sell else "LONG 🟢"
                            # هنا السحر: عرض النسبة الحالية فوراً بجانب الصفقة
                            live_stat = get_live_ratio(symbol)
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] {symbol:<10} | {side} | ${usd_value/1000:.0f}k | {live_stat}")

                except Exception:
                    continue
            
            # تصفير العدادات كل دقيقة تقريباً لضمان حداثة النسبة
            # (اختياري: ممكن نشيله لو عايز تراكمي)
            if int(time.time()) % 60 == 0:
                 for s in WATCHLIST: session_stats[s] = {'buy': 0, 'sell': 0}
                 print(f"\n--- 🔄 Stats Reset (New Minute) ---\n")
            
            time.sleep(0.2) # سرعة جنونية

        except KeyboardInterrupt:
            sys.exit()
        except Exception:
            time.sleep(1)

if __name__ == "__main__":
    check_whales()