# handlers/commands.py
from telegram.ext import CommandHandler, CallbackContext
from telegram import Update, ReplyKeyboardMarkup
import logging

def get_main_keyboard():
    keyboard = [
        ["🔍 Пошук музики", "📥 Завантажити пісню"],
        ["🎶 Розпізнати пісню", "📃 Отримати текст пісні"],
        ["🎧 Рекомендації", "🧩 Вікторина"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: CallbackContext) -> None:
    logging.info("✅ /start викликано")
    await update.message.reply_text("🎵 Привіт! Я музичний бот. Обери дію:", reply_markup=get_main_keyboard())

start_command_handler = CommandHandler("start", start)
