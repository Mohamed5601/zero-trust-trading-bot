# notifier.py
import requests
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

def send_telegram_msg(message):
    """ دالة ترسل رسالة نصية إلى تليجرام """
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown" # عشان نقدر نستخدم الخط العريض والروابط
        }
        requests.post(url, json=payload, timeout=5)
        print("📨 Notification sent to Telegram!")
    except Exception as e:
        print(f"⚠️ Failed to send Telegram message: {e}")

# تجربة سريعة عشان نتأكد إن البوت شغال
if __name__ == "__main__":
    send_telegram_msg("🚀 **Test Message:** البوت جاهز للعمل يا ريس!")