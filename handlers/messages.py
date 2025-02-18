# handlers/messages.py

import logging
import os
import urllib.parse

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.constants import ParseMode
from telegram.ext import CallbackContext, MessageHandler, filters, CallbackQueryHandler

from sqlDb.db import insert_search
from utils.download import (
    download_music_with_metadata,
    download_thumbnail,
    search_music,
    get_lyrics, fetch_youtube_metadata
)
from utils.recommendations import get_recommendations
from utils.sanitize import format_duration, format_filesize



async def insert_song_bd(User_id, Username, artist: str, text: str):
    await insert_search(User_id, Username, artist, text)

def format_duration_local(sec):
    m, s = divmod(sec, 60)
    return f"{m}:{s:02d}"

async def buttons_handler(update: Update, context: CallbackContext) -> None:
    text = update.message.text
    logging.info(f"📩 Користувач натиснув кнопку: {text}")

    global user_id, username
    user_id = str(update.message.from_user.id)
    # result = await get_recommendations(user_id)
    # print(result)
    username = update.message.from_user.username or update.message.from_user.first_name


    if text == "🔍 Пошук відео кліпу":
        await update.message.reply_text("🔎 Введіть ім'я виконавця або пісню для пошуку:")
        context.user_data["mode"] = "search"  # Встановлюємо режим пошуку
        logging.info("⏳ Режим пошуку увімкнено")
    elif text == "📥 Завантажити пісню":
        await update.message.reply_text("🎵 Введіть назву пісні для завантаження:")
        context.user_data["mode"] = "download"  # Режим завантаження
        logging.info("⏳ Режим завантаження увімкнено")
    elif text == "🎶 Розпізнати пісню":
        await update.message.reply_text("🎤 Надішліть голосове повідомлення з піснею.")
    elif text == "📃 Отримати текст пісні":
        await update.message.reply_text("📜 Введіть назву пісні для отримання тексту:")
        context.user_data["mode"] = "lyrics"  # Режим отримання тексту
        logging.info("⏳ Режим отримання тексту увімкнено")
    elif text == "🎧 Рекомендації":
        await send_recommendations_menu(update, context)
    else:
        await update.message.reply_text("❌ Невідома команда. Використовуйте клавіатуру для вибору дій.")

async def text_message_handler(update: Update, context: CallbackContext) -> None:
    text = update.message.text
    logging.info(f"📩 Користувач надіслав текст: {text}")

    mode = context.user_data.get("mode")
    if mode == "download":
        # Режим завантаження пісні
        context.user_data["mode"] = "download"
        logging.info(f"🎵 Назва пісні для завантаження: {text}")
        await send_music_with_thumb(update, context, text)  # Функція завантаження з обкладинкою
    elif mode == "search":
        # Режим пошуку музики
        context.user_data["mode"] = None
        logging.info(f"🎵 Запит для пошуку музики: {text}")
        await send_search_results(update, context, text)
    elif mode == "lyrics":
        # Режим отримання тексту пісні
        context.user_data["mode"] = None
        logging.info(f"📜 Запит для отримання тексту: {text}")
        await send_lyrics(update, context)
    else:
        await update.message.reply_text("❌ Невідома команда. Використовуйте клавіатуру для вибору дій.")


async def download_callback(update: Update, context: CallbackContext) -> None:
    query_obj = update.callback_query
    await query_obj.answer()  # відповідаємо на callback
    await query_obj.edit_message_reply_markup(reply_markup=None)

    data = query_obj.data  # наприклад, "download_https://www.youtube.com/watch?v=XYZ"
    prefix = "download_"
    if not data.startswith(prefix):
        await query_obj.edit_message_text("❌ Некоректний вибір.")
        return

    video_url = data[len(prefix):]
    if not video_url.startswith("http"):
        await query_obj.edit_message_text("❌ Некоректний формат URL.")
        return

    logging.info(f"🔍 Завантаження треку з URL: {video_url}")
    # Викликаємо функцію завантаження з обкладинкою, передаючи URL замість звичайного запиту.
    # При цьому функція send_music_with_thumb має бути оновлена для обробки прямого URL (якщо потрібно)
    from handlers.messages import send_music_with_thumb
    await send_music_with_thumb(update, context, video_url)
# Реєструємо callback handler
download_callback_handler = CallbackQueryHandler(download_callback, pattern="^download_")

async def send_search_results(update: Update, context: CallbackContext, query: str) -> None:
    logging.info(f"🔍 Виконується пошук музики: {query}")
    await update.message.reply_text(f"🔍 Шукаю музику за запитом: {query}...")
    results = await search_music(query)
    if not results:
        await update.message.reply_text("❌ Результатів не знайдено.")
        return
    context.user_data['search_results'] = results
    msg = "Знайдено наступні варіанти:\n\n"
    keyboard = []
    for i, res in enumerate(results, start=1):
        duration_str = format_duration(res['duration']) if res['duration'] else "N/A"
        msg += f"*{i}. {res['title']}*\nВиконавець: {res['uploader']}\nТривалість: {duration_str}\n[Переглянути]({res['url']})\n\n"
        keyboard.append([InlineKeyboardButton(text="Завантажити", callback_data=f"download_{i - 1}")])
    inline_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=inline_markup)

