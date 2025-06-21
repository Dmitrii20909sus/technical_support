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
    markup.add(types.KeyboardButton("Оставить отзыв"))
    markup.add(types.KeyboardButton("Все отзывы"))
    return markup

def create_questions_keyboard():
    questions = manager.get_all_questions()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    for question in questions:
        markup.add(types.KeyboardButton(question))
    markup.add(types.KeyboardButton("Другое")) 
    markup.add(types.KeyboardButton('Назад в меню'))
    return markup

@bot.message_handler(commands=['start'])
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

@bot.message_handler(func=lambda message: message.text == "Оставить отзыв")
def _send_feedback(message):
    markup = types.InlineKeyboardMarkup()
    yes = types.InlineKeyboardButton("Оставить отзыв", callback_data="yes")
    markup.add(yes)
    bot.send_message(
        message.chat.id, " Нажмите сюда чтобы оставить отзыв", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "Все отзывы")
def show_feedbacks(message):
    
    feedbacks = manager.get_feedbacks()
    total = manager.get_feedback_count()

    if not feedbacks:
        bot.send_message(message.chat.id, "Пока нету отзывов")
        return
    
    avg_rating = manager.get_average_rating()
    response = format_feedbacks(feedbacks, 0, total, avg_rating=avg_rating)
    markup = create_pagination_markup(0, total)
    bot.send_message(message.chat.id, response, reply_markup=markup)

    
def format_feedbacks(feedbacks, offset, total, avg_rating=None):
    text = "📊 Статистика отзывов\n"
    if avg_rating is not None:
        text += f"⭐ Средний рейтинг: {avg_rating}/5\n\n"
    text += f"📝 Отзывы ({offset+1}-{min(offset+len(feedbacks),total)} из {total}):\n\n"
    for fb in feedbacks:
        try:
            user_info = f"👤 Пользователь: {'@' + fb[2] if fb[2] else 'Аноним'} \n"
            text += (
                user_info )
            text += (   f"⭐ Оценка: {fb[4] if fb[4] is not None else 'Хз'}/5\n")
            
            if fb[3] is not None:                             
              text += (  f"📄 Комментарий: {fb[3]}\n")
            text += (   
                f"📅 Дата: {fb[5]}\n"
                f"━━━━━━━━━━━━\n"
                 )     
        except IndexError:
            text += f"⚠️ Ошибка формата отзыва (ID: {fb[0] if fb else 'неизвестно'})\n━━━━━━━━━━━━\n"
    return text

def create_pagination_markup(offset, total):
    markup = types.InlineKeyboardMarkup()
    if offset > 0:
        markup.add(types.InlineKeyboardButton("◀️ Prev", callback_data=f"fb_prev_{offset}"))
    if offset + 5 < total:
        markup.add(types.InlineKeyboardButton("Next ▶️", callback_data=f"fb_next_{offset}"))
    return markup

@bot.callback_query_handler(func=lambda call: call.data.startswith(('fb_prev_', 'fb_next_')))
def handle_pagination(call):
    if call.from_user.id != ADMIN_ID:
        return
    
    action, offset = call.data.split('_')[1], int(call.data.split('_')[2])
    new_offset = offset - 5 if action == 'prev' else offset + 5
    
    feedbacks = manager.get_feedbacks(new_offset)
    total = manager.get_feedback_count()
    
    if not feedbacks:
        return
    
    response = format_feedbacks(feedbacks, new_offset, total)
    markup = create_pagination_markup(new_offset, total)
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=response,
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
        markup = types.InlineKeyboardMarkup()
        yes = types.InlineKeyboardButton("Да, оставить отзыв", callback_data="yes")
        no = types.InlineKeyboardButton("Нет, связатся с администрацией", callback_data="no")
        markup.add(yes, no)
        bot.send_message(user_id, "Вам помогла данная информация?", reply_markup=markup)
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
    user_id = message.chat.id
    answer = manager.get_answer(message.text)
    if answer:
        markup = types.InlineKeyboardMarkup()
        yes = types.InlineKeyboardButton("Да, оставить отзыв", callback_data="yes")
        no = types.InlineKeyboardButton("Нет, связатся с администрацией", callback_data="no")
        markup.add(yes, no)
        bot.send_message(user_id, answer)
        bot.send_message(user_id, "Вам помогла данная информация?", reply_markup=markup)
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



@bot.callback_query_handler(func=lambda call: call.data == "yes")
def handle_yes(call):
    markup = types.InlineKeyboardMarkup(row_width=5)
    markup.add(
        types.InlineKeyboardButton("1", callback_data="feedback_1"),
        types.InlineKeyboardButton("2", callback_data="feedback_2"),
        types.InlineKeyboardButton("3", callback_data="feedback_3"),
        types.InlineKeyboardButton("4", callback_data="feedback_4"),
        types.InlineKeyboardButton("5", callback_data="feedback_5")
    )
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Оцените сервис от 1 до 5 (5 - отлично):",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("feedback_"))
def process_feedback_rating(call):
    rating = int(call.data.split("_")[1])
    

    user_states[call.from_user.id] = {"rating": rating}
    
   
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("Оставить комментарий", callback_data="leave_comment"),
        types.InlineKeyboardButton("Пропустить", callback_data="skip_comment")
    )
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"Вы поставили {rating}/5. Хотите добавить комментарий?",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "leave_comment")
def ask_for_comment(call):
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Напишите ваш комментарий:"
    )
    
   
    bot.register_next_step_handler_by_chat_id(
        call.message.chat.id, 
        save_feedback_with_comment,
        call.from_user.id
    )

@bot.callback_query_handler(func=lambda call: call.data == "skip_comment")
def skip_comment(call):
    user_id = call.from_user.id
    username = call.from_user.username or call.from_user.first_name

    manager.save_feedback(
        user_id=user_id,
        username=username,
        message=None,
        estimation=user_states[user_id]["rating"]
    )
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"✅ Спасибо за оценку {user_states[user_id]['rating']}/5!",
    )
    
 
    bot.send_message(
        call.message.chat.id,
        "Выберите действие:",
        reply_markup=create_main_keyboard()
    )
def save_feedback_with_comment(message, user_id):
    username = message.from_user.username or message.from_user.first_name
    
    success = manager.save_feedback(
        user_id=user_id,
        username=username,
        message=message.text,
        estimation=user_states[user_id]["rating"]
    )
    
    if success:
        bot.send_message(
            message.chat.id,
            f"✅ Спасибо за ваш отзыв {user_states[user_id]['rating']}/5! "
            "Ваша оценка обновлена.",
            reply_markup=create_main_keyboard()
        )
    else:
        bot.send_message(
            message.chat.id,
            "⚠️ Произошла ошибка при сохранении отзыва",
            reply_markup=create_main_keyboard()
        )
@bot.callback_query_handler(func=lambda call: call.data == "no")
def handle_no(call):
    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        "Пожалуйста, напишите ваш вопрос администратору:",
        reply_markup=types.ForceReply(selective=True)
    )
    user_states[call.message.chat.id] = "message_question"



if __name__ == '__main__':
    bot.polling(none_stop=True)