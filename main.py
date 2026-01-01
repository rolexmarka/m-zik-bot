import os
import sqlite3
import yt_dlp
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

# Loglama: Botun ne yaptığını konsolda görmek için
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# Tokeni Replit Secrets'tan alıyoruz (Birazdan ekleyeceğiz)
TOKEN = os.getenv('BOT_TOKEN')

# Veritabanı: Trendleri kaydetmek için
conn = sqlite3.connect('music_bot.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS trends (song_name TEXT, count INTEGER)')
conn.commit()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎵 **Müzik Botu Hazır!**\nŞarkı adını yaz, hemen bulayım.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text
    # Trend güncelleme
    cursor.execute('INSERT INTO trends (song_name, count) VALUES (?, 1) ON CONFLICT(song_name) DO UPDATE SET count = count + 1', (query,))
    conn.commit()

    wait_msg = await update.message.reply_text(f"🔍 '{query}' aranıyor...")
    
    try:
        ydl_opts = {'format': 'bestaudio', 'noplaylist': True, 'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            results = ydl.extract_info(f"ytsearch5:{query}", download=False)['entries']
        
        keyboard = [[InlineKeyboardButton(f"📥 {v['title'][:40]}", callback_data=f"dl|{v['id']}")] for v in results]
        await wait_msg.edit_text("Lütfen birini seç:", reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        await wait_msg.edit_text(f"Hata: {e}")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    video_id = query.data.split("|")[1]
    await query.answer()
    await query.edit_message_text("💾 İndiriliyor, lütfen bekleyin...")
    
    file_path = f"{video_id}.mp3"
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': video_id,
        'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}],
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f"https://www.youtube.com/watch?v={video_id}"])
        
        with open(file_path, 'rb') as audio:
            await context.bot.send_audio(chat_id=query.message.chat_id, audio=audio, caption="✅ Hazır!")
        os.remove(file_path)
    except Exception as e:
        await query.message.reply_text(f"İndirme hatası: {e}")

if __name__ == '__main__':
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_callback))
    print("Bot başlatıldı...")
    application.run_polling()
