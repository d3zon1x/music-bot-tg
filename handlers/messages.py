# handlers/messages.py

import logging
import os
from telegram import Update, InputFile, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import CallbackContext, MessageHandler, filters, CallbackQueryHandler
from utils.download import (
    download_music_with_metadata,
    download_thumbnail,
    download_music,
    fetch_youtube_metadata,
    recognize_song, search_music, get_lyrics
)
from utils.sanitize import format_duration, format_filesize

def format_duration_local(sec):
    m, s = divmod(sec, 60)
    return f"{m}:{s:02d}"

async def buttons_handler(update: Update, context: CallbackContext) -> None:
    text = update.message.text
    logging.info(f"📩 Користувач натиснув кнопку: {text}")


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
        await update.message.reply_text("✨ Введіть назву улюбленого виконавця – я підберу щось схоже.")
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
    await query_obj.answer()  # обов'язково відповідаємо на callback

    await query_obj.edit_message_reply_markup(reply_markup=None)

    data = query_obj.data  # наприклад, "download_0"
    try:
        index = int(data.split("_")[1])
    except (IndexError, ValueError):
        await query_obj.edit_message_text("❌ Некоректний вибір.")
        return

    results = context.user_data.get('search_results', [])
    if index < 0 or index >= len(results):
        await query_obj.edit_message_text("❌ Некоректний вибір.")
        return

    # Наприклад, використовуємо title з результатів як запит для завантаження.
    track_query = results[index]['title']
    # await query_obj.edit_message_text(f"🔍 Завантаження треку: {track_query}...")
    logging.info(f"🔍 Завантаження треку: {track_query}")
    # Викликаємо функцію завантаження з обкладинкою (яка має бути визначена, наприклад, send_music_with_thumb)
    from handlers.messages import send_music_with_thumb  # імпортуємо, якщо потрібно
    await send_music_with_thumb(update, context, track_query)

# Реєструємо callback handler
download_callback_handler = CallbackQueryHandler(download_callback, pattern="^download_")

async def send_search_results(update: Update, context: CallbackContext, query: str) -> None:
    logging.info(f"🔍 Виконується пошук музики: {query}")
    await update.message.reply_text(f"🔍 Шукаю музику за запитом: {query}...")

    results = search_music(query)  # має повернути список результатів, наприклад:
    # [{'title': 'Song Title', 'duration': 210, 'uploader': 'Artist Name', 'url': 'https://...'}, ...]
    if not results:
        await update.message.reply_text("❌ Результатів не знайдено.")
        return

    # Зберігаємо результати в user_data для подальшого використання в callbackQuery
    context.user_data['search_results'] = results

    msg = "Знайдено наступні варіанти:\n\n"
    keyboard = []
    for i, res in enumerate(results, start=1):
        duration_str = format_duration(res['duration']) if res['duration'] else "N/A"
        msg = f"* {res['title']}*\nВиконавець: {res['uploader']}\nТривалість: {duration_str}\n[Переглянути]({res['url']})\n\n"
        # Створюємо кнопку для завантаження цього треку
        # callback_data "download_<index>" (індекс починається з 0)
        keyboard.append([InlineKeyboardButton(text="Завантажити", callback_data=f"download_{i - 1}")])

    inline_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=inline_markup)


async def send_lyrics(update: Update, context: CallbackContext) -> None:
    query = update.message.text
    logging.info(f"🔍 Отримання тексту для пісні: {query}")
    await update.message.reply_text("🔍 Отримую текст пісні, зачекайте...")
    lyrics = get_lyrics(query)
    if not lyrics:
        await update.message.reply_text("❌ Не вдалося отримати текст пісні.")
        return
    # Розбиваємо текст на частини (Telegram обмежує повідомлення до ~4096 символів)
    max_length = 4000
    parts = [lyrics[i:i+max_length] for i in range(0, len(lyrics), max_length)]
    for part in parts:
        await update.message.reply_text(part)


# Якщо потрібно, можна додати відповідний хендлер:
search_music_handler = MessageHandler(
    filters.TEXT & filters.Regex("^🔍 Пошук музики$"),
    send_search_results  # Або окрема функція, що спочатку просить запит, а потім викликає send_search_results
)


async def send_music_with_thumb(update: Update, context: CallbackContext, query: str) -> None:
    # Отримуємо об'єкт повідомлення: якщо це callback query, беремо його повідомлення
    msg_obj = update.message if update.message is not None else update.callback_query.message
    await msg_obj.reply_text(f"⬇️ Шукаю і Завантажую: {query}...")

    # Завантажуємо аудіо та метадані
    filename, title, duration, uploader, thumb_url = download_music_with_metadata(query)
    if not filename or not os.path.exists(filename):
        await msg_obj.reply_text("❌ Не вдалося знайти пісню. Спробуйте ще раз.")
        return

    # duration_str = format_duration(duration) if duration else "N/A"
    # info_msg = f"Надсилаю:\n{title}\nТривалість: {duration_str}\nВиконавець: {uploader}"
    # await msg_obj.reply_text(info_msg)

    # Завантажуємо та зменшуємо thumbnail
    thumb_path = download_thumbnail(thumb_url, 'thumb.jpg', 200)

    try:
        with open(filename, 'rb') as audio_file:
            from telegram import InputFile
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
    except Exception as e:
        logging.error(f"❌ Помилка надсилання аудіофайлу: {e}")
        await msg_obj.reply_text("❌ Виникла помилка при відправленні пісні.")
