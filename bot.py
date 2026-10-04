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

# ==================== Al-I'dadat al-Asasiyah ====================
TELEGRAM_TOKEN = '8848147122:AAG5G4pXYeycdpBI-GS7skhbY2YM6e2zUjI'
# Miftah Gemini API al-khass bi-ka allathi qamta bi-tawfiqih
GEMINI_API_KEY = 'AQ.Ab8RN6JRlJ88PYPtrs0apZOrsKBhvTj7XCvZWPaSW_dxXwcU8w'
SHRINKME_API_TOKEN = '896319677a1627b715581ada979db092b8961386'
CHANNEL_ID = '@UnlimitTechDZ'

bot = telebot.TeleBot(TELEGRAM_TOKEN)
server = Flask(__name__)
ALGERIA_TZ = pytz.timezone('Africa/Algiers')

# Tahyi'at 'amil al-zaka' al-istina'i Gemini
client = genai.Client(api_key=GEMINI_API_KEY)

# Masadir al-akhbar al-taqniyah
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

# ==================== Al-Dawal al-Asasiyah ====================

def shorten_link(original_link):
    """Ikhtisar al-rawabit tilpa'iyyan 'abr ShrinkMe"""
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
    """I'adat siyaghat al-manshoor bi-istikhdam al-zaka' al-istina'i"""
    prompt = f"""
    Qum bi-i'adat siyaghat hatha al-manshoor al-taqni aw al-tatbiq bi-usloob ihtirafi, jazthab, wa nazeef bil-lughah al-arabiyah.
    Shuroot sarimah:
    1. Qum bi-izalat ayyu ma'rifat qanawat qadimat aw asma' masadir kharijiyah tamaman.
    2. Ij'al al-usloob munasiban li-qanah taqniyah ismuha "UnlimitTechDZ".
    3. Hafiz 'ala al-rawabit al-mawjudah aw utruk makanon wadihan laha.
    
    Al-nass al-asli:
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

def ai_generate_reply(user_question):
    """Ijabat al-zaka' al-istina'i 'ala talabat al-mutabi'in"""
    prompt = f"""
    Anta mudir thaki wa musa'id taqni li-qanah "UnlimitTechDZ".
    Ajib 'ala risalat al-mutabi' al-tali bi-usloob lateef, ihtirafi, wa musa'id jiddan bil-lughah al-arabiyah:
    
    Risalat al-mustakhdim: {user_question}
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return response.text
    except Exception as e:
        return "Ahlan bik ya sadiqi, tamma istilam risalatuka wa sayatamma talbiyatuha!"

# ==================== Mu'alajat al-Awamir ====================

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Marhaban bik ya Bashir fi ghurfat tahakkum al-mudir al-thaki li-qanah 🏴‍☠Unlimit Tech🇩🇿 🚀")

@bot.message_handler(commands=['getnews'])
def manual_fetch_news(message):
    bot.reply_to(message, "⚡ Jari fahas masadir RSS...")
    count = 0
    
    for url in RSS_SOURCES:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:1]:
                title = entry.title
                original_link = entry.link
                
                if original_link in seen_links:
                    continue
                seen_links.add(original_link)
                
                rewritten_text = ai_rewrite_and_clean(f"Unwan al-maqal: {title}\nRabith: {original_link}")
                
                urls = re.findall(r'(https?://[^\s]+)', rewritten_text)
                final_text = rewritten_text
                for u in urls:
                    if "shrinkme" not in u and "t.me" not in u:
                        shortened = shorten_link(u)
                        final_text = final_text.replace(u, shortened)
                
                post_id = str(hash(original_link))
                pending_posts[post_id] = {
                    "text": f"🚀 **Jadid al-Taqniyah:**\n\n{final_text}\n\n🔗 *@UnlimitTechDZ*"
                }
                
                markup = InlineKeyboardMarkup()
                markup.row(
                    InlineKeyboardButton("✅ Nashr Fawri", callback_data=f"approve_{post_id}"),
                    InlineKeyboardButton("❌ Ilghaa", callback_data=f"reject_{post_id}")
                )
                
                bot.send_message(message.chat.id, f"📌 **Mu'ayanah:**\n\n{pending_posts[post_id]['text']}", reply_markup=markup, parse_mode="Markdown")
                count += 1
                if count >= 3:
                    break
        except:
            continue

@bot.message_handler(func=lambda message: message.forward_from_chat or (message.text and "http" in message.text))
def capture_forwarded_content(message):
    text = message.text or message.caption or ""
    if not text:
        return
        
    bot.reply_to(message, "🤖 Jari mu'alajat al-manshoor 'abr al-zaka' al-istina'i...")
    
    cleaned_and_rewritten = ai_rewrite_and_clean(text)
    
    urls = re.findall(r'(https?://[^\s]+)', cleaned_and_rewritten)
    final_text = cleaned_and_rewritten
    for u in urls:
        if "shrinkme" not in u and "t.me" not in u:
            shortened = shorten_link(u)
            final_text = final_text.replace(u, shortened)
            
    post_id = str(hash(text))
    pending_posts[post_id] = {
        "text": f"📱 **Tatbiq Mumayyiz:**\n\n{final_text}\n\n🔗 *@UnlimitTechDZ*"
    }
    
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✅ Nashr Fawri", callback_data=f"approve_{post_id}"),
        InlineKeyboardButton("❌ Ilghaa", callback_data=f"reject_{post_id}")
    )
    
    bot.send_message(
        message.chat.id,
        f"📌 **Al-Natijah:**\n\n{pending_posts[post_id]['text']}",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda message: True)
def handle_general_chat(message):
    user_text = message.text
    ai_reply = ai_generate_reply(user_text)
    bot.reply_to(message, ai_reply)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    data = call.data
    if "_" not in data:
        return
    action, post_id = data.split("_", 1)
    
    if action == "approve":
        if post_id in pending_posts:
            post_content = pending_posts[post_id]['text']
            try:
                bot.send_message(CHANNEL_ID, post_content, parse_mode="Markdown")
                bot.answer_callback_query(call.id, "✅ Tamma al-nashr binajah!")
                bot.send_message(call.message.chat.id, "📢 Tamma nashr al-manshoor fi al-qanah!")
            except Exception as e:
                bot.answer_callback_query(call.id, "⚠️ Fashal al-nashr, ta'akkad anna al-bot mushrif.")
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
            del pending_posts[post_id]
            
    elif action == "reject":
        if post_id in pending_posts:
            del pending_posts[post_id]
        bot.answer_callback_query(call.id, "Tamma al-hadhth ❌")
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
    
