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
            self.conn.execute("""CREATE TABLE IF NOT EXISTS all_feedbacks(
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               user_id INTEGER NOT NULL,
               username TEXT,
               message TEXT,
               estimation INTEGER,
               timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
               is_current BOOLEAN DEFAULT TRUE
        )""")
            
    def insert_questions(self):
        default_questions = [
            ("Бот не отвечает", "Проверьте интернет-соединение. Если проблема не исчезнет, обратитесь к @dimon_chad69"),
            ("Как найти меню?", "По правилу у вас должна автоматически выйти клавиатура где и находится меню. Если же она пропала то нажмите на окошко возле кнопки отправить. Если данного окошка вовсе нет то обратитесь к администратору."),
            ("Для чего нужны артефакты?", "Когда соберёте каждый артифакт, они будут ключом для концовки игры"),
            ("Как использовать еду?", "Чтобы отправиться в путешестивие вам нужно иметь минимум 20 единиц еды которые у вас потом отберутся после путешествия,чтобы заработать еду вы должны идти на охоту"),
            ("Для чего мне нужны монеты, дерево и камни?", "Вам нужны ресурсы чтобы улучшать свой дом и в итоге пройти игру полностью"),
            ("Где мои данные?", "Ваши данные хранятся безопасно в нашей базе данных при помощи библиотеки sqlite")
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
            
    def save_feedback(self, user_id, username, message, estimation=None):
     with self.conn:
        try:
           
            self.conn.execute(
                "UPDATE all_feedbacks SET is_current = FALSE WHERE user_id = ?",
                (user_id,)
            )
            
   
            self.conn.execute(
                """INSERT INTO all_feedbacks 
                (user_id, username, message, estimation) 
                VALUES (?, ?, ?, ?)""",
                (user_id, username, message, estimation)
            )
            return True
        except sqlite3.Error as e:
            print(f"Ошибка сохранения отзыва: {e}")
            return False
    
    def get_average_rating(self):
     with self.conn:
        cursor = self.conn.execute(
            "SELECT AVG(estimation) FROM all_feedbacks WHERE estimation IS NOT NULL AND is_current = TRUE"
        )
        result = cursor.fetchone()[0]
        return round(result, 2) if result else None
    
    def get_feedbacks(self, offset=0, limit=5):
     with self.conn:
        cursor = self.conn.execute(
            """SELECT * FROM all_feedbacks 
            WHERE is_current = TRUE
            ORDER BY timestamp DESC 
            LIMIT ? OFFSET ?""",
            (limit, offset)
        )
        return cursor.fetchall()


    def get_feedback_count(self):
     with self.conn:
        cursor = self.conn.execute(
            "SELECT COUNT(*) FROM all_feedbacks WHERE is_current = TRUE"
        )
        return cursor.fetchone()[0]
     
     