async def send_lyrics(update: Update, context: CallbackContext) -> None:
    query = update.message.text
    logging.info(f"🔍 Отримання тексту для пісні: {query}")
    await update.message.reply_text("🔍 Отримую текст пісні, зачекайте...")
    lyrics = await get_lyrics(query)
    if not lyrics:
        await update.message.reply_text("❌ Не вдалося отримати текст пісні.")
        return
    # Розбиваємо текст на частини (Telegram обмежує повідомлення до ~4096 символів)
    max_length = 4000
    parts = [lyrics[i:i+max_length] for i in range(0, len(lyrics), max_length)]
    for part in parts:
        await update.message.reply_text(part)

async def send_recommendations_menu(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [InlineKeyboardButton("5 треків", callback_data="reco_5")],
        [InlineKeyboardButton("10 треків", callback_data="reco_10")],
        [InlineKeyboardButton("15 треків", callback_data="reco_15")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Виберіть кількість рекомендацій:", reply_markup=reply_markup)
    context.user_data["mode"] = "recommendations"

# Callback handler для меню рекомендацій
async def recommendations_callback(update: Update, context: CallbackContext) -> None:
    query_obj = update.callback_query
    await query_obj.answer()
    await query_obj.edit_message_reply_markup(reply_markup=None)
    data = query_obj.data  # наприклад, "reco_5"
    try:
        limit = int(data.split("_")[1])
    except (IndexError, ValueError):
        await query_obj.edit_message_text("❌ Некоректний вибір.")
        return
    user_id = str(update.callback_query.from_user.id)
    recommendations = await get_recommendations(user_id, limit)
    if not recommendations:
        await query_obj.message.reply_text("❌ Не вдалося отримати рекомендації.")
        return
    # Зберігаємо рекомендації для callback'ів завантаження
    context.user_data['recommendations'] = recommendations
    for idx, rec in enumerate(recommendations):
        duration_str = format_duration(rec['duration']) if rec.get('duration') else "N/A"
        results = await search_music(rec['artist'] + " " + rec['title'])
        for i, res in enumerate(results, start=1):
            duration_str = format_duration(res['duration']) if res['duration'] else "N/A"
            msg = f"*{i}. {res['title']}*\nВиконавець: {res['uploader']}\nТривалість: {duration_str}\n[Переглянути]({res['url']})\n\n"
            # keyboard.append([InlineKeyboardButton(text="Завантажити", callback_data=f"download_{i - 1}")])
            keyboard = [
                [InlineKeyboardButton("Завантажити", callback_data=f"download_{res['url']}")]
            ]
            inline_markup = InlineKeyboardMarkup(keyboard)
            await query_obj.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=inline_markup)

        # print(result)
        # msg_text = (
        #     f"*{result['title']}*\n"
        #     f"Виконавець: {result['uploader']}\n"
        #     f"Тривалість: {result['duration']}\n"
        #     f"[Переглянути на YouTube]({result['url']})"
        # )






# Якщо потрібно, можна додати відповідний хендлер:



async def send_music_with_thumb(update: Update, context: CallbackContext, query: str) -> None:
    msg_obj = update.message if update.message is not None else update.callback_query.message
    await msg_obj.reply_text(f"⬇️Завантажую: {query}...", disable_web_page_preview=True)
    filename, title, duration, uploader, thumb_url = await download_music_with_metadata(query)
    if not filename or not os.path.exists(filename):
        await msg_obj.reply_text("❌ Не вдалося знайти пісню. Спробуйте ще раз.")
        return
    thumb_path = await download_thumbnail(thumb_url, 'thumb.jpg', 200)
    try:
        with open(filename, 'rb') as audio_file:
            audio_input = InputFile(audio_file, filename=os.path.basename(filename))
            if thumb_path and os.path.exists(thumb_path):
                with open(thumb_path, 'rb') as thumb_file:
                    thumb_input = InputFile(thumb_file, filename=os.path.basename(thumb_path))
                    await msg_obj.reply_audio(
                        audio=audio_input,
                        title=title,
                        performer=uploader,
                        duration=duration if duration else 0,
                        caption="@music_for_weyymss_bot",
                        api_kwargs={"thumb": thumb_input}
                    )
            else:
                await msg_obj.reply_audio(
                    audio=audio_input,
                    title=title,
                    performer=uploader,
                    duration=duration if duration else 0
                )
        logging.info(f"✅ Пісня відправлена: {filename}")
        await insert_song_bd(user_id, username, uploader, title)
    except Exception as e:
        logging.error(f"❌ Помилка надсилання аудіофайлу: {e}")
        await msg_obj.reply_text("❌ Виникла помилка при відправленні пісні.")


