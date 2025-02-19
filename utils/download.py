# utils/download.py

import os
import urllib.parse

import requests
import yt_dlp
import logging
from bs4 import BeautifulSoup
from PIL import Image

from config import GENIUS_API_KEY
from utils.sanitize import sanitize_filename, format_duration, format_filesize

def normalize_youtube_url(url: str) -> str:
    """
    Приймає будь-яке посилання YouTube і повертає канонічне посилання виду:
    "https://www.youtube.com/watch?v=VIDEO_ID"
    """
    parsed = urllib.parse.urlparse(url)
    video_id = None
    hostname = parsed.hostname.lower() if parsed.hostname else ''
    if hostname in ['youtu.be']:
        video_id = parsed.path.lstrip('/')
    elif hostname in ['www.youtube.com', 'youtube.com']:
        qs = urllib.parse.parse_qs(parsed.query)
        video_id = qs.get('v', [None])[0]
        # Якщо video_id не знайдено, перевіримо, чи є /embed/ або /v/ у шляху
        if not video_id and parsed.path:
            path_parts = parsed.path.split('/')
            if 'embed' in path_parts or 'v' in path_parts:
                video_id = path_parts[-1]
    if video_id:
        return f"https://www.youtube.com/watch?v={video_id}"
    return url

async def fetch_youtube_metadata(query):
    """
    Отримує базову інформацію про трек (без завантаження):
      - title (назва)
      - duration (тривалість, сек)
      - uploader (канал/виконавець)
      - thumbnail (URL обкладинки)
    Повертає словник з цими полями.
    """
    if query.startswith("http"):
        normalized_query = normalize_youtube_url(query)
        search_str = normalized_query
    else:
        search_str = f"ytsearch:{query}"

    logging.info(f"🔎 Отримую метадані для: {search_str}")

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'music/%(title)s.%(ext)s',
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(search_str, download=False)
        if 'entries' in info:
            info = info['entries'][0]
        meta = {
            'title': info.get('title', 'Unknown'),
            'duration': info.get('duration', 0),
            'uploader': info.get('uploader', 'Unknown'),
            'thumbnail': info.get('thumbnail', None),
        }
    return meta

async def download_music(query):
    """
    Завантажує аудіо (перший результат) за запитом.
    Якщо query є URL, нормалізуємо його, інакше додаємо "ytsearch:".
    Повертає шлях до .mp3-файлу або None, якщо не знайдено.
    """
    logging.info(f"🎵 Завантажую музику: {query}")
    if query.startswith("http"):
        search_query = normalize_youtube_url(query)
    else:
        search_query = f"ytsearch:{query}"

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'music/%(title)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    from yt_dlp import YoutubeDL
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(search_query, download=True)
        if 'entries' in info:
            if not info['entries']:
                raise ValueError("No entries found for the query")
            info = info['entries'][0]
        filename = ydl.prepare_filename(info)
        filename = filename.replace('.webm', '.mp3').replace('.m4a', '.mp3')
        if os.path.exists(filename):
            logging.info(f"✅ Завантажено файл: {filename}")
            return filename
        else:
            logging.error(f"❌ Файл не знайдено: {filename}")
            return None

async def download_music_with_metadata(query):
    """
    Спочатку отримує метадані через fetch_youtube_metadata,
    потім завантажує аудіо за допомогою download_music.
    Повертає кортеж: (filename, title, duration, uploader, thumbnail)
    """
    meta = await fetch_youtube_metadata(query)
    title = meta.get('title', 'Unknown')
    duration = meta.get('duration', 0)
    uploader = meta.get('uploader', 'Unknown')
    thumbnail = meta.get('thumbnail', None)
    filename = await download_music(query)
    return filename, title, duration, uploader, thumbnail

async def download_thumbnail(url, out_path='thumb.jpg', max_size_kb=200):
    """
    Завантажує thumbnail за URL і зменшує його, поки не стане менше max_size_kb (у KB).
    Повертає шлях до файлу або None, якщо не вдалося завантажити.
    """
    if not url:
        return None
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            logging.error(f"❌ Не вдалося завантажити thumbnail: статус {r.status_code}")
            return None
        with open(out_path, 'wb') as f:
            f.write(r.content)
        if os.path.getsize(out_path) > max_size_kb * 1024:
            img = Image.open(out_path)
            img.thumbnail((320, 320))
            img.save(out_path, optimize=True, quality=85)
            # Якщо все ще перевищує ліміт, зменшуємо якість
            while os.path.getsize(out_path) > max_size_kb * 1024:
                img = Image.open(out_path)
                img.save(out_path, optimize=True, quality=70)
        return out_path
    except Exception as e:
        logging.error(f"Помилка завантаження thumbnail: {e}")
        return None

async def search_music(query, max_results=1):
    """
    Виконує пошук музики за запитом (без завантаження файлів) та повертає список результатів.
    Повертає список словників, кожен містить 'title', 'duration', 'uploader' та 'url' (посилання на YouTube).
    """
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'music/%(title)s.%(ext)s',
    }
    results = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # Використовуємо ytsearchN, де N — кількість результатів
        info = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
        if 'entries' in info:
            for entry in info['entries']:
                result = {
                    'title': entry.get('title', 'Unknown'),
                    'duration': entry.get('duration', 0),
                    'uploader': entry.get('uploader', 'Unknown'),
                    'url': entry.get('webpage_url', '')
                }
                results.append(result)
    return results

async def get_lyrics(song_query):
    search_url = f"https://api.genius.com/search?q={song_query}"
    headers = {"Authorization": f"Bearer {GENIUS_API_KEY}"}

    try:
        response = requests.get(search_url, headers=headers, timeout=10)
        data = response.json()
        hits = data.get("response", {}).get("hits", [])
        if not hits:
            logging.error("❌ Не знайдено результатів для пошуку лірики.")
            return None
        song_url = hits[0]["result"]["url"]
    except Exception as e:
        logging.error(f"❌ Помилка пошуку в Genius API: {e}")
        return None

    # Скрапимо текст пісні з URL сторінки
    headers_scrape = {"User-Agent": "Mozilla/5.0"}
    try:
        page = requests.get(song_url, headers=headers_scrape, timeout=10)
        if page.status_code != 200:
            logging.error(f"❌ Не вдалося завантажити сторінку з лірикою: статус {page.status_code}")
            return None

        soup = BeautifulSoup(page.text, "html.parser")
        # Genius використовує новий markup: шукаємо всі div з data-lyrics-container="true"
        containers = soup.find_all("div", attrs={"data-lyrics-container": "true"})
        if not containers:
            logging.error("❌ Не вдалося знайти елементи з текстом пісні.")
            return None

        lyrics = "\n".join([container.get_text(separator="\n", strip=True) for container in containers])
        return lyrics.strip()
    except Exception as e:
        logging.error(f"❌ Помилка скрапінгу лірики: {e}")
        return None

async def recognize_song(file_path):
    """
    Розпізнає пісню через Audd.io.
    Повертає назву треку або 'Не вдалося розпізнати трек'.
    """
    url = "https://api.audd.io/"
    data = {"api_token": "b158e7438fe38dde1f0990e3fd6bfd29"}
    try:
        with open(file_path, "rb") as f:
            files = {"file": f}
            response = requests.post(url, data=data, files=files).json()
        if "result" in response and response["result"]:
            return response["result"].get("title", "Невідомо")
        else:
            return "Не вдалося розпізнати трек"
    except Exception as e:
        logging.error(f"Помилка розпізнавання треку: {e}")
        return "Не вдалося розпізнати трек"

