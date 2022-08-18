import logging

from sqlalchemy.exc import ProgrammingError
from sqlalchemy.sql import exists

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.callback_data import CallbackData
from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData

meta = MetaData()

logging.basicConfig(level=logging.INFO)
TOKEN = '5673734280:AAG6MskGNKJaqdugAKspyjEc9lZsUCqcmM0'
bot = Bot(token=TOKEN)
dp = Dispatcher(bot=bot)
connect_cb = CallbackData('connect', 'action', 'chat_id', 'username')
engine = create_engine('sqlite:///users.db', echo=True)
users = Table(
    'users', meta,
    Column('id', Integer, primary_key=True),
    Column('username', String),
    Column('chat_id', Integer, unique=True))

partners = Table(
    'partners', meta,
    Column('chat_id', Integer, primary_key=True),
    Column('partner_chat_id', Integer)
)
conn = engine.connect()
meta.create_all(engine)


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    q = users.select().where(users.c.chat_id == message.chat.id)
    result = conn.execute(q)
    if result.first() is None:
        ins = users.insert().values(username=message.chat.username, chat_id=message.chat.id)
        result = conn.execute(ins)
        print(result)
    await message.answer('Hello, ready to play some games? Click /play!')


async def get_users(message: types.Message):
    u = users.select()
    result = conn.execute(u)
    keyboard = InlineKeyboardMarkup()
    for row in result:
        if message.chat.username == row[1]:
            continue
        s = users.select().where(username=row[1])
        chat_id = conn.execute(s).first()[2]
        keyboard.add(InlineKeyboardButton(text=row[1], callback_data=connect_cb.new(action='request', chat_id=chat_id,
                                                                                    username=row[1])))
    await message.answer(f'All users:', reply_markup=keyboard)


# checking if row exists in table, particularly partners or users
def exists_in_table(conn, table, chat_id):
    q = table.select().where(table.c.chat_id == chat_id)
    result = conn.execute(q)
    if result.first() is None:
        return False
    else:
        return True


# creating a pull of players to choose
@dp.message_handler(commands=['play'])
async def play(message: types.Message):
    await message.answer("That's great, now choose user, which with you'd like to play:")
    await get_users(message)


# deleting a session between users
@dp.message_handler(commands=['quit'])
async def quit_dialog(message: types.Message):
    try:
        if exists_in_table(conn, partners, message.chat.id):
            q = partners.select().where(partners.c.chat_id == message.chat.id)
            result = conn.execute(q)
            row = result.first()
            await bot.send_message(row[2],
                                   'The connection was cut off by other user. Hope you had a good time')
        else:
            raise ProgrammingError
        await message.answer('Hope you had good time')
        delete_q1 = partners.delete().where(partners.c.chat_id == message.chat.id)
        delete_q2 = partners.delete().where(partners.c.chat_id == row[2])
        conn.execute(delete_q1)
        conn.execute(delete_q2)
    except ProgrammingError:
        await message.answer("You don't have any partners yet. Send me /play and I'll find you somebody to play with:)")


# requesting chosen user to create a connection
@dp.callback_query_handler(connect_cb.filter(action='request'))
async def request_to_connect(callback_query: types.CallbackQuery, callback_data: dict):
    await callback_query.answer('Request is sent. Waiting for response...')
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(InlineKeyboardButton('Yes', callback_data=connect_cb.new(action='accepted',
                                                                          chat_id=callback_query.message.chat.id,
                                                                          username=callback_query.message.chat.username)))
    keyboard.add(InlineKeyboardButton('No', callback_data=connect_cb.new(action='rejected',
                                                                         chat_id=callback_query.message.chat.id,
                                                                         username=callback_query.message.chat.username)))
    await bot.send_message(callback_data['chat_id'],
                           f"There is request from {callback_data['username']}. Do you want to play with him/her? ",
                           reply_markup=keyboard)


# accepting request and establishing connection. Adding users to database 'partners'
@dp.callback_query_handler(connect_cb.filter(action='accepted'))
async def request_accepted(callback_query: types.CallbackQuery, callback_data: dict):
    if not exists_in_table(conn, partners, callback_query.message.chat.id):
        ins_1 = partners.insert().values(chat_id=callback_query.message.chat.id,
                                         partner_chat_id=callback_data['chat_id'])
        ins_2 = partners.insert().values(chat_id=callback_data['chat_id'],
                                         partner_chat_id=callback_query.message.chat.id)
        conn.execute(ins_1)
        conn.execute(ins_2)
    await callback_query.message.answer('Connection is established. Now you can send any message to your partner!')
    await bot.send_message(callback_data['chat_id'],
                           'Your request was accepted. Now you can send any message to your partner!')


# rejecting a request
@dp.callback_query_handler(connect_cb.filter(action='rejected'))
async def request_rejected(callback_query: types.CallbackQuery, callback_data: dict):
    await callback_query.message.answer('Request is rejected')
    await bot.send_message(callback_data['chat_id'],
                           "Your request was unfortunately rejected. I am sure you'll find someone else")
    await get_users(callback_query.message)


@dp.message_handler()
async def dialogue(message: types.Message):
    q = partners.select().where(partners.c.chat_id == message.chat.id)
    result = conn.execute(q)
    try:
        partner_chat_id = result.fetchone()[1]
        await bot.send_message(partner_chat_id, message.text)
    except Exception:
        await message.answer("You don't have any partners yet. Send me /play and I'll find you somebody to play with:)")


executor.start_polling(dispatcher=dp, skip_updates=True)
