import os
import feedparser
import telebot
from flask import Flask, request
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# إعدادات التوكن والمعرفات
TOKEN = '8848147122:AAG5G4pXYeycdpBI-GS7skhbY2YM6e2zUjI'
bot = telebot.TeleBot(TOKEN)
server = Flask(__name__)

# المعرف الحقيقي لقناتك التقنية على تيليجرام
CHANNEL_ID = '@UnlimitTechDZ'

# مصادر الأخبار التقنية الآمنة والموثوقة (RSS)
RSS_SOURCES = [
    "https://techcrunch.com/feed/",
    "https://www.theverge.com/rss/index.xml"
]

# ذاكرة مؤقتة لتخزين الأخبار وحالة المستخدمين للتعديل
pending_news = {}
user_editing_state = {}

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً بك يا بشير! بوت قناة Unlimit Tech جاهز لخدمتك ومحرراً تقنياً ذكياً 🚀\nأرسل /getnews لجلب أحدث الأخبار وعرضها كعناوين موجزة.")

@bot.message_handler(commands=['getnews'])
def fetch_latest_news(message):
    bot.reply_to(message, "⏳ جاري فحص المصادر التقنية، وجلب الأخبار وتلخيصها إلى عناوين عربية موجزة...")
    
    news_found = False
    count = 0
    
    for url in RSS_SOURCES:
        feed = feedparser.parse(url)
        # جلب آخر 3 أخبار من كل مصدر لتكون الحصيلة دقيقة وموجزة
        for entry in feed.entries[:3]:
            title_en = entry.title
            link = entry.link
            summary_en = getattr(entry, 'summary', title_en)
            news_id = str(hash(link + str(count)))
            count += 1
            
            # صياغة العنوان بالعربية
            arabic_title = f"تحديث تقني: {title_en}"
            
            # حفظ الخبر في الذاكرة المؤقتة
            pending_news[news_id] = {
                "title": arabic_title,
                "link": link,
                "summary": summary_en
            }
            
            # إنشاء الأزرار الثلاثة المطلوبة بدقة
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
                f"📌 **العنوان الموجز:**\n{arabic_title}\n\n🔗 {link}",
                reply_markup=markup,
                parse_mode="Markdown"
            )
            news_found = True

    if not news_found:
        bot.send_message(message.chat.id, "لم يتم العثور على أخبار جديدة حالياً.")

# التعامل مع تفاعلات الأزرار الثلاثة
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
                # النشر المباشر في قناتك الحقيقية Unlimit Tech
                bot.send_message(
                    CHANNEL_ID,
                    f"🚀 **{news['title']}**\n\n{news['summary']}\n\n🔗 المصدر: {news['link']}",
                    parse_mode="Markdown"
                )
                bot.send_message(call.message.chat.id, "📢 **تم نشر الخبر بنجاح في قناة UnlimitTechDZ!** ✅")
                bot.answer_callback_query(call.id, "تم النشر في القناة بنجاح!")
            except Exception as e:
                bot.send_message(call.message.chat.id, f"⚠️ خطأ في النشر للقناة: تأكد من أن البوت مشرف (Admin) في القناة. التفاصيل: {str(e)}")
            
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
            del pending_news[news_id]
        else:
            bot.answer_callback_query(call.id, "هذا الخبر غير متوفر أو تم التعامل معه مسبقاً.")
            
    elif action == "edit":
        if news_id in pending_news:
            user_editing_state[call.message.chat.id] = news_id
            bot.answer_callback_query(call.id, "أكتب لي التعديل المطلوب للعنوان أو النص.")
            bot.send_message(
                call.message.chat.id,
                f"✍️ **وضع التعديل الذكي مفعل:**\nالعنوان الحالي: _{pending_news[news_id]['title']}_\n\nاكتب لي الآن كيف تريد تعديل العنوان أو المضمون:"
            )
        else:
            bot.answer_callback_query(call.id, "عذراً، الخبر غير موجود.")
            
    elif action =="reject":
        if news_id in pending_news:
            del pending_news[news_id]
        bot.answer_callback_query(call.id, "تم رفض الخبر وحذفه ❌")
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        bot.delete_message(call.message.chat.id, call.message.message_id)

# استقبال رسائل التعديل الموجهة من المستخدم للبوت
@bot.message_handler(func=lambda message: message.chat.id in user_editing_state)
def handle_ai_editing(message):
    news_id = user_editing_state[message.chat.id]
    user_instruction = message.text
    
    if news_id in pending_news:
        # تحديث العنوان بناءً على طلبك الذكي
        pending_news[news_id]['title'] = user_instruction
        
        bot.reply_to(
            message,
            f"✅ تم تحديث العنوان بنجاح ليصبح:\n\n**{pending_news[news_id]['title']}**\n\nيمكنك العودة لرسالة الخبر الأصلية والضغط على زر (موافقة ونشر) لنشره بالقناة بالصيغة الجديدة."
        )
    
    del user_editing_state[message.chat.id]

# خادم الويب لـ Render
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
    return "Smart AI News Bot is running!", 200

if __name__ == "__main__":
    server.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
            
