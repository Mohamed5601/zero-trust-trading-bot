import asyncio
import aiohttp
import feedparser
import google.generativeai as genai
from telegram import Bot
import sys
import ccxt.async_support as ccxt  # استخدام النسخة Async لضمان السرعة وعدم التوقف
import re
import logging
from collections import deque
from datetime import datetime, timedelta, timezone
from config import GEMINI_API_KEY, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

# ==========================================
# ⚙️ إعدادات المحلل الذكي (V4 - Immortal)
# ==========================================
CHOSEN_MODEL = 'gemini-flash-latest' 

# إعداد السجلات (Logging) لمراقبة البوت في الخلفية
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("bot_log.log"), logging.StreamHandler()]
)

# استخدام deque بدلاً من set لضمان حذف الأقدم (FIFO)
last_processed_links = deque(maxlen=500) 

RSS_SOURCES = [
    "https://cointelegraph.com/rss",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://bitcoinmagazine.com/.rss/full/",
    "https://decrypt.co/feed"
]

# إعداد Gemini مع نظام المحاولات المتكررة
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(CHOSEN_MODEL)

async def get_crypto_price(symbol):
    """ جلب السعر الحالي باستخدام النسخة Async من CCXT """
    if not symbol or symbol == "UNKNOWN":
        return None
    
    exchange = ccxt.binance({'enableRateLimit': True})
    try:
        symbol = symbol.upper().strip()
        ticker = await exchange.fetch_ticker(f"{symbol}/USDT")
        await exchange.close() # إغلاق الاتصال فوراً لتوفير الموارد
        return ticker['last']
    except Exception as e:
        logging.warning(f"⚠️ تعذر جلب سعر {symbol}: {e}")
        await exchange.close()
        return None

async def analyze_news_with_data(title, summary, source_name):
    """ تحليل الخبر مع التعامل مع قيود الـ API (Rate Limits) """
    prompt = f"""
    أنت خبير تداول خوارزمي "متشائم وواقعي" (Contrarian Trader).
    لديك خبر: "{title}"
    المصدر: {source_name}
    الملخص: {summary}

    مطلوب منك 3 أشياء (كن صريحاً وقاسياً في التحليل):
    
    1. **العملة (Symbol):** الرمز فقط (مثل BTC). لو غير موجود اكتب UNKNOWN.
    2. **الدرجة (Score):** من -10 لـ +10.
    3. **التقرير وكشف المستور (Report):**
      - حلل الخبر باختصار.
      - **(مهم جداً) فقرة "ما لا يخبرك به أحد":** اذكر الجانب السلبي أو الخفي. هل السيولة حقيقية؟ هل هو فخ تصريف؟ هل الخبر قديم والسوق امتصه؟ تكلم عن "تأثير السيولة" و "رسوم الغاز" بواقعية كما يفعل صناع السوق.

    ⚠️ التنسيق المطلوب بدقة:
    SYMBOL: [الرمز]
    SCORE: [الرقم]
    REPORT: [اكتب التحليل هنا ومعه فقرة الأسرار]
    """
    
    for attempt in range(3): # محاولة 3 مرات في حال وجود ضغط على الـ API
        try:
            response = await asyncio.to_thread(model.generate_content, prompt)
            return response.text
        except Exception as e:
            if "429" in str(e): # إذا تم الوصول للحد الأقصى للطلبات
                wait_time = (attempt + 1) * 30
                logging.warning(f"⏳ ضغط API (429). انتظار {wait_time} ثانية...")
                await asyncio.sleep(wait_time)
            else:
                logging.error(f"❌ خطأ Gemini: {e}")
                break
    return None

def parse_gemini_response(text):
    symbol = "UNKNOWN"
    score = 0
    report = text
    try:
        symbol_match = re.search(r"SYMBOL:\s*([A-Za-z0-9]+)", text)
        if symbol_match: symbol = symbol_match.group(1)
        score_match = re.search(r"SCORE:\s*([-+]?\d+)", text)
        if score_match: score = int(score_match.group(1))
        report_match = re.split(r"REPORT:\s*", text)
        if len(report_match) > 1: report = report_match[1]
    except Exception as e:
        logging.error(f"⚠️ خطأ في معالجة النص: {e}")
    return symbol, score, report
