# utils/sanitize.py
import re

def sanitize_filename(filename):
    """Видаляє з назви файлу небезпечні символи."""
    invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    for char in invalid_chars:
        filename = filename.replace(char, '')
    return filename.strip()

def format_duration(sec):
    """Форматує тривалість у формат mm:ss."""
    m, s = divmod(sec, 60)
    return f"{m}:{s:02d}"

def format_filesize(size):
    """Перетворює байти у мегабайти (MB) з двома знаками після коми."""
    mb = size / (1024 * 1024)
    return f"{mb:.2f} MB"

def clean_track_info(artist: str, track: str):
    """
    Очищує назву треку (track) від виконавця (artist), а також від різних
    приписів типу (Official Audio), (Official Music Video) тощо.
    Повертає кортеж (clean_artist, clean_track).
    """

    artist_esc = re.escape(artist.strip())
    pattern = rf"(?i)^{artist_esc}\s*-\s*"  # (?i) – case-insensitive
    track = re.sub(pattern, "", track.strip())

    # 2. Видаляємо приписки в дужках/квадратних дужках на кшталт:
    #    (Official Audio), (Official Music Video), [Official Video], (Lyrics), (feat. ...), тощо.
    #    Можна задати кілька шаблонів або один універсальний із ключовими словами
    #    Задля прикладу видаляємо будь-який текст у дужках, де зустрічаються слова Official|Audio|Video|Lyrics
    track = re.sub(r"(?i)\(([^)]*(official|audio|video|lyrics|remix)[^)]*)\)", "", track)
    track = re.sub(r"(?i)\[([^]]*(official|audio|video|lyrics|remix)[^]]*)\]", "", track)

    # 3. Видаляємо зайві пробіли, дефіси, тощо
    track = re.sub(r"\s+", " ", track).strip()
    artist_clean = artist.strip()

    return artist_clean, track