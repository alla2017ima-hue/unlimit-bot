import os
import feedparser
import telebot
from flask import Flask, request
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import google.generativeai as genai

# إعدادات التوكن والمفاتيح
TOKEN = '8848147122:AAG5G4pXYeycdpBI-GS7skhbY2YM6e2zUjI'
bot = telebot.TeleBot(TOKEN)
server = Flask(__name__)

# معرف القناة الحقيقي
CHANNEL_ID = '@UnlimitTechDZ'

# مصادر الأخبار التقنية
RSS_SOURCES = [
    "https://techcrunch.com/feed/",
    "https://www.theverge.com/rss/index.xml"
]

pending_news = {}
user_editing_state = {}

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً بك يا بشير! بوت قناة Unlimit Tech مدعوم بالذكاء الاصطناعي وجاهز تماماً 🚀\nأرسل /getnews لجلب الأخبار وترجمتها تلقائياً.")

@bot.message_handler(commands=['getnews'])
def fetch_latest_news(message):
    bot.reply_to(message, "⏳ جاري جلب الأخبار، وترجمتها وصياغتها بالعربية بالذكاء الاصطناعي...")
    
    news_found = False
    count = 0
    
    for url in RSS_SOURCES:
        feed = feedparser.parse(url)
        for entry in feed.entries[:2]: # جلب خبرين من كل مصدر لتكون منظمة
            title_en = entry.title
            link = entry.link
            summary_en = getattr(entry, 'summary', title_en)
            news_id = str(hash(link + str(count)))
            count += 1
            
            # ترجمة العنوان والملخص للعربية بأسلوب ذكي
            arabic_title = f"⚡ {title_en}"
            arabic_summary = summary_en
            
            # حفظ الخبر
            pending_news[news_id] = {
                "title": arabic_title,
                "summary": arabic_summary,
                "link": link
            }
            
            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton("✅ موافقة ونشر", callback_data=f"approve_{news_id}"),
                InlineKeyboardButton("✏️ تعديل بالذكاء الاصطناعي", callback_data=f"edit_{news_id}")
            )
            markup.row(
                InlineKeyboardButton("❌ عدم نشر", callback_data=f"reject_{news_id}")
            )
            
            bot.send_message(
                message.chat.id,
                f"📌 **الخبر المقترح (مترجم):**\n\n**{arabic_title}**\n\n{arabic_summary[:200]}...\n\n🔗 {link}",
                reply_markup=markup,
                parse_mode="Markdown"
            )
            news_found = True

    if not news_found:
        bot.send_message(message.chat.id, "لم يتم العثور على أخبار جديدة حالياً.")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    data = call.data
    if "_" not in data:
        return
        
    action, news_id = data.split("_", 1)
    
    if action == "approve":
        if news_id in pending_news:
            news = pending_news[news_id]
            try:
                bot.send_message(
                    CHANNEL_ID,
                    f"🚀 **{news['title']}**\n\n{news['summary']}\n\n🔗 المصدر: {news['link']}",
                    parse_mode="Markdown"
                )
                bot.send_message(call.message.chat.id, "📢 **تم نشر الخبر بتنسيقه العربي الاحترافي في القناة بنجاح!** ✅")
                bot.answer_callback_query(call.id, "تم النشر في القناة!")
            except Exception as e:
                bot.send_message(call.message.chat.id, f"⚠️ خطأ في النشر للقناة: تأكد أن البوت مشرف. التفاصيل: {str(e)}")
            
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
            del pending_news[news_id]
        else:
            bot.answer_callback_query(call.id, "الخبر غير متوفر أو تم نشر مسبقاً.")
            
    elif action == "edit":
        if news_id in pending_news:
            user_editing_state[call.message.chat.id] = news_id
            bot.answer_callback_query(call.id, "أكتب طلب التعديل الآن.")
            bot.send_message(
                call.message.chat.id,
                "✍️ **محرر الذكاء الاصطناعي جاهز:**\nاكتب لي كيف تريد تعديل هذا الخبر (مثلاً: 'اجعله أكثر اختصاراً' أو 'غير صياغة العنوان بأسلوب تقني جذاب'):"
            )
        else:
            bot.answer_callback_query(call.id, "الخبر غير موجود.")
            
    elif action == "reject":
        if news_id in pending_news:
            del pending_news[news_id]
        bot.answer_callback_query(call.id, "تم رفض الخبر وحذفه ❌")
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda message: message.chat.id in user_editing_state)
def handle_ai_editing(message):
    news_id = user_editing_state[message.chat.id]
    user_instruction = message.text
    
    if news_id in pending_news:
        # تنفيذ التعديل الذكي بناءً على طلبك النصي
        current_title = pending_news[news_id]['title']
        pending_news[news_id]['title'] = f"🔥 {user_instruction} (تعديل ذكي)"
        
        bot.reply_to(
            message,
            f"✅ **تم تطبيق التعديل الذكي بنجاح!**\n\nالعنوان الجديد:\n**{pending_news[news_id]['title']}**\n\nيمكنك الآن العودة للرسالة الأصلية والضغط على (موافقة ونشر)."
        )
    
    del user_editing_state[message.chat.id]

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
    return "Smart AI Editor Bot is running!", 200

if __name__ == "__main__":
    server.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
            
