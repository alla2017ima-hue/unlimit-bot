import os
import time
from datetime import datetime
import pytz
import feedparser
import requests
import telebot
from flask import Flask, request
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from apscheduler.schedulers.background import BackgroundScheduler

# إعدادات التوكن والمعرفات
TOKEN = '8848147122:AAG5G4pXYeycdpBI-GS7skhbY2YM6e2zUjI'
bot = telebot.TeleBot(TOKEN)
server = Flask(__name__)

CHANNEL_ID = '@UnlimitTechDZ'

# ربط حساب ShrinkMe الخاص بك عبر الـ API Token
SHRINKME_API_TOKEN = '896319677a1627b715581ada979db092b8961386'

def shorten_link(original_link):
    """دالة لاختصار الروابط تلقائياً عبر حسابك في ShrinkMe لجلب الأرباح"""
    try:
        api_url = f"https://shrinkme.io/api?api={SHRINKME_API_TOKEN}&url={original_link}"
        response = requests.get(api_url, timeout=10)
        data = response.json()
        if data.get("status") == "success":
            return data.get("shortenedUrl")
    except Exception as e:
        print(f"Error shortening link: {e}")
    return original_link

# توقيت الجزائر لضبط جدول النشر بدقة
ALGERIA_TZ = pytz.timezone('Africa/Algiers')

# مصادر الأخبار التقنية والتطبيقات
RSS_SOURCES = [
    "https://www.tech-wd.com/wd/feed/",            # 1. عالم التقنية
    "https://www.ardroid.com/feed/",                # 2. أردرويد
    "https://www.unlimit-tech.com/blog/feed/",      # 3. التقنية بلا حدود
    "https://sultantec.com/feed/",                    # 4. سلطان تك
    "https://aitnews.com/feed/",                    # 5. البوابة العربية للأخبار التقنية
    "https://www.iphoneislam.com/feed",             # 6. آي فون الإسلام
    "https://www.saudimax.com/feed/",               # 7. سعودي مكس
    "https://www.yallatech.net/feed/",              # 8. يلا تك
    "https://www.MekkanoTech.com/feed/",            # 9. مكنو تك
    "https://www.tsuut.com/feed/",                  # 10. صوت التقنية
    "https://www.th3professional.com/feed",         # 11. محترفو الشرح
    "https://www.computer-wd.com/feed/"             # 12. عالم الكمبيوتر
]

# كلمات مفتاحية محظورة لضمان نظافة المحتوى
BLOCKED_WORDS = ['18+', 'adult', 'مخل', 'خارج عن الاداب', 'فنان', 'مشاهير', 'برج', 'أبراج', 'مسلسلات', 'أفلام', 'برجك']

seen_links = set()
pending_manual_news = {}

def is_clean_tech_content(title):
    title_lower = title.lower()
    for word in BLOCKED_WORDS:
        if word in title_lower:
            return False
    return True

def auto_fetch_and_publish():
    """النشر المباشر التلقائي في أوقات الذروة مع اختصار الروابط لجلب الأرباح"""
    now = datetime.now(ALGERIA_TZ)
    current_hour = now.hour
    
    # فترات الذروة: الصباحية (6 إلى 12) والمسائية (18 إلى 00)
    is_morning_shift = (6 <= current_hour < 12)
    is_evening_shift = (18 <= current_hour < 24)
    
    if not (is_morning_shift or is_evening_shift):
        return
        
    published_count = 0
    
    for url in RSS_SOURCES:
        try:
            feed = feedparser.parse(url)
            # جلب أحدث خبر من كل مصدر في كل دورة تلقائية
            for entry in feed.entries[:1]:
                title = entry.title
                original_link = entry.link
                
                if original_link in seen_links:
                    continue
                if not is_clean_tech_content(title):
                    continue
                    
                seen_links.add(original_link)
                monetized_link = shorten_link(original_link)
                
                prefix_tag = "📱 تطبيق / عرض مدفوع صار مجاناً:" if any(w in title for w in ["تطبيق", "عرض", "مجاناً", "لعبة", "برنامج", "مدفوع"]) else "🚀 جديد التقنية:"
                
                # النشر المباشر في القناة دون الحاجة لأي تدخل منك
                bot.send_message(
                    CHANNEL_ID,
                    f"{prefix_tag}\n\n**{title}**\n\n🔗 {monetized_link}",
                    parse_mode="Markdown"
                )
                published_count += 1
                time.sleep(3)
                
                # نشر 3 عناصر كحد أقصى في كل جولة تلقائية حتى لا نغرق القناة
                if published_count >= 3:
                    break
        except Exception as e:
            continue

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً بك يا بشير! بوت UnlimitTechDZ يعمل بنظام الطيار الآلي (النشر التلقائي واختصار الروابط) 🚀")

