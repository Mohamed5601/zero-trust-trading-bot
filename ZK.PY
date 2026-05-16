import threading
import time
import json
import os
import pandas as pd
import numpy as np
import websocket  # pip install websocket-client
from collections import deque
from pybit.unified_trading import WebSocket as BybitWS
from colorama import init, Fore, Style, Back
from threading import Lock

init(autoreset=True)

# --- CONFIGURATION ---
SYMBOL_BINANCE = 'avntusdt'  # Lowercase for Binance Stream
SYMBOL_BYBIT = 'AVNTUSDT'    # Uppercase for Bybit
REFRESH_RATE = 0.1          # 100ms refresh for faster eyes
AVG_WINDOW_SECONDS = 5
WINDOW_SIZE = int(AVG_WINDOW_SECONDS / REFRESH_RATE)

# --- GLOBAL MEMORY (Dual Source) ---
# Bybit Memory
ob_bybit_bids = {}
ob_bybit_asks = {}

# Binance Memory
ob_binance_bids = {}
ob_binance_asks = {}

# Unified Trade Stream
# رفعنا الذاكرة لـ 10,000 لأننا بنسحب من منصتين
recent_trades = deque(maxlen=10000) 
intel_history = deque(maxlen=WINDOW_SIZE)
price_history = deque(maxlen=50) # لمراقبة اتجاه السعر (Price Action)

data_lock = Lock()
binance_ready = False
bybit_ready = False

# --- 1. BINANCE WORKER (Raw WebSocket) ---
def on_message_binance(ws, message):
    global ob_binance_bids, ob_binance_asks, binance_ready
    msg = json.loads(message)
    stream = msg.get('stream')
    data = msg.get('data')

    with data_lock:
        # معالجة الأوردر بوك (Depth)
        if 'depth20' in stream:
            # Binance بيبعت Snapshot كل مرة في الستريم ده (سهل التعامل)
            ob_binance_bids = {float(x[0]): float(x[1]) for x in data['bids']}
            ob_binance_asks = {float(x[0]): float(x[1]) for x in data['asks']}
            binance_ready = True
        
        # معالجة الصفقات (AggTrades)
        elif 'aggTrade' in stream:
            try:
                price = float(data['p'])
                qty = float(data['q'])
                is_maker = data['m'] # True means Sell (Maker was Buyer), False means Buy
                side = 'sell' if is_maker else 'buy'
                cost = price * qty
                
                recent_trades.append({
                    'source': 'BNB',
                    'side': side,
                    'cost': cost,
                    'price': price,
                    'time': time.time()
                })
            except: pass

def start_binance_stream():
    # دمج ستريم الدفتر + ستريم الصفقات لتقليل الاتصالات
    stream_url = f"wss://stream.binance.com:9443/stream?streams={SYMBOL_BINANCE}@depth20@100ms/{SYMBOL_BINANCE}@aggTrade"
    ws = websocket.WebSocketApp(stream_url, on_message=on_message_binance)
    ws.run_forever()

# --- 2. BYBIT HANDLERS (Pybit) ---
def handle_bybit_orderbook(message):
    global ob_bybit_bids, ob_bybit_asks, bybit_ready
    data = message.get('data', {})
    msg_type = message.get('type')
    
    with data_lock:
        if msg_type == 'snapshot':
            ob_bybit_bids = {float(x[0]): float(x[1]) for x in data.get('b', [])}
            ob_bybit_asks = {float(x[0]): float(x[1]) for x in data.get('a', [])}
            bybit_ready = True
        elif msg_type == 'delta':
            for b in data.get('b', []):
                p, s = float(b[0]), float(b[1])
                if s == 0: ob_bybit_bids.pop(p, None)
                else: ob_bybit_bids[p] = s
            for a in data.get('a', []):
                p, s = float(a[0]), float(a[1])
                if s == 0: ob_bybit_asks.pop(p, None)
                else: ob_bybit_asks[p] = s

