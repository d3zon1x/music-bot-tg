# utils/sanitize.py

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