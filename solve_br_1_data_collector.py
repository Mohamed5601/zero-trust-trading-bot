import pandas as pd
import os

DATA_FOLDER = 'market_data' # تأكد أن هذا هو اسم المجلد الصحيح عندك

def inspect_data():
    if not os.path.exists(DATA_FOLDER):
        print("❌ المجلد غير موجود!")
        return

    files = [f for f in os.listdir(DATA_FOLDER) if f.endswith('.csv')]
    print(f"📊 تقرير فحص الكميات والتواريخ لـ {len(files)} ملف:\n")
    print(f"{'اسم الملف':<25} | {'عدد الشموع':<10} | {'البداية':<20} | {'النهاية'}")
    print("-" * 80)

    for file in files:
        try:
            df = pd.read_csv(os.path.join(DATA_FOLDER, file))
            if df.empty:
                print(f"{file:<25} | ⚠️ فارغ!      | -                    | -")
                continue
                
            count = len(df)
            start = df['timestamp'].iloc[0]
            end = df['timestamp'].iloc[-1]
            
            # تلوين بسيط: لو العدد قليل جداً نضع علامة
            flag = "✅" if count > 1000 else "⚠️"
            
            print(f"{file:<25} | {count:<10} {flag} | {start:<20} | {end}")
        except Exception as e:
            print(f"❌ خطأ في قراءة {file}: {e}")

if __name__ == "__main__":
    inspect_data()