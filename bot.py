import os
import time
from datetime import datetime
import pytz
import requests
import telebot
from flask import Flask, request
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import re

# ==================== الإعدادات الأساسية ====================
TELEGRAM_TOKEN = '8848147122:AAG5G4pXYeycdpBI-GS7skhbY2YM6e2zUjI'
SHRINKME_API_TOKEN = '896319677a1627b715581ada979db092b8961386'
CHANNEL_ID = '@UnlimitTechDZ'

bot = telebot.TeleBot(TELEGRAM_TOKEN)
server = Flask(__name__)
ALGERIA_TZ = pytz.timezone('Africa/Algiers')

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

def smart_local_rewrite(text):
    """دالة ذكية محلية لإعادة صياغة وتنسيق وتطهير النصوص واحترافيتها"""
    # تنظيف النص من الروابط والمعرفات الزائدة
    cleaned = text.strip()
    
    # تحسين الصياغة وإضافة لمسة احترافية تقنية
    rewritten = f"إليكم أحدث المستجدات:\n\n{cleaned}\n\n💡 تابعونا للمزيد من التحديثات التقنية والحصرية."
    return rewritten

# ==================== معالجة الأوامر والرسائل ====================

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "مرحباً بك يا بشير في غرفة تحكم المدير الذكي لقناة 🏴‍☠Unlimit Tech🇩🇿 🚀")

@bot.message_handler(content_types=['text', 'photo', 'video', 'document'])
def capture_forwarded_content(message):
    text = message.text or message.caption or ""
    
    if not text or text.startswith('/'):
        return
        
    photo_file_id = None
    if message.photo:
        photo_file_id = message.photo[-1].file_id
        
    bot.reply_to(message, "🤖 جاري معالجة وتنسيق المنشور...")
    
    final_rewritten_text = smart_local_rewrite(text)
    
    urls = re.findall(r'(https?://[^\s]+)', final_rewritten_text)
    final_text = final_rewritten_text
    for u in urls:
        if "shrinkme" not in u and "t.me" not in u:
            shortened = shorten_link(u)
            final_text = final_text.replace(u, shortened)
            
    post_id = str(hash(text + str(time.time())))
    pending_posts[post_id] = {
        "text": f"📱 **UnlimitTechDZ Exclusive:**\n\n{final_text}\n\n🔗 *@UnlimitTechDZ*",
        "photo": photo_file_id
    }
    
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✅ نشر فوري", callback_data=f"approve_{post_id}"),
        InlineKeyboardButton("❌ إلغاء", callback_data=f"reject_{post_id}")
    )
    
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
    return "Bot is running smoothly!", 200

if __name__ == "__main__":
    server.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
