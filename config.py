# config.py

# قائمة العملات التي نريد مراقبتها (رموز العقود الآجلة في باينانس)
SYMBOLS = [
    # --- الكبار (البوصلة) ---
    'BTCUSDT',   # عشان نعرف اتجاه السوق العام
    'ETHUSDT',   # قائد العملات البديلة
    'SOLUSDT',   # أسرع عملة قوية حالياً

    # --- صواريخ الأرباح (Meme Coins) ---
    # دي العملات اللي بتعمل 10% و 20% في اليوم (سر النمو)
    'BNBUSDT',  
  #  '1000SHIBUSDT',
  #  '1000BONKUSDT', 
  #  '1000FLOKIUSDT',
  #  'WIFUSDT',   # عملة قوية جداً على سولانا

    # --- مشاريع قوية وترند (Growth) ---
    # عملات مشروعها قوي وسيولتها عالية
  #  'SUIUSDT',   # ترند قوي جداً الأيام دي
    'XRPUSDT',   # حركتها عنيفة لما بتتحرك
  #  'ADAUSDT',
  #  'AVAXUSDT',
  #  'NEARUSDT'
]

# --- 1. إعدادات التليجرام ---
TELEGRAM_TOKEN = ""
TELEGRAM_CHAT_ID = ""

# الفاصل الزمني بين كل سحبة بيانات (بالثواني)
# 300 ثانية = 5 دقائق
FETCH_INTERVAL = 300 

# اسم ملف قاعدة البيانات
DB_NAME = 'market_data.db'

# --- إعدادات الأخبار والذكاء الاصطناعي ---
# مفتاح CryptoPanic (المصدر)
CRYPTOPANIC_TOKEN = ""


GEMINI_API_KEY = ""

# كلمات مفتاحية لو الخبر احتوى عليها نعتبره هام جداً (اختياري)
IMPORTANT_KEYWORDS = ['Binance', 'SEC', 'ETF', 'Rate Cut', 'Inflation', 'Powell']

# ضع مفاتيح Bybit هنا
BINANCE_API_KEY = "مفتاح_باي_بت_الجديد"    # سميناها BINANCE في الكود القديم، عادي اترك الاسم كما هو وضع القيمة الجديدة
BINANCE_SECRET_KEY = "مفتاح_السر_الجديد"

# مبلغ التداول لكل رمز (دولار)
TRADE_AMOUNT_USDT = 1000
TRADE_AMOUNT_USDT = 150
