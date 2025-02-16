import nest_asyncio
nest_asyncio.apply()

import asyncio
import logging
from telegram.ext import Application
from handlers.commands import start_command_handler
from handlers.messages import text_message_handler, buttons_handler, search_music_handler
from handlers.voice import voice_message_handler
from telegram.ext import CommandHandler, MessageHandler, filters
from handlers.commands import start_command_handler  # з твого commands.py
from handlers.messages import buttons_handler
from handlers.voice import voice_message_handler  # якщо є voice

from config import TOKEN  # API-ключ можна винести в окремий файл config.py

# Налаштування логування
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

buttons_handler = MessageHandler(
    ( ( (   # Фільтр для точних рядків кнопок
      (filters.TEXT & filters.Regex("^(📥 Завантажити пісню|🔍 Пошук відео кліпу|🎶 Розпізнати пісню|📃 Отримати текст пісні|🎧 Рекомендації)$"))
      ) )),
    buttons_handler
)

text_message_handler = MessageHandler(
    filters.TEXT & ~filters.COMMAND,
    text_message_handler
)



async def main():
    app = Application.builder().token(TOKEN).build()



    app.add_handler(start_command_handler)
    app.add_handler(buttons_handler)
    app.add_handler(text_message_handler)
    app.add_handler(search_music_handler)
    app.add_handler(voice_message_handler)




    print("🎵 Бот запущений!")
    await app.run_polling(close_loop=False)

if __name__ == "__main__":
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    loop.create_task(main())
    loop.run_forever()
