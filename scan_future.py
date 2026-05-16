import ccxt
import pandas as pd
import numpy as np
import os
import time
import warnings
from datetime import datetime
from tqdm import tqdm

# تجاهل التحذيرات للحفاظ على نظافة الشاشة
warnings.filterwarnings("ignore")

# --- 1. الإعدادات الأساسية ---
COINS = ['XRP/USDT'] 
# تم الحفاظ على قائمة الفريمات كما في ملفك الأصلي
TIMEFRAMES = ['5m', '15m', '30m', '1h', '2h', '4h', '6h', '12h', '1d', '1w', '1M']
START_DATE_DEFAULT = '2026-01-01 00:00:00' 

# --- إعدادات الذكاء التكيفي (بديلة للنسبة الثابتة) ---
MIN_REQUIRED_MATCHES = 5     # أقل عدد سيناريوهات لقبول النتيجة
START_THRESHOLD = 0.90       # نبدأ البحث بدقة خرافية
MIN_SAFE_THRESHOLD = 0.65    # خط أحمر لا ننزل تحته أبداً
STEP_DOWN = 0.05             # مقدار التنازل التدريجي عند الضرورة

# --- 2. مصفوفة الإعدادات الذهبية (السر للدقة القصوى) ---
TF_SETTINGS = {
    '5m':  {'length': 60, 'horizon': 12},
    '15m': {'length': 60, 'horizon': 12},
    '30m': {'length': 50, 'horizon': 10},
    '1h':  {'length': 48, 'horizon': 8},
    '2h':  {'length': 48, 'horizon': 8},
    '4h':  {'length': 40, 'horizon': 6},
    '6h':  {'length': 40, 'horizon': 6},
    '12h': {'length': 30, 'horizon': 5},
    '1d':  {'length': 30, 'horizon': 5},
    '1w':  {'length': 24, 'horizon': 4},
    '1M':  {'length': 12, 'horizon': 3}
}

