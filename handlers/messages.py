# handlers/messages.py

import logging
import os
from telegram import Update, InputFile
from telegram.constants import ParseMode
from telegram.ext import CallbackContext, MessageHandler, filters
from utils.download import (
    download_music_with_metadata,
    download_thumbnail,
    download_music,
    fetch_youtube_metadata,
    recognize_song, search_music
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
    else:
        await update.message.reply_text("❌ Невідома команда. Використовуйте клавіатуру для вибору дій.")



async def send_search_results(update: Update, context: CallbackContext, query: str) -> None:
    logging.info(f"🔍 Виконується пошук музики: {query}")
    await update.message.reply_text(f"🔍 Шукаю музику за запитом: {query}...")
    # Функція search_music має повернути список словників з метаданими
    results = search_music(query)
    if not results:
        await update.message.reply_text("❌ Результатів не знайдено.")
        return
    for i, res in enumerate(results, start=1):
        duration_str = format_duration(res['duration']) if res['duration'] else "N/A"
        msg = f"* {res['title']}*\nВиконавець: {res['uploader']}\nТривалість: {duration_str}\n[Переглянути]({res['url']})\n\n"
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)



# Якщо потрібно, можна додати відповідний хендлер:
search_music_handler = MessageHandler(
    filters.TEXT & filters.Regex("^🔍 Пошук музики$"),
    send_search_results  # Або окрема функція, що спочатку просить запит, а потім викликає send_search_results
)


async def send_music_with_thumb(update: Update, context: CallbackContext, query: str) -> None:
    logging.info(f"🔍 Обробка завантаження пісні: {query}")
    await update.message.reply_text(f"⬇️ Шукаю і Завантажую: {query}...")

    # Завантаження аудіо і метаданих
    filename, title, duration, uploader, thumb_url = download_music_with_metadata(query)
    if not filename or not os.path.exists(filename):
        await update.message.reply_text("❌ Не вдалося знайти пісню. Спробуйте ще раз.")
        return

    # duration_str = format_duration(duration) if duration else "N/A"
    # info_msg = f"Надсилаю:\n{title}\nТривалість: {duration_str}\nВиконавець: {uploader}"
    # await update.message.reply_text(info_msg)

    # Завантажуємо і зменшуємо thumbnail
    thumb_path = download_thumbnail(thumb_url, 'thumb.jpg', 200)

    try:
        with open(filename, 'rb') as audio_file:
            audio_input = InputFile(audio_file, filename=os.path.basename(filename))
            if thumb_path and os.path.exists(thumb_path):
                with open(thumb_path, 'rb') as thumb_file:
                    thumb_input = InputFile(thumb_file, filename=os.path.basename(thumb_path))
                    # Передаємо thumb через api_kwargs
                    await update.message.reply_audio(
                        audio=audio_input,
                        title=title,
                        performer=uploader,
                        duration=duration if duration else 0,
                        caption="@music_for_weyymss_bot",
                        api_kwargs={"thumb": thumb_input}
                    )
            else:
                await update.message.reply_audio(
                    audio=audio_input,
                    title=title,
                    performer=uploader,
                    caption="@music_for_weyymss_bot",
                    duration=duration if duration else 0
                )
        logging.info(f"✅ Пісня відправлена: {filename}")
        await update.message.reply_text("🔍Введіть назву пісні або виберіть іншу дію.")

    except Exception as e:
        logging.error(f"❌ Помилка надсилання аудіофайлу: {e}")
        await update.message.reply_text("❌ Виникла помилка при відправленні пісні.")# Реєстрація хендлерів, які можна додати в bot.py
