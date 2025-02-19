# handlers/messages.py
import asyncio
import logging
import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.constants import ParseMode
from telegram.ext import CallbackContext, CallbackQueryHandler


from sqlDb.db import insert_search
from utils.download import (
    download_thumbnail,
    search_music,
    get_lyrics, normalize_youtube_url
)
from utils.recommendations import get_recommendations
from utils.sanitize import format_duration


async def insert_song_bd(u_id, user, artist: str, text: str):
    await insert_search(u_id, user, artist, text)

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

    await send_music_with_thumb(update, context, video_url)
# Реєструємо callback handler

async def send_search_results(update: Update, context: CallbackContext, query: str) -> None:
    logging.info(f"🔍 Виконується пошук музики: {query}")
    await update.message.reply_text(f"🔍 Шукаю музику за запитом: {query}...")
    results = await search_music(query)
    if not results:
        await update.message.reply_text("❌ Результатів не знайдено.")
        return
    context.user_data['search_results'] = results
    keyboard = []
    for i, res in enumerate(results, start=1):
        duration_str = format_duration(res['duration']) if res['duration'] else "N/A"
        msg = f"*{res['title']}*\n👤: {res['uploader']}\n🕑: {duration_str}\n[Переглянути]({res['url']})\n\n"
        keyboard.append([InlineKeyboardButton(text="Завантажити", callback_data=f"download_{res['url']}")])
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
            msg = f"*{res['title']}*\n👤: {res['uploader']}\n🕑: {duration_str}\n[Переглянути]({res['url']})\n\n"
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

def progress_hook_factory(bot, chat_id, message_id, loop):
    def progress_hook(d):
        if d.get('status') == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            if total:
                downloaded = d.get('downloaded_bytes', 0)
                percent = downloaded / total * 100
                # Використовуємо run_coroutine_threadsafe для запуску корутини у головному event loop
                future = asyncio.run_coroutine_threadsafe(
                    bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=f"⬇️ Завантаження: {percent:.1f}%"
                    ),
                    loop
                )
                # Якщо потрібно, можна додати обробку результату:
                try:
                    future.result()
                except Exception as e:
                    if "Message is not modified" in str(e):
                        pass
                    else:
                        logging.error(f"Error updating progress: {e}")
    return progress_hook

async def send_music_with_thumb(update: Update, context: CallbackContext, query: str) -> None:
    msg_obj = update.message if update.message is not None else update.callback_query.message
    progress_message = await msg_obj.reply_text(f"⬇️ Пошук: {query}", disable_web_page_preview=True)
    chat_id = progress_message.chat_id
    message_id = progress_message.message_id

    # Отримуємо головний event loop
    main_loop = asyncio.get_running_loop()

    def download():
        from yt_dlp import YoutubeDL
        with YoutubeDL(ydl_opts) as ydl:
            if query.startswith("http"):
                normalized_query = normalize_youtube_url(query)
                info = ydl.extract_info(f"ytsearch:{normalized_query}", download=True)
            else:
                info = ydl.extract_info(f"ytsearch:{query}", download=True)

            if 'entries' in info:
                if not info['entries']:
                    # Якщо список порожній – кидаємо виключення
                    raise ValueError("No entries found for the query")
                info = info['entries'][0]
            filename = ydl.prepare_filename(info)
            filename = filename.replace('.webm', '.mp3').replace('.m4a', '.mp3')
            return info, filename

    bot = context.bot
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'music/%(title)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'progress_hooks': [progress_hook_factory(bot, chat_id, message_id, main_loop)],
    }

    # Завантаження в окремому потоці
    try:
        info, filename = await asyncio.to_thread(download)
    except Exception as e:
        logging.error(f"❌ Помилка під час завантаження: {e}")
        await msg_obj.reply_text("❌ Не вдалося знайти пісню. Спробуйте інший запит.")
        return

    if not filename or not os.path.exists(filename):
        await msg_obj.reply_text("❌ Не вдалося знайти пісню. Спробуйте ще раз.")
        return

    thumb_url = info.get('thumbnail')
    thumb_path = await download_thumbnail(thumb_url, 'thumb.jpg', 200)

    try:
        with open(filename, 'rb') as audio_file:
            audio_input = InputFile(audio_file, filename=os.path.basename(filename))
            if thumb_path and os.path.exists(thumb_path):
                with open(thumb_path, 'rb') as thumb_file:
                    thumb_input = InputFile(thumb_file, filename=os.path.basename(thumb_path))
                    await msg_obj.reply_audio(
                        audio=audio_input,
                        title=info.get('title', 'Unknown'),
                        performer=info.get('uploader', 'Unknown'),
                        duration=info.get('duration', 0),
                        caption="@music_for_weyymss_bot",
                        api_kwargs={"thumb": thumb_input}
                    )
            else:
                await msg_obj.reply_audio(
                    audio=audio_input,
                    title=info.get('title', 'Unknown'),
                    performer=info.get('uploader', 'Unknown'),
                    duration=info.get('duration', 0)
                )
        logging.info(f"✅ Пісня відправлена: {filename}")
        await insert_song_bd(user_id, username, info.get('uploader', 'Unknown'), info.get('title', 'Unknown'))
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"{info.get('title', 'Unknown')} ✅\n"
        )
    except Exception as e:
        logging.error(f"❌ Помилка надсилання аудіофайлу: {e}")
        await msg_obj.reply_text("❌ Виникла помилка при відправленні пісні.")


download_callback_handler = CallbackQueryHandler(download_callback, pattern="^download_")
