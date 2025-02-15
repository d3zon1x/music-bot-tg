# handlers/voice.py
from telegram import Update
from telegram.ext import MessageHandler, filters, CallbackContext
from utils.download import recognize_song
import logging

def handle_voice(update: Update, context: CallbackContext) -> None:
    file = context.bot.getFile(update.message.voice.file_id)
    file_path = "voice.ogg"
    file.download(file_path)
    logging.info(f"🎤 Голосовий файл завантажено: {file_path}")
    song_name = recognize_song(file_path)
    update.message.reply_text(f"🎶 Це схоже на: {song_name}")

voice_message_handler = MessageHandler(filters.VOICE, handle_voice)
