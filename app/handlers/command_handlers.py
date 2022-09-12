from aiogram import types, Dispatcher
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from create_bot import users_db, connect_cb, partners_db, durak_interface, durak_games, dp, bot


async def start(message: types.Message):
    result = users_db.select_by_id(message.chat.id)
    if result.first() is None:
        if message.chat.username is None:
            users_db.insert('unknown', chat_id=message.chat.id)
        else:
            users_db.insert(message.chat.username, chat_id=message.chat.id)
    await message.answer('Привет, ты готов играть? Тогда смело отправляй мне /play!')


async def get_users(message: types.Message):
    result = users_db.select_all()
    keyboard = InlineKeyboardMarkup()
    for row in result:
        if message.chat.username == row[1]:
            continue
        result = users_db.select_by_username(row[1])
        chat_id = result.first()[2]
        keyboard.add(InlineKeyboardButton(text=row[1], callback_data=connect_cb.new(action='request', chat_id=chat_id,
                                                                                    username=row[1])))
    await message.answer(f'Все пользователи:', reply_markup=keyboard)


# creating a pull of players to choose
@dp.message_handler(commands=['play'])
async def play(message: types.Message):
    await message.answer("Замечательно, теперь выбери пользователя, с котором ты бы хотел поиграть:")
    await get_users(message)


# deleting a session between users
@dp.message_handler(commands=['quit'])
async def quit_dialog(message: types.Message):
    try:
        if partners_db.exists_in_table(message.chat.id):
            result = partners_db.select_by_id(chat_id=message.chat.id)
            row = result.first()

            durak_games.pop(str(row[1]), None)
            durak_games.pop(str(message.chat.id), None)
            durak_interface.delete_message(str(message.chat.id))
            durak_interface.delete_message(str(row[1]))

            await bot.send_message(row[1],
                                   'Соединение было разорвано другим пользователем. Надеюсь ты хорошо провел время',
                                   reply_markup=ReplyKeyboardRemove())
        else:
            raise Exception
        await message.answer('Надеюсь ты хорошо провел время', reply_markup=ReplyKeyboardRemove())
        partners_db.delete_by_id(message.chat.id)
        partners_db.delete_by_id(row[1])
    except Exception:
        await message.answer("У тебя нету партнеров пока что. Отправь мне /play и я найду с кем тебе поиграть:)")


def register_command_handlers(dp: Dispatcher):
    dp.register_message_handler(start, commands=['start'])
    dp.register_message_handler(play, commands=['play'])
    dp.register_message_handler(quit_dialog, commands=['quit'])