# tick_collector.py
# هذا البوت هو "الصندوق الأسود" الذي يسجل كل حركة بيع وشراء حقيقية
import time
import os
import csv
import datetime
import cloudscraper
from config import SYMBOLS

# إعداد المجلدات لحفظ الداتا
DATA_DIR = "raw_tick_data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

scraper = cloudscraper.create_scraper()
BASE_URL = "https://fapi.binance.com"

def get_recent_trades(symbol, limit=1000):
    """
    سحب آخر 1000 صفقة تمت فعلياً في السوق.
    هذه ليست شموع، هذه عمليات بيع وشراء حقيقية.
    """
    try:
        # endpoint: aggTrades يعطيك تفاصيل من باع ومن اشترى
        url = f"{BASE_URL}/fapi/v1/aggTrades"
        params = {'symbol': symbol, 'limit': limit}
        response = scraper.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"⚠️ Error {symbol}: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return []

def save_trades_to_csv(symbol, trades):
    """
    حفظ الصفقات في ملف CSV يومي منفصل لكل عملة
    """
    # اسم الملف يتغير يومياً أوتوماتيكياً (مثلاً: BTCUSDT_2025-12-11.csv)
    date_str = datetime.datetime.utcnow().strftime('%Y-%m-%d')
    filename = f"{DATA_DIR}/{symbol}_{date_str}.csv"
    
    file_exists = os.path.isfile(filename)
    
    # تحويل البيانات إلى صيغة سهلة القراءة
    # aggTrade keys: a: TradeID, p: Price, q: Quantity, f: FirstTradeID, l: LastTradeID, T: Timestamp, m: IsBuyerMaker
    
    with open(filename, 'a', newline='') as f:
        writer = csv.writer(f)
        
        # كتابة رأس الجدول لو الملف جديد
        if not file_exists:
            writer.writerow(['TradeID', 'Price', 'Quantity', 'Timestamp', 'Is_Sell_Order'])
            
        for t in trades:
            # t['m'] == True تعني أن "صانع السوق" كان مشترياً، يعني المنفذ كان "بائعاً" (Sell Order)
            # هذه أهم معلومة لمعرفة ضغط البيع والشراء
            writer.writerow([t['a'], t['p'], t['q'], t['T'], t['m']])

def start_mining():
    print("🚀 STARTING DEEP DATA MINER (Tick-by-Tick)...")
    print(f"📂 Saving data to folder: {DATA_DIR}")
    
    # لتجنب التكرار، سنحفظ ID آخر صفقة سجلناها لكل عملة
    last_trade_ids = {symbol: 0 for symbol in SYMBOLS}
    
    while True:
        for symbol in SYMBOLS:
            trades = get_recent_trades(symbol)
            
            if not trades:
                continue
                
            # تصفية الصفقات الجديدة فقط (عشان منسجلش نفس الصفقة مرتين)
            new_trades = [t for t in trades if t['a'] > last_trade_ids[symbol]]
            
            if new_trades:
                save_trades_to_csv(symbol, new_trades)
                # تحديث آخر ID
                last_trade_ids[symbol] = new_trades[-1]['a']
                print(f"   ✅ {symbol}: Saved {len(new_trades)} new trades.")
            
            time.sleep(1) # راحة سريعة جداً لتجنب البلوك
            
        print("   ⏳ ... scanning ...")
        time.sleep(5) # ننتظر قليلاً ثم نعيد الكرة

if __name__ == "__main__":
    start_mining()