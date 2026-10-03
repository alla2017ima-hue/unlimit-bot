import os
import feedparser
import telebot
from flask import Flask, request
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# إعدادات التوكن والمعرفات
TOKEN = '8848147122:AAG5G4pXYeycdpBI-GS7skhbY2YM6e2zUjI'
bot = telebot.TeleBot(TOKEN)
server = Flask(__name__)

CHANNEL_ID = '@UnlimitTechDZ'

# مصادر تقنية عربية + مصادر متخصصة في التطبيقات والعروض المجانية
RSS_SOURCES = [
    "https://www.tech-wd.com/wd/feed/",          # عالم التقنية
    "https://www.ardroid.com/feed/",              # أردرويد (خاص بتطبيقات وأندرويد)
    "https://www.unlimit-tech.com/blog/feed/",    # التقنية بلا حدود
    "https://sultantec.com/feed/"                  # سلطان تك (أخبار وبرامج وتطبيقات)
]

# كلمات مفتاحية محظورة لضمان نظافة المحتوى وخلوه تماماً من أي شيء غير لائق أو مخالف
BLOCKED_WORDS = ['18+', 'adult', 'مخل', 'خارج عن الاداب', 'فنان', 'مشاهير', 'برج', 'أبراج', 'مسلسلات', 'أفلام']

pending_news = {}
user_editing_state = {}
seen_links = set()

def is_clean_tech_content(title):
    """دالة للتأكد من أن الخبر تقني بحت وخالٍ تماماً من أي محتوى غير لائق"""
    title_lower = title.lower()
    for word in BLOCKED_WORDS:
        if word in title_lower:
            return False
    return True

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "أهلاً بك يا بشير! بوت قناة Unlimit Tech للمحتوى التقني والتطبيقات المجانية جاهز 🚀\nأرسل /getnews لجلب أحدث البرامج، العروض، والتطبيقات.")

@bot.message_handler(commands=['getnews'])
def fetch_latest_news(message):
    bot.reply_to(message, "⏳ جاري فحص المصادر التقنية وجلب أحدث التطبيقات، البرامج، والعروض الحصرية...")
    
    news_found_count = 0
    count = 0
    
    for url in RSS_SOURCES:
        feed = feedparser.parse(url)
        # جلب آخر 6 مقالات من كل مصدر لضمان حصيلة كبيرة ومنوعة
        for entry in feed.entries[:6]:
            title = entry.title
            link = entry.link
            
            # فحص خلو المحتوى من التكرار أو الكلمات غير المرغوبة
            if link in seen_links:
                continue
                
            if not is_clean_tech_content(title):
                continue
                
            news_id = str(hash(link + str(count)))
            count += 1
            
            seen_links.add(link)
            
            pending_news[news_id] = {
                "title": title,
                "link": link
            }
            
            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton("✅ موافقة ونشر", callback_data=f"approve_{news_id}"),
                InlineKeyboardButton("✏️ تعديل العنوان", callback_data=f"edit_{news_id}")
            )
            markup.row(
                InlineKeyboardButton("❌ عدم نشر", callback_data=f"reject_{news_id}")
            )
            
            # تمييز العروض والتطبيقات إن وجدت في العنوان
            prefix_tag = "📱 تطبيق / عرض:" if "تطبيق" in title or "عرض" in title or "مجاناً" in title else "📌 مقال تقني:"
            
            bot.send_message(
                message.chat.id,
                f"{prefix_tag}\n\n**{title}**\n\n🔗 {link}",
                reply_markup=markup,
                parse_mode="Markdown"
            )
            news_found_count += 1

    if news_found_count == 0:
        bot.send_message(message.chat.id, "لا توجد مقالات جديدة حالياً. انتظر قليلاً ريثما يتم رصد عروض أو برامج جديدة.")
    else:
        bot.send_message(message.chat.id, f"✅ تم العثور على {news_found_count} عنصراً جديداً (تطبيقات، برامج، وأخبار تقنية نظيفة)!")

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
                    f"🚀 **{news['title']}**\n\n🔗 {news['link']}",
                    parse_mode="Markdown"
                )
                bot.send_message(call.message.chat.id, "📢 **تم نشر المحتوى في قناة UnlimitTechDZ بنجاح!** ✅")
                bot.answer_callback_query(call.id, "تم النشر في القناة!")
            except Exception as e:
                bot.send_message(call.message.chat.id, f"⚠️ خطأ في النشر: تأكد أن البوت مشرف في القناة. التفاصيل: {str(e)}")
            
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
            del pending_news[news_id]
        else:
            bot.answer_callback_query(call.id, "العنصر غير متوفر أو تم التعامل معه مسبقاً.")
            
    elif action == "edit":
        if news_id in pending_news:
            user_editing_state[call.message.chat.id] = news_id
            bot.answer_callback_query(call.id, "أرسل التعديل الآن.")
            bot.send_message(
                call.message.chat.id,
                "✍️ **تعديل العنوان:**\nاكتب العنوان الجديد الذي تريده لهذا التطبيق أو المقال وسأعتمده فوراً:"
            )
        else:
            bot.answer_callback_query(call.id, "العنصر غير موجود.")
            
    elif action == "reject":
        if news_id in pending_news:
            del pending_news[news_id]
        bot.answer_callback_query(call.id, "تم رفض العنصر وحذفه ❌")
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda message: message.chat.id in user_editing_state)
def handle_text_editing(message):
    news_id = user_editing_state[message.chat.id]
    new_text = message.text
    
    if news_id in pending_news:
        pending_news[news_id]['title'] = new_text
        bot.reply_to(
            message,
            f"✅ **تم تحديث العنوان إلى:**\n\n**{new_text}**\n\nيمكنك الآن العودة للرسالة الأصلية والضغط على زر (موافقة ونشر)."
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
    return "Tech Apps Bot is running!", 200

if __name__ == "__main__":
    server.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
