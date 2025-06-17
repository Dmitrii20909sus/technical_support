import sqlite3
from telebot import types

class DB_Manager:
    def __init__(self, database):
        self.database = database
        self.conn = sqlite3.connect(self.database, check_same_thread=False)
        self.create_tables()
        self.insert_questions()

    def create_tables(self):
        with self.conn:
            self.conn.execute("""CREATE TABLE IF NOT EXISTS questions(
                id INTEGER PRIMARY KEY,
                question TEXT UNIQUE,
                answer TEXT)""")
            self.conn.execute("""CREATE TABLE IF NOT EXISTS user_messages(
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                username TEXT,
                message TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                category TEXT,
                status TEXT DEFAULT 'pending')""") 
            
    def insert_questions(self):
        default_questions = [
            ("Бот не отвечает", "Проверьте интернет-соединение. Если проблема не исчезнет, обратитесь к @dimon_chad69"),
            ("Как пользоваться ботом?", "!!! дома доделаю"),
            ("Где мои данные?", "Ваши данные хранятся безопасно в нашей базе данных")
        ]
        with self.conn:
            self.conn.executemany("INSERT OR IGNORE INTO questions (question, answer) VALUES (?, ?)", default_questions)

    def get_all_questions(self):
        with self.conn:
            cursor = self.conn.execute("SELECT question FROM questions ORDER BY id")
            return [row[0] for row in cursor.fetchall()]

    def get_answer(self, question):
        with self.conn:
            cursor = self.conn.execute("SELECT answer FROM questions WHERE question = ?", (question,))
            result = cursor.fetchone()
            return result[0] if result else None

    def save_user_message(self, user_id, username, message, category, status='pending'): 
        with self.conn:
            self.conn.execute("INSERT INTO user_messages (user_id, username, message, category, status) VALUES (?, ?, ?, ?, ?)", 
                            (user_id, username, message, category, status))
            
  