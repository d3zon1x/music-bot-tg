# db.py
import sqlite3
from sqlite3 import Error

DATABASE = "music_bot.db"

def create_connection():
    conn = None
    try:
        conn = sqlite3.connect(DATABASE)
        return conn
    except Error as e:
        print(e)
    return conn

def init_db():
    conn = create_connection()
    if conn is not None:
        create_table_sql = """
            CREATE TABLE IF NOT EXISTS user_searches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                username TEXT,
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

def insert_search(user_id: str, username: str, song_query: str):

    conn = create_connection()
    sql = """
        INSERT INTO user_searches (user_id, username, song_query)
        VALUES (?, ?, ?)
    """
    try:
        cur = conn.cursor()
        cur.execute(sql, (user_id, username, song_query))
        conn.commit()
    except Error as e:
        print(e)
    finally:
        if conn:
            conn.close()
