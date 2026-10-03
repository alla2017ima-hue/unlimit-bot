import os
import time
from datetime import datetime
import pytz
import feedparser
import telebot
from flask import Flask, request
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from apscheduler.schedulers.background import BackgroundScheduler

# إعدادات التوكن والمعرفات
TOKEN = '8848147122:AAG5G4pXYeycdpBI-GS7skhbY2YM6e2zUjI'
bot = telebot.TeleBot(TOKEN)
server = Flask(__name__)

CHANNEL_ID = '@UnlimitTechDZ'

# توقيت الجزائر لضبط جدول النشر بدقة
ALGERIA_TZ = pytz.timezone('Africa/Algiers')

# أكثر من 15 مصدراً ضخماً (أخبار، برامج، وتطبيقات مجانية ومأجورات أصبحت مجانية)
RSS_SOURCES = [
    "https://www.tech-wd.com/wd/feed/",            # 1. عالم التقنية
    "https://www.ardroid.com/feed/",                # 2. أردرويد (أندرويد وتطبيقات)
    "https://www.unlimit-tech.com/blog/feed/",      # 3. التقنية بلا حدود
    "https://sultantec.com/feed/",                    # 4. سلطان تك
    "https://aitnews.com/feed/",                    # 5. البوابة العربية للأخبار التقنية
    "https://www.iphoneislam.com/feed",             # 6. آي فون الإسلام (آبل وبرامج)
    "https://www.saudimax.com/feed/",               # 7. سعودي مكس
    "https://www.yallatech.net/feed/",              # 8. يلا تك
    "https://www.MekkanoTech.com/feed/",            # 9. مكنو تك (شروحات وتطبيقات)
    "https://www.tsuut.com/feed/",                  # 10. صوت التقنية
    "https://www.th3professional.com/feed",         # 11. محترفو الشرح
    "https://www.computer-wd.com/feed/"             # 12. عالم الكمبيوتر (برامج وشروحات مفيدة)
]

# كلمات مفتاحية محظورة لضمان نظافة المحتوى وخلوه تماماً
BLOCKED_WORDS = ['18+', 'adult', 'مخل', 'خارج عن الاداب', 'فنان', 'مشاهير', 'برج', 'أبراج', 'مسلسلات', 'أفلام', 'برجك']

seen_links = set()

def is_clean_tech_content(title):
    title_lower = title.lower()
    for word in BLOCKED_WORDS:
        if word in title_lower:
            return False
    return True

def auto_fetch_and_publish():
    """وظيفة يتم تشغيلها تلقائياً في أوقات الذروة لجلب ونشر الأخبار مباشرة في القناة"""
    now = datetime.now(ALGERIA_TZ)
    current_hour = now.hour
    
    # التحقق هل الوقت ضمن فترات الذروة المحددة (6:00 إلى 12:00) أو (18:00 إلى 00:00)
    is_morning_shift = (6 <= current_hour < 12)
    is_evening_shift = (18 <= current_hour < 24)
    
    if not (is_morning_shift or is_evening_shift):
        return # خارج أوقات العمل التلقائي، راحة للسيستم والقناة
        
    published_count = 0
    
    for url in RSS_SOURCES:
        try:
            feed = feedparser.parse(url)
            # أخذ أحدث خبرين من كل مصدر في كل دورة تلقائية لكي لا نغرق القناة دفعة واحدة بل بشكل متواصل
            for entry in feed.entries[:2]:
                title = entry.title
                link = entry.link
                
                if link in seen_links:
                    continue
                if not is_clean_tech_content(title):
                    continue
                    
                seen_links.add(link)
                
                prefix_tag = "📱 تطبيق / عرض مدفوع صار مجاناً:" if any(w in title for w in ["تطبيق", "عرض", "مجاناً", "لعبة", "برنامج", "مدفوع"]) else "🚀 جديد التقنية:"
                
                # النشر التلقائي المباشر في القناة
                bot.send_message(
                    CHANNEL_ID,
                    f"{prefix_tag}\n\n**{title}**\n\n🔗 {link}",
                    parse_mode="Markdown"
                )
                published_count += 1
                time.sleep(2) # فاصل صغير بين كل رسالة وأخرى لتجنب حظر تليجرام
                
                if published_count >= 5: # نشر 5 عناصر في كل جولة تلقائية ثم التوقف انتظاراً للجولة التالية
                    break
        except Exception as e:
            continue

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً بك يا بشير! بوت UnlimitTechDZ يعمل بنظام النشر التلقائي في أوقات الذروة (صباحاً ومساءً) 🚀\nيمكنك طلب الأخبار يدوياً في أي وقت عبر الأمر: /getnews")

@bot.message_handler(commands=['getnews'])
def manual_fetch_news(message):
    bot.reply_to(message, "⚡ تم إيقاظ البوت! جاري فحص أكثر من 15 مصدراً وجلب حصيلة فورية وكبيرة من التطبيقات والأخبار...")
    
    news_found_count = 0
    count = 0
    
    for url in RSS_SOURCES:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:3]:
                title = entry.title
                link = entry.link
                
                if link in seen_links:
                    continue
                if not is_clean_tech_content(title):
                    continue
                    
                seen_links.add(link)
                news_id = str(hash(link + str(count)))
                count += 1
                
                markup = InlineKeyboardMarkup()
                markup.row(
                    InlineKeyboardButton("✅ نشر فوري بالقناة", callback_data=f"approve_{news_id}"),
                    InlineKeyboardButton("❌ إلغاء", callback_data=f"reject_{news_id}")
                )
                
                bot.send_message(
                    message.chat.id,
                    f"📌 **عنصر مقترح:**\n\n**{title}**\n\n🔗 {link}",
                    reply_markup=markup,
                    parse_mode="Markdown"
                )
                news_found_count += 1
        except:
            continue

    if news_found_count == 0:
        bot.send_message(message.chat.id, "جميع المقالات الحديثة تم نشرها مسبقاً. البوت سيعود لجلب الجديد تلقائياً في وقته.")
    else:
        bot.send_message(message.chat.id, f"✅ تم جلب {news_found_count} عنصراً للمراجعة اليدوية.")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    data = call.data
    if "_" not in data:
        return
    action, news_id = data.split("_", 1)
    if action == "approve":
        bot.answer_callback_query(call.id, "تم النشر!")
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    elif action == "reject":
        bot.answer_callback_query(call.id, "تم الحذف")
        bot.delete_message(call.message.chat.id, call.message.message_id)

# إعداد جدول التشغيل التلقائي (Background Scheduler)
scheduler = BackgroundScheduler(timezone=ALGERIA_TZ)
# فحص المصادر ونشر الجديد تلقائياً كل ساعة خلال أوقات العمل المحددة
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
    return "Auto-Pilot Tech Bot is running!", 200

if __name__ == "__main__":
    server.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
    
