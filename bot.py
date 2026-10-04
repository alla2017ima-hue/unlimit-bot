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
import re
from google import genai

# ==================== الإعدادات الأساسية ====================
TELEGRAM_TOKEN = '8848147122:AAG5G4pXYeycdpBI-GS7skhbY2YM6e2zUjI'
GEMINI_API_KEY = 'AQ.Ab8RN6JRlJ88PYPtrs0apZOrsKBhvTj7XCvZWPaSW_dxXwcU8w'
SHRINKME_API_TOKEN = '896319677a1627b715581ada979db092b8961386'
CHANNEL_ID = '@UnlimitTechDZ'

bot = telebot.TeleBot(TELEGRAM_TOKEN)
server = Flask(__name__)
ALGERIA_TZ = pytz.timezone('Africa/Algiers')

# تهيئة عميل الذكاء الاصطناعي Gemini
client = genai.Client(api_key=GEMINI_API_KEY)

# مصادر الأخبار التقنية
RSS_SOURCES = [
    "https://www.tech-wd.com/wd/feed/",
    "https://www.ardroid.com/feed/",
    "https://www.unlimit-tech.com/blog/feed/",
    "https://sultantec.com/feed/",
    "https://aitnews.com/feed/",
    "https://www.iphoneislam.com/feed",
    "https://www.saudimax.com/feed/",
    "https://www.yallatech.net/feed/",
    "https://www.MekkanoTech.com/feed/",
    "https://www.tsuut.com/feed/",
    "https://www.th3professional.com/feed",
    "https://www.computer-wd.com/feed/"
]

seen_links = set()
pending_posts = {}

# ==================== الدوال الأساسية ====================

def shorten_link(original_link):
    """اختصار الروابط تلقائياً عبر ShrinkMe"""
    try:
        if "t.me" in original_link or "telegram.dog" in original_link:
            return original_link
        api_url = f"https://shrinkme.io/api?api={SHRINKME_API_TOKEN}&url={original_link}"
        response = requests.get(api_url, timeout=10)
        data = response.json()
        if data.get("status") == "success":
            return data.get("shortenedUrl")
    except Exception as e:
        print(f"Error shortening link: {e}")
    return original_link

def ai_rewrite_and_clean(original_text):
    """إعادة صياغة جذرية ومبتكرة للمنشور مع إزالة كاملة للمصادر الخارجية"""
    prompt = f"""
    أنت محترف صناعة محتوى تقني ومدير لقناة "UnlimitTechDZ".
    قم بقراءة هذا النص واكتب له صياغة جديدة تماماً، بأسلوب جذاب، مشوق، ومبتكر باللغة العربية.
    
    شروط صارمة:
    1. امنع النسخ الحرفي تماماً، وقم بتغيير صياغة وترتيب الجمل بطريقة فريدة كأنك كتبت الخبر بنفسك.
    2. احذف نهائياً أي اسم قناة، أو توقيع، أو معرف مصدر خارجي موجود في النص.
    3. حافظ على الروابط التقنية أو اترك لها مكاناً واضحاً لكي يتم التعامل معها.
    
    النص الأصلي:
    {original_text}
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return response.text
    except Exception as e:
        print(f"AI Error: {e}")
        return original_text

# ==================== معالجة الأوامر والرسائل ====================

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "مرحباً بك يا بشير في غرفة تحكم المدير الذكي لقناة 🏴‍☠Unlimit Tech🇩🇿 🚀")

@bot.message_handler(content_types=['text', 'photo'])
def capture_forwarded_content(message):
    text = message.text or message.caption or ""
    if not text:
        return
        
    if text.startswith('/'):
        return
        
    # التقاط الصورة المرفقة إن وجدت
    photo_file_id = None
    if message.photo:
        photo_file_id = message.photo[-1].file_id
        
    bot.reply_to(message, "🤖 جاري معالجة المنشور والصورة وصياغتها بالذكاء الاصطناعي...")
    
    cleaned_and_rewritten = ai_rewrite_and_clean(text)
    
    urls = re.findall(r'(https?://[^\s]+)', cleaned_and_rewritten)
    final_text = cleaned_and_rewritten
    for u in urls:
        if "shrinkme" not in u and "t.me" not in u:
            shortened = shorten_link(u)
            final_text = final_text.replace(u, shortened)
            
    post_id = str(hash(text))
    pending_posts[post_id] = {
        "text": f"📱 **UnlimitTechDZ Exclusive:**\n\n{final_text}\n\n🔗 *@UnlimitTechDZ*",
        "photo": photo_file_id
    }
    
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✅ نشر فوري", callback_data=f"approve_{post_id}"),
        InlineKeyboardButton("❌ إلغاء", callback_data=f"reject_{post_id}")
    )
    
    # إرسال المعاينة (مع الصورة إن وجدت أو نص فقط)
    if photo_file_id:
        bot.send_photo(
            message.chat.id,
            photo_file_id,
            caption=f"📌 **معاينة مع الصورة:**\n\n{pending_posts[post_id]['text']}",
            reply_markup=markup,
            parse_mode="Markdown"
        )
    else:
        bot.send_message(
            message.chat.id,
            f"📌 **معاينة:**\n\n{pending_posts[post_id]['text']}",
            reply_markup=markup,
            parse_mode="Markdown"
        )

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    data = call.data
    if "_" not in data:
        return
    action, post_id = data.split("_", 1)
    
    if action == "approve":
        if post_id in pending_posts:
            post_data = pending_posts[post_id]
            post_content = post_data['text']
            photo_file_id = post_data.get('photo')
            try:
                # النشر في القناة مع الصورة إذا كانت موجودة
                if photo_file_id:
                    bot.send_photo(CHANNEL_ID, photo_file_id, caption=post_content, parse_mode="Markdown")
                else:
                    bot.send_message(CHANNEL_ID, post_content, parse_mode="Markdown")
                
                bot.answer_callback_query(call.id, "✅ تم النشر بنجاح!")
                bot.send_message(call.message.chat.id, "📢 تم نشر المنشور في القناة!")
            except Exception as e:
                bot.answer_callback_query(call.id, f"⚠️ فشل النشر: {e}")
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
            del pending_posts[post_id]
            
    elif action == "reject":
        if post_id in pending_posts:
            del pending_posts[post_id]
        bot.answer_callback_query(call.id, "تم الحذف ❌")
        bot.delete_message(call.message.chat.id, call.message.message_id)

# ==================== Webhook ====================

@server.route('/' + TELEGRAM_TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@server.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url='https://unlimit-bot.onrender.com/' + TELEGRAM_TOKEN)
    return "AI Master Bot is running smoothly!", 200

if __name__ == "__main__":
    server.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
