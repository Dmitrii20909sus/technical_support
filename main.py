from telebot import TeleBot, types
from logic import DB_Manager
from config import *

bot = TeleBot(token)
manager = DB_Manager(database)
ADMIN_ID = admin_id  
user_states = {}

def create_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Не могу разобраться"))
    markup.add(types.KeyboardButton("Другое"))  # Добавлено в главное меню
    return markup

def create_questions_keyboard():
    questions = manager.get_all_questions()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    for question in questions:
        markup.add(types.KeyboardButton(question))
    markup.add(types.KeyboardButton("Другое"))  # Также добавлено в меню вопросов
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
    user_states[message.chat.id] = 'waiting_message'
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Отмена"))
    bot.send_message(
        message.chat.id,
        "Напишите ваш вопрос администратору:",
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: user_states.get(message.chat.id) == 'waiting_message')
def handle_user_message(message):
    if message.text == "Отмена":
        user_states[message.chat.id] = None
        bot.send_message(
            message.chat.id,
            "Отправка отменена.",
            reply_markup=create_questions_keyboard()
        )
        return
    
    username = message.from_user.username or message.from_user.first_name
    manager.save_user_message(message.chat.id, username, message.text)
    
    bot.send_message(
        message.chat.id,
        "✅ Ваше сообщение отправлено администратору",
        reply_markup=create_main_keyboard()
    )
    
    admin_msg = f"✉️ Новое сообщение от @{username} (ID: {message.chat.id}):\n\n{message.text}"
    bot.send_message(ADMIN_ID, admin_msg)
    
    user_states[message.chat.id] = None

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
            reply_markup=create_main_keyboard()
        )

if __name__ == '__main__':
    bot.polling(none_stop=True)