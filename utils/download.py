# utils/download.py
import os
import yt_dlp
from utils.sanitize import sanitize_filename
import requests

def download_music(query):
    print(f"🎵 Завантажую музику: {query}")
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
            print(f"✅ Завантажено файл: {filename}")
            return filename
        else:
            print(f"❌ Файл не знайдено: {filename}")
            return None

def recognize_song(file_path):
    url = "https://api.audd.io/"
    data = {"api_token": "b158e7438fe38dde1f0990e3fd6bfd29"}
    with open(file_path, "rb") as f:
        files = {"file": f}
        response = requests.post(url, data=data, files=files).json()
    return response["result"]["title"] if "result" in response else "Не вдалося розпізнати трек"