def handle_bybit_trades(message):
    data = message.get('data', [])
    with data_lock:
        for trade in data:
            try:
                side = 'buy' if trade['S'] == 'Buy' else 'sell'
                cost = float(trade['p']) * float(trade['v'])
                recent_trades.append({
                    'source': 'BYB',
                    'side': side,
                    'cost': cost,
                    'price': float(trade['p']),
                    'time': time.time()
                })
            except: pass

# --- 3. THE GLOBAL FUSION ENGINE ---
def get_global_intelligence():
    with data_lock:
        if not (binance_ready and bybit_ready): return "INITIALIZING_STREAMS"

        # 1. تجميع السيولة (Aggregation)
        # نأخذ مجموع الدولارات في أول 20 مستوى من المنصتين
        # Binance
        bnb_bid_vol = sum([p*s for p,s in ob_binance_bids.items()])
        bnb_ask_vol = sum([p*s for p,s in ob_binance_asks.items()])
        # Bybit
        byb_bid_vol = sum([p*s for p,s in ob_bybit_bids.items()])
        byb_ask_vol = sum([p*s for p,s in ob_bybit_asks.items()])
        
        total_bid_wall = bnb_bid_vol + byb_bid_vol
        total_ask_wall = bnb_ask_vol + byb_ask_vol
        
        # 2. Global Imbalance
        imbalance = (total_bid_wall - total_ask_wall) / (total_bid_wall + total_ask_wall)
        intel_history.append(imbalance)
        
        # تنعيم الإشارة (Weighted Average)
        weights = np.arange(1, len(intel_history) + 1)
        smoothed_imbalance = np.average(intel_history, weights=weights)

        # 3. Global Delta (Last 5 Secs)
        now = time.time()
        relevant_trades = [t for t in recent_trades if now - t['time'] <= AVG_WINDOW_SECONDS]
        
        delta = 0
        current_price = 0
        
        if relevant_trades:
            buy_vol = sum(t['cost'] for t in relevant_trades if t['side'] == 'buy')
            sell_vol = sum(t['cost'] for t in relevant_trades if t['side'] == 'sell')
            delta = buy_vol - sell_vol
            current_price = relevant_trades[-1]['price'] # آخر سعر تم تنفيذه عالمياً
            
            # تخزين السعر لتحليل الاتجاه
            price_history.append(current_price)
        
        # 4. Price Trend Analysis (Slope)
        # هل السعر ثابت أم يتحرك؟ (بسيط)
        price_trend = "STABLE"
        if len(price_history) > 10:
            p_start = price_history[0]
            p_end = price_history[-1]
            if p_end > p_start + 5: price_trend = "UP"
            elif p_end < p_start - 5: price_trend = "DOWN"

        return {
            'imbalance': smoothed_imbalance,
            'delta': delta,
            'bids': total_bid_wall,
            'asks': total_ask_wall,
            'price': current_price,
            'trend': price_trend,
            'vol_bnb_pct': bnb_bid_vol / (total_bid_wall+1) # نسبة سيولة بينانس
        }

# --- 4. VISUALIZATION (Actionable) ---
CLR = "\033[K"
HOME = "\033[H"

