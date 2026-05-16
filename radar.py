import asyncio
import json
import statistics
import os
import ccxt.async_support as ccxt  # نستخدم النسخة الـ Async من ccxt
import websockets
from datetime import datetime
from collections import deque
from colorama import init, Fore, Style

init(autoreset=True)

# ==========================================
# ⚙️ إعدادات النظام
# ==========================================
SYMBOL = 'avntUSDT'       # صيغة Bybit V5 WebSocket
CCXT_SYMBOL = 'ZVNT/USDT' # صيغة CCXT
OI_HISTORY_LEN = 20      
REFRESH_RATE = 3         
WSS_URL = "wss://stream.bybit.com/v5/public/linear"

# مخزن بيانات مشترك (يتم تحديثه لحظياً من السوكيت)
shared_data = {
    'price': 0.0,
    'oi': 0.0,
    'last_update': None,
    'connected': False
}

# مخزن بيانات التحليل (Buffer)
oi_history = deque(maxlen=OI_HISTORY_LEN)

async def get_1h_change(exchange):
    """
    جلب التغير الحقيقي خلال الساعة الماضية بدقة (عبر REST API لأنه بيانات تاريخية)
    """
    try:
        ohlcv = await exchange.fetch_ohlcv(CCXT_SYMBOL, timeframe='1h', limit=2)
        if len(ohlcv) < 2:
            return 0.0
        
        prev_close = ohlcv[-2][4]  
        current_price = ohlcv[-1][4] 
        
        change_pct = ((current_price - prev_close) / prev_close) * 100
        return change_pct
    except Exception:
        return 0.0

def interpret_market(price_1h_pct, oi_change_pct):
    if price_1h_pct > 0 and oi_change_pct > 0:
        return f"{Fore.GREEN}STRONG BULLISH (Trend + Vol Up) 🚀"
    elif price_1h_pct > 0 and oi_change_pct < 0:
        return f"{Fore.YELLOW}WEAK BULLISH (Longs Closing) ⚠️"
    elif price_1h_pct < 0 and oi_change_pct > 0:
        return f"{Fore.RED}STRONG BEARISH (Shorts Building Up) 🩸"
    elif price_1h_pct < 0 and oi_change_pct < 0:
        return f"{Fore.CYAN}BEARISH COVERING (Shorts Exiting) 📉"
    else:
        return f"{Fore.WHITE}CHOPPY / NEUTRAL 🦀"

def print_dashboard(price, oi, avg_oi, price_1h_pct):
    os.system('cls' if os.name == 'nt' else 'clear')
    
    oi_delta_pct = ((oi - avg_oi) / avg_oi) * 100 if avg_oi > 0 else 0
    signal = interpret_market(price_1h_pct, oi_delta_pct)

    print(Style.BRIGHT + Fore.MAGENTA + f"🛡️ PRECISION RADAR (WSS) | {CCXT_SYMBOL}")
    print("=" * 60)
    
    print(f"\n💰 {Fore.YELLOW}PRICE ACTION:")
    print(f"   Current: ${price:,.2f}")
    
    color_1h = Fore.GREEN if price_1h_pct > 0 else Fore.RED
    print(f"   1H Change: {color_1h}{price_1h_pct:+.2f}% {Style.RESET_ALL}(vs Previous Candle Close)")

    print(f"\n🌊 {Fore.CYAN}LIQUIDITY FLOW (OI):")
    print(f"   Current OI: ${oi:,.0f}")
    print(f"   Avg OI ({OI_HISTORY_LEN} ticks): ${avg_oi:,.0f}")
    
    oi_color = Fore.GREEN if oi_delta_pct > 0 else Fore.RED
    print(f"   Flow Delta: {oi_color}{oi_delta_pct:+.4f}% {Style.RESET_ALL}(Momentum vs Avg)")

    print(f"\n🧠 {Style.BRIGHT}CONTEXT:")
    print(f"   {signal}")
    print("-" * 60)
    status = f"{Fore.GREEN}Connected ⚡" if shared_data['connected'] else f"{Fore.RED}Connecting..."
    print(f"Status: {status} | Last Update: {datetime.now().strftime('%H:%M:%S')}")

# ==========================================
# 🔌 مهمة 1: الاتصال المستمر (WebSocket Task)
# ==========================================
async def websocket_listener():
    while True:
        try:
            async with websockets.connect(WSS_URL) as websocket:
                # الاشتراك في قناة الـ Tickers للحصول على السعر والـ OI
                subscribe_msg = {
                    "op": "subscribe",
                    "args": [f"tickers.{SYMBOL}"]
                }
                await websocket.send(json.dumps(subscribe_msg))
                print(f"{Fore.GREEN}✅ WebSocket Connected: Listening to {SYMBOL}...")
                shared_data['connected'] = True

                while True:
                    response = await websocket.recv()
                    data = json.loads(response)
                    
                    # استخراج البيانات من رسالة Bybit V5
                    if 'topic' in data and f"tickers.{SYMBOL}" == data['topic']:
                        ticker_data = data['data']
                        
                        # التحديث فقط إذا توفرت القيم (Bybit أحياناً ترسل تحديث جزئي)
                        if 'lastPrice' in ticker_data:
                            shared_data['price'] = float(ticker_data['lastPrice'])
                        
                        if 'openInterest' in ticker_data:
                            shared_data['oi'] = float(ticker_data['openInterest'])
                        
                        shared_data['last_update'] = datetime.now()

        except Exception as e:
            shared_data['connected'] = False
            print(f"{Fore.RED}⚠️ WSS Error: {e} - Reconnecting in 5s...")
            await asyncio.sleep(5)

# ==========================================
# 🧠 مهمة 2: المعالجة والتحليل (Logic Task)
# ==========================================
async def logic_processor():
    # إعداد CCXT Async
    exchange = ccxt.bybit({
        'enableRateLimit': True,
        'options': {'defaultType': 'linear'}
    })

    print("⏳ Initializing Buffer from Live Stream...")
    
    # انتظار امتلاء البيانات الأولية من الويب سوكيت
    while shared_data['price'] == 0 or shared_data['oi'] == 0:
        await asyncio.sleep(1)

    # ملء البفر (Buffer) بشكل أولي سريع
    while len(oi_history) < OI_HISTORY_LEN:
        oi_history.append(shared_data['oi'])
        print(f"Buffer: {len(oi_history)}/{OI_HISTORY_LEN}", end='\r')
        await asyncio.sleep(0.5) # تعبئة سريعة

    print("\n✅ System Active! Running Logic...")

    while True:
        try:
            # 1. أخذ نسخة من البيانات الحالية (Snapshot)
            current_price = shared_data['price']
            current_oi = shared_data['oi']

            # 2. تطبيق منطق الـ Smoothing القديم
            oi_history.append(current_oi)
            avg_oi = statistics.mean(oi_history)

            # 3. جلب بيانات الفريم (كل فترة لتقليل الطلبات)
            # هنا نستخدم await لأن الدالة async
            pct_1h = await get_1h_change(exchange)

            # 4. العرض
            print_dashboard(current_price, current_oi, avg_oi, pct_1h)

            # الحفاظ على الـ Refresh Rate الخاص بالاستراتيجية
            await asyncio.sleep(REFRESH_RATE)

        except Exception as e:
            print(f"Logic Error: {e}")
            await asyncio.sleep(5)
    
    await exchange.close()

# ==========================================
# 🚀 المشغل الرئيسي
# ==========================================
async def main():
    # تشغيل المهمتين بالتوازي
    await asyncio.gather(
        websocket_listener(),
        logic_processor()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Exiting...")