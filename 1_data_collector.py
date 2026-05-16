import ccxt
import pandas as pd
import os
import time
from datetime import datetime
from tqdm import tqdm  # <--- تم إضافة المكتبة هنا

# --- إعدادات العملات والفريمات ---
COINS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'BNB/USDT', 'SHIB/USDT', 'STX/USDT']
TIMEFRAMES = ['5m', '15m', '30m', '1h', '2h', '4h', '6h', '12h', '1d', '1w', '1M']
START_DATE_GENERAL = '2017-01-01 00:00:00'

class DataCollector:
    def __init__(self):
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}
        })
        if not os.path.exists('market_data'):
            os.makedirs('market_data')

    # دالة مساعدة لحساب مدة الفريم بالمللي ثانية لضبط شريط التحميل
    def get_timeframe_ms(self, timeframe):
        amount = int(timeframe[:-1])
        unit = timeframe[-1]
        if unit == 'm': return amount * 60 * 1000
        elif unit == 'h': return amount * 60 * 60 * 1000
        elif unit == 'd': return amount * 24 * 60 * 60 * 1000
        elif unit == 'w': return amount * 7 * 24 * 60 * 60 * 1000
        elif unit == 'M': return amount * 30 * 24 * 60 * 60 * 1000 # تقريبي
        return 60000 # افتراضي

    def fetch_and_update(self, symbol, timeframe):
        safe_symbol = symbol.replace('/', '')
        filename = f'market_data/{safe_symbol}_{timeframe}.csv'
        
        # 1. تحديد نقطة البداية
        if os.path.exists(filename):
            existing_df = pd.read_csv(filename)
            last_timestamp = pd.to_datetime(existing_df['timestamp']).iloc[-1]
            since = int(last_timestamp.timestamp() * 1000) + 1
            mode = "تحديث"
        else:
            since = self.exchange.parse8601(START_DATE_GENERAL + 'Z')
            existing_df = pd.DataFrame()
            mode = "جديد"

        # حساب التقدير لشريط التحميل
        now = self.exchange.milliseconds()
        total_time_needed = now - since
        tf_ms = self.get_timeframe_ms(timeframe)
        estimated_candles = total_time_needed // tf_ms
        
        if estimated_candles <= 0:
            print(f"✅ {symbol} [{timeframe}] محدث بالفعل.")
            return

        print(f"🔄 {mode}: {symbol} [{timeframe}] - جاري سحب {estimated_candles} شمعة تقريباً...")

        # --- بداية شريط التحميل ---
        new_data = []
        with tqdm(total=estimated_candles, unit=" candle", ncols=100) as pbar:
            while True:
                try:
                    ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=1000)
                    if not ohlcv:
                        break
                    
                    new_data.extend(ohlcv)
                    fetched_count = len(ohlcv)
                    since = ohlcv[-1][0] + 1
                    
                    # تحديث الشريط بالعدد الذي تم جلبه
                    pbar.update(fetched_count)
                    
                    if since > now:
                        break
                    
                    time.sleep(self.exchange.rateLimit / 1000)
                    
                except Exception as e:
                    pbar.set_description(f"⚠️ Error: {e}")
                    time.sleep(5)
                    continue
        # --- نهاية شريط التحميل ---

        if not new_data:
            return

        # 2. الحفظ والتنسيق
        df_new = pd.DataFrame(new_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df_new['timestamp'] = pd.to_datetime(df_new['timestamp'], unit='ms')
        
        full_df = pd.concat([existing_df, df_new]).drop_duplicates(subset='timestamp', keep='last')
        full_df.to_csv(filename, index=False)
        # print(f"✅ تم الحفظ. الإجمالي: {len(full_df)}") # تم إلغاؤه لأن الشريط يغني عنه

if __name__ == "__main__":
    collector = DataCollector()
    print("🚀 بدء جامع البيانات...")
    
    for coin in COINS:
        for tf in TIMEFRAMES:
            try:
                collector.fetch_and_update(coin, tf)
            except Exception as e:
                print(f"\n❌ فشل مع {coin} {tf}: {e}")

    print("\n🎉 تمت المهمة! جميع البيانات جاهزة.")