# db.py
import sqlite3
from sqlite3 import Error

from utils.sanitize import clean_track_info

DATABASE = "music_bot.db"

def create_connection():
    conn = None
    try:
        conn = sqlite3.connect(DATABASE)
        return conn
    except Error as e:
        print(e)
    return conn

async def init_db():
    conn = create_connection()
    if conn is not None:
        create_table_sql = """
            CREATE TABLE IF NOT EXISTS user_searches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                username TEXT,
                artist_query TEXT,
                song_query TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """
        try:
            c = conn.cursor()
            c.execute(create_table_sql)
            conn.commit()
        except Error as e:
            print(e)
        finally:
            conn.close()
    else:
        print("Помилка! Не вдалося створити з'єднання з базою даних.")

async def insert_search(user_id: str, username: str, artist_query: str, song_query: str):
    artist_query, song_query = clean_track_info(artist_query, song_query)
    conn = create_connection()
    sql = """
        INSERT INTO user_searches (user_id, username, artist_query, song_query)
        VALUES (?, ?, ?, ?);
    """
    try:
        cur = conn.cursor()
        cur.execute(sql, (user_id, username, artist_query, song_query))
        conn.commit()
    except Error as e:
        print(e)
    finally:
        if conn:
            conn.close()

async def get_recent_searches(user_id: str, limit: int = 25):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT artist_query, song_query FROM user_searches WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
        (user_id, limit)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"artist": row[0], "song": row[1]} for row in rows]