async def send_telegram(text):
    """ إرسال ذكي: يتعامل مع الرسائل الطويلة جداً ومع أخطاء التنسيق """
    bot = Bot(token=TELEGRAM_TOKEN)
    
    # 1. التأكد من طول الرسالة (الحد الأقصى لتيليجرام 4096)
    # سنقص النص عند 3900 حرف لنترك مساحة آمنة للتنسيق والروابط
    if len(text) > 3900:
        text = text[:3900] + "\n\n...(تم اختصار النص لطوله الشديد)"

    try:
        # المحاولة الأولى: إرسال بتنسيق Markdown
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text, parse_mode="Markdown", disable_web_page_preview=False)
    except Exception as e:
        logging.warning(f"⚠️ فشل التنسيق (Markdown)، يتم الإرسال كنص عادي. السبب: {e}")
        try:
            # المحاولة الثانية (خطة الطوارئ): إرسال النص بدون أي تنسيق لضمان وصول المعلومة
            # نقوم بإزالة الرموز التي قد تسبب مشاكل في هذه الحالة
            clean_text = text.replace("*", "").replace("_", "").replace("`", "")
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=clean_text)
        except Exception as e2:
            logging.error(f"❌ خطأ قاتل في إرسال تيليجرام: {e2}")

async def fetch_rss_feed(session, url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124"}
    try:
        async with session.get(url, headers=headers, timeout=20) as response:
            if response.status == 200:
                feed = feedparser.parse(await response.text())
                now_utc = datetime.now(timezone.utc)
                valid_entries = []
                for entry in feed.entries:
                    pub_time = None
                    if hasattr(entry, 'published_parsed'): pub_time = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                    elif hasattr(entry, 'updated_parsed'): pub_time = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
                    
                    if pub_time and (now_utc - pub_time) < timedelta(hours=6):
                        valid_entries.append(entry)
                return valid_entries
    except Exception as e:
        logging.debug(f"RSS Timeout/Error for {url}: {e}")
    return []

async def news_scanner():
    logging.info("🚀 انطلاق النظام المتكامل (Immortal Mode).")
    
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                for url in RSS_SOURCES:
                    entries = await fetch_rss_feed(session, url)
                    if not entries: continue
                    
                    source_name = url.split('.')[1].capitalize()
                    for entry in entries[:3]:
                        if entry.link not in last_processed_links:
                            last_processed_links.append(entry.link) # الإضافة للـ deque
                            
                            logging.info(f"📰 خبر جديد من {source_name}: {entry.title}")
                            
                            full_response = await analyze_news_with_data(entry.title, getattr(entry, 'summary', ''), source_name)
                            if not full_response: continue

                            symbol, score, report_text = parse_gemini_response(full_response)
                            
                            price_text = ""
                            if symbol != "UNKNOWN":
                                price = await get_crypto_price(symbol)
                                if price: price_text = f"\n💰 **السعر الحالي:** ${price:,.8f}"
                            
                            score_icon = "⚪️"
                            if score >= 7: score_icon = "🟢 🔥 إيجابي جداً"
                            elif score >= 3: score_icon = "🟢 إيجابي"
                            elif score <= -7: score_icon = "🔴 🩸 سلبي جداً"
                            elif score <= -3: score_icon = "🔴 سلبي"
                            
                            msg = (
                                f"📰 **NEWS ({source_name})**\n"
                                f"📊 **تقييم الخبر:** {score}/10 {score_icon}\n"
                                f"🪙 **العملة:** #{symbol} {price_text}\n"
                                f"{'-'*20}\n"
                                f"{report_text}\n"
                                f"\n🔗 [المصدر]({entry.link})"
                            )
                            
                            await send_telegram(msg)
                            await asyncio.sleep(20) # تنظيم التدفق لتجنب الحظر

                await asyncio.sleep(300) # فحص كل 5 دقائق

            except Exception as e:
                logging.critical(f"⚠️ خطأ غير متوقع في الحلقة الرئيسية: {e}")
                await asyncio.sleep(60)

if __name__ == '__main__':
    try:
        asyncio.run(news_scanner())
    except KeyboardInterrupt:
        logging.info("🛑 تم الإيقاف يدوياً.")