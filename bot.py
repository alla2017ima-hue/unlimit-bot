import os
import feedparser
import telebot
from flask import Flask, request
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = '8848147122:AAG5G4pXYeycdpBI-GS7skhbY2YM6e2zUjI'
bot = telebot.TeleBot(TOKEN)
server = Flask(__name__)

# قائمة مصادر الأخبار التقنية الآمنة والموثوقة (RSS)
RSS_SOURCES = [
    "https://techcrunch.com/feed/",
    "https://www.theverge.com/rss/index.xml"
]

# ذاكرة مؤقتة لحفظ الأخبار التي تم جلبها لمراجعتها
pending_news = {}

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً بك يا بشير! بوت Unlimit Tech يعمل بنظام المراقبة والموافقة المسبقة للأخبار 🚀\nأرسل /getnews لجلب أحدث الأخبار التقنية لمراجعتها.")

@bot.message_handler(commands=['getnews'])
def fetch_latest_news(message):
    bot.reply_to(message, "⏳ جاري فحص المصادر التقنية وجلب أحدث الأخبار الآمنة...")
    
    news_found = False
    for url in RSS_SOURCES:
        feed = feedparser.parse(url)
        if feed.entries:
            entry = feed.entries[0]
            title = entry.title
            link = entry.link
            news_id = str(hash(link))
            
            # حفظ الخبر في الذاكرة المؤقتة للمراجعة
            pending_news[news_id] = {"title": title, "link": link}
            
            # إنشاء الأزرار الثلاثة المطلوبة
            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton("✅ موافقة ونشر", callback_data=f"approve_{news_id}"),
                InlineKeyboardButton("✏️ تعديل", callback_data=f"edit_{news_id}")
            )
            markup.row(
                InlineKeyboardButton("❌ عدم نشر", callback_data=f"reject_{news_id}")
            )
            
            bot.send_message(
                message.chat.id,
                f"📰 **خبر تقني جديد مقترح:**\n\n{title}\n\n🔗 {link}",
                reply_markup=markup,
                parse_mode="Markdown"
            )
            news_found = True
            break

    if not news_found:
        bot.send_message(message.chat.id, "لم يتم العثور على أخبار جديدة حالياً.")

# التعامل مع تفاعلات الأزرار الثلاثة
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    data = call.data
    action, news_id = data.split("_", 1)
    
    if action == "approve":
        if news_id in pending_news:
            news = pending_news[news_id]
            bot.send_message(call.message.chat.id, f"📢 **تم النشر بنجاح في القناة:**\n\n{news['title']}\n{news['link']}")
            bot.answer_callback_query(call.id, "تمت الموافقة والنشر بنجاح! ✅")
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
            del pending_news[news_id]
        else:
            bot.answer_callback_query(call.id, "هذا الخبر لم يعد متوفراً أو تم التعامل معه مسبقاً.")
            
    elif action == "edit":
        bot.answer_callback_query(call.id, "أرسل لي التعديل أو العنوان الجديد الذي تريده وسأقوم بتحديثه.")
        bot.send_message(call.message.chat.id, "✍️ أكتب لي التعديل المطلوب لهذا الخبر الآن:")
        
    elif action == "reject":
        if news_id in pending_news:
            del pending_news[news_id]
        bot.answer_callback_query(call.id, "تم رفض الخبر وحذفه بنجاح ❌")
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        bot.delete_message(call.message.chat.id, call.message.message_id)

# إعدادات خادم الويب Flask الخاص بـ Render
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
    return "Bot is running with News Review System!", 200

if __name__ == "__main__":
    server.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
    
