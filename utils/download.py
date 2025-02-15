# utils/download.py

import os
import requests
import yt_dlp
import logging
from PIL import Image
from utils.sanitize import sanitize_filename, format_duration, format_filesize

def fetch_youtube_metadata(query):
    """
    Отримує базову інформацію про трек (без завантаження):
      - title (назва)
      - duration (тривалість, сек)
      - uploader (канал/виконавець)
      - thumbnail (URL обкладинки)
    Повертає словник з цими полями.
    """
    logging.info(f"🔎 Отримую метадані для: {query}")
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'music/%(title)s.%(ext)s',
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch:{query}", download=False)
        if 'entries' in info:
            info = info['entries'][0]
        meta = {
            'title': info.get('title', 'Unknown'),
            'duration': info.get('duration', 0),
            'uploader': info.get('uploader', 'Unknown'),
            'thumbnail': info.get('thumbnail', None),
        }
    return meta

def download_music(query):
    """
    Завантажує аудіо (перший результат) за запитом.
    Повертає шлях до .mp3-файлу або None, якщо не знайдено.
    """
    logging.info(f"🎵 Завантажую музику: {query}")
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'music/%(title)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch:{query}", download=True)
        if 'entries' in info:
            info = info['entries'][0]
        filename = ydl.prepare_filename(info)
        filename = filename.replace('.webm', '.mp3').replace('.m4a', '.mp3')
        if os.path.exists(filename):
            logging.info(f"✅ Завантажено файл: {filename}")
            return filename
        else:
            logging.error(f"❌ Файл не знайдено: {filename}")
            return None

def download_music_with_metadata(query):
    """
    Спочатку отримує метадані (title, duration, uploader, thumbnail),
    потім завантажує аудіо, повертає:
      (filename, title, duration, uploader, thumbnail)
    """
    meta = fetch_youtube_metadata(query)
    title = meta['title']
    duration = meta['duration']
    uploader = meta['uploader']
    thumbnail = meta['thumbnail']
    filename = download_music(query)
    return filename, title, duration, uploader, thumbnail

def download_thumbnail(url, out_path='thumb.jpg', max_size_kb=200):
    """
    Завантажує thumbnail за URL і зменшує його, поки не стане <200 KB.
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
            while os.path.getsize(out_path) > max_size_kb * 1024:
                img = Image.open(out_path)
                img.save(out_path, optimize=True, quality=70)
        return out_path
    except Exception as e:
        logging.error(f"Помилка завантаження thumbnail: {e}")
        return None

def recognize_song(file_path):
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