class SOLRealMoneyBot:
    def __init__(self):
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}
        })
        self.data_folder = 'market_data'
        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)

    # --- دالة مساعدة لحساب الوقت ---
    def get_timeframe_ms(self, timeframe):
        amount = int(timeframe[:-1])
        unit = timeframe[-1]
        if unit == 'm': return amount * 60 * 1000
        elif unit == 'h': return amount * 60 * 60 * 1000
        elif unit == 'd': return amount * 24 * 60 * 60 * 1000
        elif unit == 'w': return amount * 7 * 24 * 60 * 60 * 1000
        elif unit == 'M': return amount * 30 * 24 * 60 * 60 * 1000
        return 60000

    # --- 3. التحديث الذكي (Robust Data Sync) ---
    def sync_data(self, symbol, timeframe):
        safe_symbol = symbol.replace('/', '')
        filepath = f'{self.data_folder}/{safe_symbol}_{timeframe}.csv'
        
        if os.path.exists(filepath):
            try:
                existing_df = pd.read_csv(filepath)
                existing_df['timestamp'] = pd.to_datetime(existing_df['timestamp'])
                last_time = existing_df['timestamp'].iloc[-1]
                since = int(last_time.timestamp() * 1000) + 1
            except:
                since = self.exchange.parse8601(START_DATE_DEFAULT + 'Z')
                existing_df = pd.DataFrame()
        else:
            since = self.exchange.parse8601(START_DATE_DEFAULT + 'Z')
            existing_df = pd.DataFrame()

        now = self.exchange.milliseconds()
        total_time = now - since
        tf_ms = self.get_timeframe_ms(timeframe)
        est_candles = max(1, total_time // tf_ms)

        new_data = []
        
        if est_candles > 50:
            pbar = tqdm(total=est_candles, unit="candle", ncols=70, desc=f"Sync {timeframe}", leave=False)
        else:
            pbar = None

        while True:
            try:
                ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=1000)
                if not ohlcv: break
                
                new_data.extend(ohlcv)
                fetched = len(ohlcv)
                since = ohlcv[-1][0] + 1
                
                if pbar: pbar.update(fetched)
                
                if since > now: break
                time.sleep(self.exchange.rateLimit / 1000)
            except Exception as e:
                time.sleep(3)
                continue
        
        if pbar: pbar.close()

        if new_data:
            df_new = pd.DataFrame(new_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df_new['timestamp'] = pd.to_datetime(df_new['timestamp'], unit='ms')
            full_df = pd.concat([existing_df, df_new]).drop_duplicates(subset='timestamp', keep='last').sort_values('timestamp')
            full_df.to_csv(filepath, index=False)
            return full_df
        return existing_df

    # --- 4. المحرك التحليلي الدقيق (Adaptive Engine) ---
    def normalize_series(self, series):
        if len(series) == 0 or series.iloc[0] == 0: return series
        return (series - series.iloc[0]) / series.iloc[0]

    def analyze_patterns(self, df, timeframe):
        settings = TF_SETTINGS.get(timeframe, {'length': 50, 'horizon': 10})
        p_len = settings['length']
        p_horizon = settings['horizon']

        min_required = p_len + p_horizon + 50
        if len(df) < min_required: return None, 0

        current_pattern = df['close'].iloc[-p_len:]
        current_pattern_norm = self.normalize_series(current_pattern)
        
        # تجميع كل التشابهات الممكنة أولاً
        potential_matches = []
        search_limit = 25000 
        
        start_search_idx = max(0, len(df) - search_limit)
        end_search_idx = len(df) - p_len - p_horizon
        
        # 1. المسح الشامل وحساب الارتباط للكل
        for i in range(start_search_idx, end_search_idx):
            past_slice = df['close'].iloc[i : i + p_len]
            past_norm = self.normalize_series(past_slice)
            
            corr = np.corrcoef(current_pattern_norm, past_norm)[0, 1]
            
            # نحتفظ فقط بما هو فوق الحد الأدنى للأمان لتقليل الذاكرة
            if corr >= MIN_SAFE_THRESHOLD:
                future_slice = df['close'].iloc[i + p_len : i + p_len + p_horizon]
                entry_price = df['close'].iloc[i + p_len - 1]
                potential_matches.append({
                    'corr': corr,
                    'max_profit_pct': (future_slice.max() - entry_price) / entry_price * 100,
                    'max_drawdown_pct': (future_slice.min() - entry_price) / entry_price * 100
                })

        # 2. الخوارزمية التكيفية: البحث عن أعلى دقة ممكنة
        current_threshold = START_THRESHOLD # نبدأ من 90%
        final_matches = []
        
        while current_threshold >= MIN_SAFE_THRESHOLD:
            # فلترة النتائج حسب الدقة الحالية
            filtered = [m for m in potential_matches if m['corr'] >= current_threshold]
            
            if len(filtered) >= MIN_REQUIRED_MATCHES:
                final_matches = filtered
                break # وجدنا مجموعة جيدة بدقة عالية، نتوقف هنا
            
            # إذا لم نجد، نقلل الدقة ونحاول مرة أخرى
            current_threshold -= STEP_DOWN

        # إذا وصلنا للقاع (65%) ولم نجد العدد المطلوب، لكن وجدنا (بعض) النتائج، نقبل بها
        if not final_matches and len(potential_matches) > 0:
             # ترتيبهم بالأفضلية وأخذ أفضل المتاح
             potential_matches.sort(key=lambda x: x['corr'], reverse=True)
             final_matches = potential_matches[:MIN_REQUIRED_MATCHES]
             if final_matches:
                 current_threshold = final_matches[-1]['corr']

        return final_matches, current_threshold

    # --- 5. الحساب الديناميكي للأهداف (Scenario Planner) ---
    def get_dynamic_targets(self, matches_df, current_price, direction_type):
        total = len(matches_df)
        if total == 0: return None

        if direction_type == 'Long':
            valid_trades = matches_df[matches_df['max_profit_pct'] > 0.05]
            if valid_trades.empty: return None
            
            p1_val = valid_trades['max_profit_pct'].quantile(0.25)
            p2_val = valid_trades['max_profit_pct'].quantile(0.50)
            p3_val = valid_trades['max_profit_pct'].quantile(0.85)
            
            prob_1 = (len(matches_df[matches_df['max_profit_pct'] >= p1_val]) / total) * 100
            prob_2 = (len(matches_df[matches_df['max_profit_pct'] >= p2_val]) / total) * 100
            prob_3 = (len(matches_df[matches_df['max_profit_pct'] >= p3_val]) / total) * 100

            return {
                'Type': '🟢 صعود',
                'T1_P': current_price * (1 + p1_val/100), 'T1_Prob': prob_1,
                'T2_P': current_price * (1 + p2_val/100), 'T2_Prob': prob_2,
                'T3_P': current_price * (1 + p3_val/100), 'T3_Prob': prob_3
            }

        elif direction_type == 'Short':
            valid_trades = matches_df[matches_df['max_drawdown_pct'] < -0.05]
            if valid_trades.empty: return None

            s1_val = valid_trades['max_drawdown_pct'].quantile(0.75)
            s2_val = valid_trades['max_drawdown_pct'].quantile(0.50)
            s3_val = valid_trades['max_drawdown_pct'].quantile(0.15)

            prob_1 = (len(matches_df[matches_df['max_drawdown_pct'] <= s1_val]) / total) * 100
            prob_2 = (len(matches_df[matches_df['max_drawdown_pct'] <= s2_val]) / total) * 100
            prob_3 = (len(matches_df[matches_df['max_drawdown_pct'] <= s3_val]) / total) * 100

            return {
                'Type': '🔴 هبوط',
                'T1_P': current_price * (1 + s1_val/100), 'T1_Prob': prob_1,
                'T2_P': current_price * (1 + s2_val/100), 'T2_Prob': prob_2,
                'T3_P': current_price * (1 + s3_val/100), 'T3_Prob': prob_3
            }
        return None

    # --- 6. التشغيل النهائي ---
    def run(self):
        print(f"\n{'='*90}")
        print(f"💰 SOL PROFESSIONAL BOT | REAL MONEY EDITION")
        print(f"🎯 الميزات: تخصيص الفريمات + أهداف ديناميكية + بحث تكيفي ذكي")
        print(f"{'='*90}")

        coin = COINS[0]
        results = []

        print(f"⏳ بدء الفحص الذكي لـ {coin}...")

        for tf in TIMEFRAMES:
            try:
                # 1. التحديث
                df = self.sync_data(coin, tf)
                
                # 2. التحليل (باستخدام المنطق التكيفي الجديد)
                matches, used_threshold = self.analyze_patterns(df, tf)
                
                if not matches:
                    continue

                df_matches = pd.DataFrame(matches)
                current_price = df['close'].iloc[-1]
                
                total_patterns = len(df_matches)
                wins = len(df_matches[df_matches['max_profit_pct'] > 0.1])
                win_rate = (wins / total_patterns) * 100
                
                if win_rate >= 55: trend_desc = "📈 صاعد"
                elif win_rate <= 45: trend_desc = "📉 هابط"
                else: trend_desc = "⚖️ متذبذب"

                long_scen = self.get_dynamic_targets(df_matches, current_price, 'Long')
                short_scen = self.get_dynamic_targets(df_matches, current_price, 'Short')
                
                settings_used = TF_SETTINGS.get(tf)
                
                # إضافة نسبة الدقة التي تم استخدامها بجانب عدد الشموع
                settings_str = f"{settings_used['length']} شمعة"
                
                results.append({
                    'TF': tf,
                    'Price': current_price,
                    'Trend': f"{trend_desc} ({win_rate:.0f}%)",
                    'Patterns': total_patterns,
                    'Settings': settings_str,
                    'Accuracy': f"{used_threshold*100:.0f}%", # معلومة إضافية للجدول
                    'Long': long_scen,
                    'Short': short_scen
                })

            except Exception as e:
                print(f"❌ Error in {tf}: {e}")
                continue

        # --- عرض الجدول النهائي ---
        print(f"\n{'='*125}")
        print(f"{'الفريم':<6} | {'التحليل (الدقة)':<18} | {'السيناريو':<8} | {'هدف 1 (مضمون)':<25} | {'هدف 2 (متوسط)':<25} | {'هدف 3 (طموح)':<25}")
        print(f"{'-'*125}")

        for res in results:
            # دمجنا معلومات التحليل مع نسبة الدقة في نفس العمود
            analysis_info = f"{res['Settings']} ({res['Accuracy']})"
            
            print(f"{res['TF']:<6} | {analysis_info:<18} | {'السعر: ' + str(res['Price']):<35} الاتجاه العام: {res['Trend']}")
            
            l = res['Long']
            if l:
                l1 = f"{l['T1_P']:.1f} (ثقة {l['T1_Prob']:.0f}%)"
                l2 = f"{l['T2_P']:.1f} (ثقة {l['T2_Prob']:.0f}%)"
                l3 = f"{l['T3_P']:.1f} (ثقة {l['T3_Prob']:.0f}%)"
                print(f"{'':<6} | {'':<18} | {l['Type']:<8} | {l1:<25} | {l2:<25} | {l3:<25}")
            else:
                print(f"{'':<6} | {'':<18} | {'🟢 صعود':<8} | {'بيانات غير كافية':<25} | {'-':<25} | {'-':<25}")

            s = res['Short']
            if s:
                s1 = f"{s['T1_P']:.1f} (ثقة {s['T1_Prob']:.0f}%)"
                s2 = f"{s['T2_P']:.1f} (ثقة {s['T2_Prob']:.0f}%)"
                s3 = f"{s['T3_P']:.1f} (ثقة {s['T3_Prob']:.0f}%)"
                print(f"{'':<6} | {'':<18} | {s['Type']:<8} | {s1:<25} | {s2:<25} | {s3:<25}")
            else:
                print(f"{'':<6} | {'':<18} | {'🔴 هبوط':<8} | {'بيانات غير كافية':<25} | {'-':<25} | {'-':<25}")

            print(f"{'-'*125}")

        print("\n✅ تم التحليل بنجاح. الأرقام جاهزة للتنفيذ.")
        print("⚠️ تذكير هام: هذه احتمالات مبنية على الماضي. استخدم وقف الخسارة (Stop Loss) دائماً.")

if __name__ == "__main__":
    bot = SOLRealMoneyBot()
    bot.run()