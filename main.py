from telebot import TeleBot, types
from logic import DB_Manager
from config import *
import sqlite3

bot = TeleBot(token)
manager = DB_Manager(database)
ADMIN_ID = admin_id  
user_states = {}

def create_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Не могу разобраться"))
    markup.add(types.KeyboardButton("Нашел ошибку"))
    return markup

def create_questions_keyboard():
    questions = manager.get_all_questions()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    for question in questions:
        markup.add(types.KeyboardButton(question))
    markup.add(types.KeyboardButton("Другое")) 
    markup.add(types.KeyboardButton('Назад в меню'))
    return markup

@bot.message_handler(commands=['start', 'help'])
def start_command(message):
    user_states[message.chat.id] = None
    bot.send_message(
        message.chat.id,
        "Выберите действие:",
        reply_markup=create_main_keyboard()
    )

@bot.message_handler(func=lambda message: message.text == "Не могу разобраться")
def show_questions(message):
    user_states[message.chat.id] = None
    bot.send_message(
        message.chat.id,
        "Выберите вопрос или 'Другое' для связи с администратором:",
        reply_markup=create_questions_keyboard()
    )

@bot.message_handler(func=lambda message: message.text == "Другое")
def other_option(message):
    user_states[message.chat.id] = 'message_question'
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Отмена"))
    bot.send_message(
        message.chat.id,
        "Напишите ваш вопрос администратору:",
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: message.text == "Нашел ошибку")
def report_problem(message):
    user_states[message.chat.id] = 'message_problem'
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Отмена"))
    bot.send_message(
        message.chat.id,
        "Напишите вами найденную ошибку администратору:",
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: user_states.get(message.chat.id) == 'message_problem')
def handle_user_problem(message):
    if message.text == "Отмена":
        user_states[message.chat.id] = None
        bot.send_message(
            message.chat.id,
            "Отправка отменена.",
            reply_markup=create_main_keyboard()
        )
        return
    
    if len(message.text) > 500:
        bot.send_message(message.chat.id, "Сообщение слишком длинное (макс. 500 символов)")
        return
    
    username = message.from_user.username or message.from_user.first_name
    manager.save_user_message(message.chat.id, username, message.text, "problem")
    
    bot.send_message(
        message.chat.id,
        "✅ Ваше сообщение об ошибке отправлено администратору",
        reply_markup=create_main_keyboard()
    ) 
    
    markup = types.InlineKeyboardMarkup()
    answer = types.InlineKeyboardButton("Ответить", callback_data="answer")
    markup.add(answer)
    
    admin_msg = f"⚠️ Сообщение об ошибке от @{username} (ID: {message.chat.id}):\n\n{message.text}"
    bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup)
    
    user_states[message.chat.id] = None

@bot.message_handler(func=lambda message: user_states.get(message.chat.id) == 'message_question')
def handle_user_question(message):
    if message.text == "Отмена":
        user_states[message.chat.id] = None
        bot.send_message(
            message.chat.id,
            "Отправка отменена.",
            reply_markup=create_questions_keyboard()
        )
        return
    
    if len(message.text) > 500:
        bot.send_message(message.chat.id, "Сообщение слишком длинное (макс. 500 символов)")
        return
    
    username = message.from_user.username or message.from_user.first_name
    manager.save_user_message(message.chat.id, username, message.text, "question")
    
    bot.send_message(
        message.chat.id,
        "✅ Ваш вопрос отправлен администратору",
        reply_markup=create_main_keyboard()
    )
    markup = types.InlineKeyboardMarkup()
    answer = types.InlineKeyboardButton("Ответить", callback_data="answer")
    markup.add(answer)
    admin_msg = f"❓ Вопрос от @{username} (ID: {message.chat.id}):\n\n{message.text}"
    bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup)
    
    user_states[message.chat.id] = None

@bot.callback_query_handler(func=lambda call: call.data == "answer")
def handle_answer_callback(call):
    admin_message_id = call.message.message_id
    user_message_text = call.message.text.split("\n\n")[-1]
    
    try:
        user_id = int(call.message.text.split("ID: ")[1].split(")")[0])
    except (IndexError, ValueError):
        bot.answer_callback_query(call.id, "Ошибка: не удалось определить ID пользователя")
        return
    
    msg = bot.send_message(
        call.from_user.id, 
        f"Введите ответ для пользователя (ID: {user_id}):\n\n{user_message_text}\n\n"
        "Напишите 'отмена' для отмены"
    )
    
    bot.register_next_step_handler(msg, process_admin_reply, user_id, admin_message_id)

def process_admin_reply(message, user_id, admin_message_id):
    if message.text.lower() in ("отмена", "cancel"):
        bot.send_message(message.chat.id, "Ответ отменён")
        return
    
    try:
        bot.send_message(
            user_id,
            f"📨 Ответ администратора:\n\n{message.text}"
        )
    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"Не удалось отправить сообщение пользователю: {e}"
        )
        return
    
    try:
        with sqlite3.connect(database) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE user_messages SET status = 'answered' WHERE id = ("
                "SELECT id FROM user_messages WHERE user_id = ? "
                "ORDER BY timestamp DESC LIMIT 1"
                ")",
                (user_id,)
            )
            conn.commit()
    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"Ошибка при обновлении статуса: {e}"
        )
    
    try:
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=admin_message_id,
            text=f"✅ Ответ отправлен пользователю (ID: {user_id}):\n\n{message.text}"
        )
    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"Не удалось обновить сообщение: {e}"
        )
    
    bot.send_message(message.chat.id, "Ответ успешно отправлен!")

@bot.message_handler(func=lambda message: message.text == "Назад в меню")
def back_to_menu(message):
    user_states[message.chat.id] = None
    bot.send_message(
        message.chat.id,
        "Главное меню:",
        reply_markup=create_main_keyboard()
    )

@bot.message_handler(func=lambda message: True)
def answer_question(message):
    answer = manager.get_answer(message.text)
    if answer:
        bot.send_message(message.chat.id, answer)
    else:
        bot.send_message(
            message.chat.id,
            "Пожалуйста, используйте кнопки меню.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        bot.send_message(
            message.chat.id,
            "Выберите действие:",
            reply_markup=create_main_keyboard()
        )

if __name__ == '__main__':
    bot.polling(none_stop=True)