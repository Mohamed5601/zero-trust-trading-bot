# analyzer.py (Time-Aware Logic - No False Signals)
import sqlite3
import pandas as pd
import time
from datetime import datetime, timedelta
from config import DB_NAME, SYMBOLS
from notifier import send_telegram_msg

# الإعدادات
LOOKBACK_MINUTES = 60      
ANALYSIS_INTERVAL = 900    
OI_THRESHOLD = 100_000     
TIME_TOLERANCE = 10        # السماح بفارق زمني +- 10 دقائق عند البحث عن الداتا القديمة

def get_db_connection():
    # نستخدم نفس إعدادات الاتصال المحسنة
    conn = sqlite3.connect(DB_NAME, timeout=10)
    conn.execute('PRAGMA journal_mode=WAL;')
    return conn

def analyze_market():
    try:
        conn = get_db_connection()
        print(f"\n🔎 [{datetime.now().strftime('%H:%M:%S')}] Precision Scan Started...")
        
        for symbol in SYMBOLS:
            # 1. سحب البيانات الحديثة فقط (آخر 24 ساعة مثلاً لتقليل الحمل)
            query = f"""
            SELECT * FROM market_metrics 
            WHERE symbol = '{symbol}' 
            AND timestamp >= datetime('now', '-3 hours') 
            ORDER BY timestamp DESC
            """
            df = pd.read_sql_query(query, conn)
            
            if df.empty:
                print(f"   ⏳ {symbol}: No data found.")
                continue

            # تحويل عمود التوقيت إلى كائن وقت حقيقي
            df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed')
            
            # 2. تحديد النقطة الحالية (Current Point)
            current_row = df.iloc[0]
            current_time = current_row['timestamp']
            
            # فحص: هل البيانات الحالية طازجة؟ (لو آخر داتا مسجلة من ساعة، يبقى الجامع واقف!)
            time_diff_now = (datetime.utcnow() - current_time).total_seconds() / 60
            # ملاحظة: SQLite يخزن UTC عادة، تأكد من توافق توقيت جهازك
            # لو الفرق بين "الآن" وآخر داتا في المخزن أكبر من 15 دقيقة، يبقى فيه مشكلة
            if time_diff_now > 20: 
                print(f"   ⚠️ {symbol}: Stale Data! Last update was {int(time_diff_now)} mins ago. Check Collector.")
                continue

            # 3. البحث عن النقطة القديمة (Past Point) بالوقت وليس بالترتيب
            target_time = current_time - timedelta(minutes=LOOKBACK_MINUTES)
            
            # فلتر لإيجاد أقرب صف للوقت المستهدف (بحد أقصى تسامح 10 دقائق)
            # نبحث عن الصفوف التي تقع في نافذة الوقت: (الهدف - 10 دقايق) إلى (الهدف + 10 دقايق)
            mask = (df['timestamp'] >= target_time - timedelta(minutes=TIME_TOLERANCE)) & \
                   (df['timestamp'] <= target_time + timedelta(minutes=TIME_TOLERANCE))
            
            candidates = df.loc[mask]
            
            if candidates.empty:
                print(f"   ⏳ {symbol}: Not enough history yet for comparison (Need ~60 mins).")
                continue
            
            # نأخذ أقرب وقت للهدف
            # (نحسب الفرق المطلق بين وقت كل صف والوقت المستهدف، ونأخذ الأقل)
            candidates['diff'] = abs(candidates['timestamp'] - target_time)
            past_row = candidates.sort_values('diff').iloc[0]

            # --- الآن الحسابات آمنة زمنياً 100% ---
            price_change = ((current_row['price'] - past_row['price']) / past_row['price']) * 100
            oi_change_pct = ((current_row['open_interest'] - past_row['open_interest']) / past_row['open_interest']) * 100
            oi_change_usd = current_row['open_interest'] - past_row['open_interest']
            ls_ratio = current_row['long_short_ratio']

            # --- المنطق المطور (لتفادي الفخاخ) ---
            signal_type = None
            emoji = ""
            
            # فخ الـ Aggressive Shorting:
            # لو السعر نزل + OI زاد.. لازم نتأكد إن L/S Ratio مش بيقع بقوة
            # لو L/S بيقل، معناها اللي بيفتح العقود هم الشورتات (الدببة) -> استمرار الهبوط
            # لو L/S ثابت أو بيزيد، معناها الحيتان بيجمعوا -> انعكاس محتمل
            
            ls_change = current_row['long_short_ratio'] - past_row['long_short_ratio']

            # 1. تجميع شرائي (Smart Absorption)
            # السعر نزل + سيولة زادت + L/S بيزيد أو ثابت (حيتان بيشتروا قدام بائعين التجزئة)
            if price_change < -0.5 and oi_change_pct > 1.5 and ls_change > -0.05:
                signal_type = "💎 SMART ABSORPTION (Buy Limit Walls)"
                emoji = "🟢 WHALE ENTRY"
            
            # 2. بيع هجومي (Aggressive Shorting - The Trap)
            # السعر نزل + سيولة زادت + L/S بيقل (شورتات جديدة بتدخل)
            elif price_change < -0.5 and oi_change_pct > 1.5 and ls_change < -0.1:
                signal_type = "🩸 AGGRESSIVE SHORTING (Trend Continuation)"
                emoji = "🔻 BEAR POWER"

            # 3. قوة اتجاه صاعد (Fuel)
            if price_change > 0.2 and oi_change_pct > 0.5 and ls_ratio > 1.0:
                signal_type = "🚀 BULLISH MOMENTUM"
                emoji = "🔥 PUMP"

            # الإرسال
            if signal_type and abs(oi_change_usd) > OI_THRESHOLD:
                # حساب الفارق الزمني الفعلي للتأكد في التقرير
                actual_time_diff = int((current_time - past_row['timestamp']).total_seconds() / 60)
                
                msg = f"""
{emoji} **{symbol}**

**Signal:** {signal_type}
⏱️ Actual Timeframe: {actual_time_diff} mins
---------------------------
💰 **Price:** ${current_row['price']:.4f} ({price_change:+.2f}%)
⚖️ **L/S Ratio:** {ls_ratio:.2f} (Change: {ls_change:+.2f})
🌊 **OI Change:** {oi_change_pct:+.2f}%
💵 **Net Flow:** ${oi_change_usd/1_000_000:+.2f}M
---------------------------
[Chart](https://www.tradingview.com/chart/?symbol=BINANCE:{symbol})
                """
                send_telegram_msg(msg)
                print(f"   📢 ALERT SENT for {symbol}!")
            else:
                print(f"   ✅ {symbol}: Neutral. (OI Chg: ${oi_change_usd/1_000_000:.1f}M)")

        conn.close()
    except Exception as e:
        print(f"❌ Analysis Error: {e}")

if __name__ == "__main__":
    send_telegram_msg("🤖 **Pro Analyzer Online:**\nTime-Logic Fixed + WAL Mode Active.")
    while True:
        analyze_market()
        print(f"💤 Waiting {ANALYSIS_INTERVAL}s...")
        time.sleep(ANALYSIS_INTERVAL)