# handlers/messages.py
import logging
from telegram import Update
from telegram.ext import MessageHandler, filters, CallbackContext
from utils.download import download_music
import os
import asyncio

async def buttons_handler(update: Update, context: CallbackContext) -> None:
    text = update.message.text
    logging.info(f"📩 Натиснута кнопка: {text}")

    if text == "📥 Завантажити пісню":
        await update.message.reply_text("🎵 Введіть назву пісні для завантаження:")
        context.user_data["awaiting_song"] = True
    elif text == "🔍 Пошук музики":
        await update.message.reply_text("🔎 Введіть ім'я виконавця або пісню для пошуку:")
    elif text == "🎶 Розпізнати пісню":
        await update.message.reply_text("🎤 Надішліть голосове повідомлення з піснею.")
    elif text == "📃 Отримати текст пісні":
        await update.message.reply_text("📜 Введіть назву пісні для отримання тексту:")
    elif text == "🎧 Рекомендації":
        await update.message.reply_text("✨ Введіть назву улюбленого виконавця – я підберу щось схоже.")
    else:
        await update.message.reply_text("❌ Невідома команда. Використовуйте клавіатуру для вибору дій.")

async def text_message_handler(update: Update, context: CallbackContext) -> None:
    text = update.message.text
    logging.info(f"📩 Отримано текст: {text}")
    if context.user_data.get("awaiting_song", False):
        context.user_data["awaiting_song"] = False
        logging.info(f"🎵 Назва пісні: {text}")
        # Викликаємо завантаження музики
        await send_music_wrapper(update, context, text)
    else:
        await update.message.reply_text("❌ Невідома команда. Використовуйте клавіатуру для вибору дій.")

async def send_music_wrapper(update: Update, context: CallbackContext, query: str) -> None:
    logging.info(f"🔍 Обробка завантаження пісні: {query}")
    await update.message.reply_text(f"🔍 Шукаю {query}...")
    file_path = download_music(query)
    if file_path and os.path.exists(file_path):
        try:
            with open(file_path, 'rb') as audio:
                await update.message.reply_audio(audio=audio)
            logging.info(f"✅ Пісня відправлена: {file_path}")
        except Exception as e:
            logging.error(f"❌ Помилка відправлення: {e}")
            await update.message.reply_text("❌ Помилка відправлення пісні.")
    else:
        await update.message.reply_text("❌ Не вдалося знайти пісню. Спробуйте ще раз.")

buttons_handler = MessageHandler(filters.TEXT & filters.Regex("^(📥 Завантажити пісню|🔍 Пошук музики|🎶 Розпізнати пісню|📃 Отримати текст пісні|🎧 Рекомендації)$"), buttons_handler)
text_message_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler)
