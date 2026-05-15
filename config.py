# config.py

# قائمة العملات التي نريد مراقبتها (رموز العقود الآجلة في باينانس)
SYMBOLS = [
    'BTCUSDT',
    'ETHUSDT',
    'SOLUSDT',
    'XRPUSDT',
    '1000PEPEUSDT'  # اخترنا بيبي لأن حركتها قوية
]

# --- 1. إعدادات التليجرام ---
TELEGRAM_TOKEN = "YOUR_KEY_HERE"
TELEGRAM_CHAT_ID = "YOUR_KEY_HERE"

# الفاصل الزمني بين كل سحبة بيانات (بالثواني)
# 300 ثانية = 5 دقائق
FETCH_INTERVAL = 300 

# اسم ملف قاعدة البيانات
DB_NAME = 'market_data.db'

# --- إعدادات الأخبار والذكاء الاصطناعي ---
# مفتاح CryptoPanic (المصدر)
CRYPTOPANIC_TOKEN = "YOUR_KEY_HERE"


GEMINI_API_KEY = "YOUR_KEY_HERE"

# كلمات مفتاحية لو الخبر احتوى عليها نعتبره هام جداً (اختياري)
IMPORTANT_KEYWORDS = ['Binance', 'SEC', 'ETF', 'Rate Cut', 'Inflation', 'Powell']

# ضع مفاتيح Bybit هنا
BINANCE_API_KEY = "مفتاح_باي_بت_الجديد"    # سميناها BINANCE في الكود القديم، عادي اترك الاسم كما هو وضع القيمة الجديدة
BINANCE_SECRET_KEY = "مفتاح_السر_الجديد"
TRADE_AMOUNT_USDT = 500
