# collector.py (Cloudscraper Version - Anti-Bot Bypass)
import cloudscraper
import time
import datetime
import json
from config import SYMBOLS, FETCH_INTERVAL
from database import init_db, insert_market_data

BASE_URL = "https://fapi.binance.com"

# إنشاء Scraper يتجاوز حماية Cloudflare
scraper = cloudscraper.create_scraper()

def get_ticker_data(symbol):
    try:
        # 1. السعر
        # نستخدم scraper.get بدل requests.get
        price_res = scraper.get(f"{BASE_URL}/fapi/v1/ticker/price", params={'symbol': symbol}, timeout=15)
        
        # فحص إذا كان الرد ليس 200 (مثلا 403 أو 429)
        if price_res.status_code != 200:
            print(f"🛑 Blocked by Binance ({symbol}): Code {price_res.status_code}")
            # طبع جزء من الرسالة عشان نعرف السبب
            print(f"   Reason: {price_res.text[:100]}") 
            return None
            
        price = float(price_res.json()['price'])

        # 2. السيولة (Open Interest)
        oi_res = scraper.get(f"{BASE_URL}/fapi/v1/openInterest", params={'symbol': symbol}, timeout=15)
        oi_data = oi_res.json()
        oi_amount = float(oi_data['openInterest']) 
        oi_value = oi_amount * price 

        # 3. التمويل (Funding Rate)
        fund_res = scraper.get(f"{BASE_URL}/fapi/v1/premiumIndex", params={'symbol': symbol}, timeout=15)
        funding_rate = float(fund_res.json()['lastFundingRate'])

        # 4. الحجم (Volume)
        stats_res = scraper.get(f"{BASE_URL}/fapi/v1/ticker/24hr", params={'symbol': symbol}, timeout=15)
        volume = float(stats_res.json()['quoteVolume'])

        # 5. نسبة اللونج/شورت
        ls_res = scraper.get(f"{BASE_URL}/fapi/v1/topLongShortAccountRatio", 
                              params={'symbol': symbol, 'period': '5m', 'limit': 1}, timeout=15)
        
        ls_ratio = 0.0
        try:
            ls_data = ls_res.json()
            if isinstance(ls_data, list) and len(ls_data) > 0:
                ls_ratio = float(ls_data[0]['longShortRatio'])
        except:
            pass # لو فشل في دي مش مشكلة، نكمل بالباقي

        return (symbol, price, oi_value, oi_amount, funding_rate, volume, ls_ratio)

    except Exception as e:
        print(f"⚠️ Error processing {symbol}: {e}")
        return None

def start_collector():
    print("🚀 Starting Crypto Collector v3 (Cloudscraper Bypass)...")
    init_db()

    while True:
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        print(f"\n🔄 Collecting data at {timestamp}...")
        
        for symbol in SYMBOLS:
            data = get_ticker_data(symbol)
            if data:
                insert_market_data(data)
                print(f"   ✅ {symbol}: P={data[1]:.4f} | OI=${data[2]/1_000_000:.1f}M | L/S={data[6]}")
            else:
                print(f"   ❌ Skipped {symbol}")
            
            # راحة 3 ثواني لتجنب الشك
            time.sleep(3) 
        
        print(f"💤 Sleeping {FETCH_INTERVAL}s...")
        time.sleep(FETCH_INTERVAL)

if __name__ == "__main__":
    start_collector()