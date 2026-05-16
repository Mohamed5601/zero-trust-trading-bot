# database.py (Production Ready - WAL Mode)
import sqlite3
from config import DB_NAME

def create_connection():
    """ إنشاء اتصال مع تفعيل وضع WAL لمنع مشاكل القفل """
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME, timeout=10) # مهلة 10 ثواني
        # تفعيل وضع WAL للسماح بالقراءة والكتابة المتزامنة
        conn.execute('PRAGMA journal_mode=WAL;')
        # جعل النتائج تعود كقاموس (Dictionary) لسهولة التعامل مع الأسماء
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"❌ Database connection error: {e}")
    return conn

def init_db():
    conn = create_connection()
    if conn is not None:
        cursor = conn.cursor()
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS market_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            symbol TEXT NOT NULL,
            price REAL,
            open_interest REAL,
            open_interest_amount REAL,
            funding_rate REAL,
            volume_24h REAL,
            long_short_ratio REAL
        );
        """
        cursor.execute(create_table_sql)
        # إنشاء Index على الوقت والعملة لتسريع البحث جداً
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_symbol_time ON market_metrics (symbol, timestamp);")
        
        conn.commit()
        conn.close()
        print(f"✅ Database {DB_NAME} (WAL Mode) initialized.")
    else:
        print("Error! Cannot create the database connection.")

def insert_market_data(data):
    conn = create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            sql = ''' INSERT INTO market_metrics(symbol, price, open_interest, open_interest_amount, funding_rate, volume_24h, long_short_ratio)
                      VALUES(?,?,?,?,?,?,?) '''
            cursor.execute(sql, data)
            conn.commit()
        except Exception as e:
            print(f"⚠️ DB Write Error: {e}")
        finally:
            conn.close()