@bot.message_handler(commands=['getnews'])
def manual_fetch_news(message):
    bot.reply_to(message, "⚡ جاري فحص المصادر يدوياً...")
    
    news_found_count = 0
    count = 0
    
    for url in RSS_SOURCES:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:2]:
                title = entry.title
                original_link = entry.link
                
                if original_link in seen_links:
                    continue
                if not is_clean_tech_content(title):
                    continue
                    
                seen_links.add(original_link)
                monetized_link = shorten_link(original_link)
                
                news_id = str(hash(original_link + str(count)))
                count += 1
                
                prefix_tag = "📱 تطبيق / عرض مدفوع صار مجاناً:" if any(w in title for w in ["تطبيق", "عرض", "مجاناً", "لعبة", "برنامج", "مدفوع"]) else "🚀 جديد التقنية:"
                pending_manual_news[news_id] = {
                    "text": f"{prefix_tag}\n\n**{title}**\n\n🔗 {monetized_link}"
                }
                
                markup = InlineKeyboardMarkup()
                markup.row(
                    InlineKeyboardButton("✅ نشر فوري بالقناة", callback_data=f"approve_{news_id}"),
                    InlineKeyboardButton("❌ إلغاء", callback_data=f"reject_{news_id}")
                )
                
                bot.send_message(
                    message.chat.id,
                    f"📌 **عنصر مقترح:**\n\n{pending_manual_news[news_id]['text']}",
                    reply_markup=markup,
                    parse_mode="Markdown"
                )
                news_found_count += 1
        except:
            continue

    if news_found_count == 0:
        bot.send_message(message.chat.id, "لا توجد مقالات جديدة حالياً.")
    else:
        bot.send_message(message.chat.id, f"✅ تم جلب {news_found_count} عنصراً للمراجعة.")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    data = call.data
    if "_" not in data:
        return
    action, news_id = data.split("_", 1)
    
    if action == "approve":
        if news_id in pending_manual_news:
            post_content = pending_manual_news[news_id]['text']
            try:
                bot.send_message(CHANNEL_ID, post_content, parse_mode="Markdown")
                bot.answer_callback_query(call.id, "✅ تم النشر في القناة بنجاح!")
                bot.send_message(call.message.chat.id, "📢 تم نشر الخبر في قناة UnlimitTechDZ!")
            except Exception as e:
                bot.answer_callback_query(call.id, "⚠️ فشل النشر، تأكد أن البوت مشرف في القناة.")
            
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
            del pending_manual_news[news_id]
        else:
            bot.answer_callback_query(call.id, "انتهت صلاحية هذا العنصر.")
            
    elif action == "reject":
        if news_id in pending_manual_news:
            del pending_manual_news[news_id]
        bot.answer_callback_query(call.id, "تم الحذف ❌")
        bot.delete_message(call.message.chat.id, call.message.message_id)

# الجدول الزمني التلقائي: يفحص وينشر تلقائياً كل ساعة في أوقات الذروة
scheduler = BackgroundScheduler(timezone=ALGERIA_TZ)
scheduler.add_job(auto_fetch_and_publish, 'interval', hours=1)
scheduler.start()

@server.route('/' + TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@server.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url='https://unlimit-bot.onrender.com/' + TOKEN)
    return "Auto-Pilot Monetized Bot is running!", 200

if __name__ == "__main__":
    server.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
                