def visualize(data):
    print(HOME, end="")
    
    # Header
    print(f"{Back.BLUE}{Fore.WHITE} 🌍 GLOBAL RADAR (BINANCE + BYBIT) | BTCUSDT {Style.RESET_ALL}{CLR}")
    
    # Price & Trend
    trend_icon = "➡️"
    if data['trend'] == "UP": trend_icon = "↗️ 🟢"
    elif data['trend'] == "DOWN": trend_icon = "↘️ 🔴"
    print(f" PRICE: {Style.BRIGHT}{data['price']:.2f} {trend_icon}{CLR}")
    
    # Imbalance Bar & Value
    imb_pct = data['imbalance'] * 100
    imb_str = f"{imb_pct:+.1f}%"
    bar_len = 40
    bid_len = int((data['imbalance'] + 1) / 2 * bar_len)
    bid_len = max(0, min(bar_len, bid_len))
    ask_len = bar_len - bid_len
    
    c_imb = Fore.GREEN if data['imbalance'] > 0 else Fore.RED
    print(f"\n{Style.BRIGHT}⚖️  GLOBAL LIQUIDITY IMBALANCE: {c_imb}{imb_str}{Style.RESET_ALL}{CLR}")
    print(Fore.GREEN + "█"*bid_len + Fore.RED + "█"*ask_len + Style.RESET_ALL + CLR)
    print(f" {Fore.GREEN}${data['bids']/1e6:.1f}M{Style.RESET_ALL} (Bids) vs {Fore.RED}${data['asks']/1e6:.1f}M{Style.RESET_ALL} (Asks){CLR}")
    
    # Delta
    d_fmt = f"${data['delta']/1e3:.1f}K"
    d_col = Fore.GREEN if data['delta'] > 0 else Fore.RED
    print(f"\n🔫 GLOBAL DELTA (5s): {d_col}{d_fmt}{Style.RESET_ALL}{CLR}")

    # --- THE SMART LOGIC (Strategic Intent) ---
    print(f"\n🧠 {Style.BRIGHT}AI INTERPRETATION:{Style.RESET_ALL} {CLR}")
    
    msg = Fore.WHITE + "Analyzing Flow..."
    
    # Logic: Imbalance vs Delta vs Price Trend
    # Case 1: Absorption (Bullish) -> High Selling (Neg Delta) BUT High Bids (Pos Imbalance) AND Price Stable/Up
    if data['imbalance'] > 0.25 and data['delta'] < -500000:
        if data['trend'] != "DOWN":
            msg = Fore.GREEN + Style.BRIGHT + "🛡️ ABSORPTION DETECTED! (Whales eating dips)"
        else:
             msg = Fore.RED + "📉 SELLING PRESSURE WINNING (Walls breaking)"

    # Case 2: Spoofing (Bearish) -> High Bids (Pos Imbalance) BUT Price Dropping fast
    elif data['imbalance'] > 0.30 and data['trend'] == "DOWN":
        msg = Fore.MAGENTA + Style.BRIGHT + "⚠️ POSSIBLE SPOOFING (Fake Buy Walls Ignored)"

    # Case 3: Aggressive Buying
    elif data['delta'] > 1000000 and data['trend'] == "UP":
        msg = Fore.GREEN + "🚀 AGGRESSIVE MOMENTUM (Follow the flow)"

    # Case 4: Aggressive Selling
    elif data['delta'] < -1000000 and data['trend'] == "DOWN":
        msg = Fore.RED + "🩸 PANIC DUMP (Don't catch knives)"

    print(msg + CLR)
    print("\n" + Style.DIM + f"Binance Weight: {data['vol_bnb_pct']*100:.0f}% of data | Time: {datetime.now().strftime('%H:%M:%S')}{CLR}")

# --- MAIN LOOP ---
if __name__ == "__main__":
    from datetime import datetime
    os.system('cls' if os.name == 'nt' else 'clear')
    
    # 1. Start Binance in Background Thread
    t_bnb = threading.Thread(target=start_binance_stream)
    t_bnb.daemon = True
    t_bnb.start()
    print("Connecting to Binance Global Stream...")

    # 2. Start Bybit in Background (Pybit handles its own threads)
    ws_bybit = BybitWS(testnet=False, channel_type="linear")
    ws_bybit.orderbook_stream(depth=50, symbol=SYMBOL_BYBIT, callback=handle_bybit_orderbook)
    ws_bybit.trade_stream(symbol=SYMBOL_BYBIT, callback=handle_bybit_trades)
    print("Connecting to Bybit Local Stream...")

    # 3. Main Loop
    try:
        while True:
            packet = get_global_intelligence()
            if isinstance(packet, dict):
                visualize(packet)
            else:
                print(f"\r{Fore.YELLOW}Syncing data streams... ({binance_ready}/{bybit_ready})", end="")
            time.sleep(REFRESH_RATE)
    except KeyboardInterrupt:
        print("\nSystem Halted.")