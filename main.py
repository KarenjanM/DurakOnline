import logging
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from durak_interface import DurakInterface
from aiogram.utils.callback_data import CallbackData
from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData
from cards import Durak, DECK
from database import UsersDatabase, PartnersDatabase

meta = MetaData()
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv('TOKEN')
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

users_db = UsersDatabase(connection=conn, table=users)
partners_db = PartnersDatabase(connection=conn, table=partners)

durak_interface = DurakInterface(bot=bot, partners_db=partners_db, users_db=users_db)


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    result = users_db.select_by_id(message.chat.id)
    if result.first() is None:
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


# requesting chosen user to create a connection
@dp.callback_query_handler(connect_cb.filter(action='request'))
async def request_to_connect(callback_query: types.CallbackQuery, callback_data: dict):
    if partners_db.exists_in_table(callback_query.message.chat.id):
        await callback_query.answer('У тебя уже есть одно соединение и поэтому не можешь создать еще одно. '
                                    'Отправь мне /quit если хочешь разоровать это.')
    else:
        await callback_query.answer('Запрос отправлен. Ожидание ответа...')
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(InlineKeyboardButton('Yes', callback_data=connect_cb.new(action='accepted',
                                                                              chat_id=callback_query.message.chat.id,
                                                                              username=callback_query.message.chat.username)))
        keyboard.add(InlineKeyboardButton('No', callback_data=connect_cb.new(action='rejected',
                                                                             chat_id=callback_query.message.chat.id,
                                                                             username=callback_query.message.chat.username)))
        await bot.send_message(callback_data['chat_id'],
                               f"Есть запрос от {callback_query.message.chat.username}. "
                               f"Хочешь ли ты поиграть с ним/ней? ",
                               reply_markup=keyboard)


durak_games = dict()


# accepting request and establishing connection. Adding users to database 'partners'
@dp.callback_query_handler(connect_cb.filter(action='accepted'))
async def request_accepted(callback_query: types.CallbackQuery, callback_data: dict):
    if partners_db.exists_in_table(callback_query.message.chat.id):
        await callback_query.answer('У тебя уже есть одно соединение и поэтому не можешь создать еще одно. '
                                    'Отправь мне /quit если хочешь разоровать это.')
    else:
        partners_db.insert(callback_query.message.chat.id, callback_data['chat_id'])
        partners_db.insert(callback_data['chat_id'], callback_query.message.chat.id)

        durak = durak_games[str(callback_query.message.chat.id)] = Durak(callback_query.message.chat.id)
        durak_games[str(callback_data['chat_id'])] = durak
        durak.current_player.chat_id = callback_query.message.chat.id
        durak.opponent_player.chat_id = callback_data['chat_id']

        kb_1 = durak_interface.get_card_hand_kb(durak.current_player.cards,
                                                durak.current_player.index, durak.attacker_index)
        kb_2 = durak_interface.get_card_hand_kb(durak.opponent_player.cards,
                                                durak.opponent_player.index, durak.attacker_index)

        await callback_query.message.answer('Игра началась!GL HF', reply_markup=kb_1)
        await durak_interface.create_or_edit_field(durak, callback_query.message.chat.id)
        await bot.send_message(callback_data['chat_id'],
                               'Твой запрос был принят. Игра началась! GL HF', reply_markup=kb_2)
        await durak_interface.create_or_edit_field(durak, callback_data['chat_id'])


# rejecting a request
@dp.callback_query_handler(connect_cb.filter(action='rejected'))
async def request_rejected(callback_query: types.CallbackQuery, callback_data: dict):
    await callback_query.message.answer('Запрос отклонен.')
    await bot.send_message(callback_data['chat_id'],
                           "Твой запрос был, к сожалению, отклонен. Я уверен ты найдешь еще кого-нибудь")
    await get_users(callback_query.message)


@dp.message_handler(lambda msg: msg.text == 'Отбой')
async def attacker_finish(message: types.Message, is_game_over=False):
    result = partners_db.select_by_id(message.chat.id)
    partner_chat_id = result.fetchone()[1]
    durak = durak_games[str(message.chat.id)]
    if durak.attack_succeed and not is_game_over:
        await message.answer('Не все карты еще побиты.')
    else:
        response = durak.finish_turn()
        if response == 'normal':
            await durak_interface.normal_finish(durak, message.chat.id, partner_chat_id)
        elif response == 'game_over':
            await message.answer('Ты победил!!! Поздравляю!', reply_markup=ReplyKeyboardRemove())
            await bot.send_message(partner_chat_id, 'Ты проирал. Ты ДУРАК.', reply_markup=ReplyKeyboardRemove())
            await quit_dialog(message)


@dp.message_handler(lambda msg: msg.text == 'Забрать карты')
async def defender_finish(message: types.Message):
    result = partners_db.select_by_id(message.chat.id)
    partner_chat_id = result.fetchone()[1]
    durak = durak_games[str(message.chat.id)]
    if not durak.attack_succeed:
        await message.answer('Ты побил пока все карты. Тебе не нужно ничего забирать')
    else:
        response = durak.finish_turn()
        if response == 'took_cards':
            await durak_interface.took_cards_finish(durak, message.chat.id, partner_chat_id)
        elif response == 'game_over':
            await message.answer('Ты победил!!! Поздравляю!', reply_markup=ReplyKeyboardRemove())
            await bot.send_message(partner_chat_id, 'Ты проирал. Ты ДУРАК.', reply_markup=ReplyKeyboardRemove())
            await quit_dialog(message)


@dp.message_handler(lambda msg: (msg.text.split()[0], msg.text.split()[1]) in DECK)
async def round_play(message: types.Message):
    result = partners_db.select_by_id(message.chat.id)
    partner_chat_id = result.fetchone()[1]
    durak = durak_games[str(message.chat.id)]
    if durak.attacker_chat_id == message.chat.id:
        if durak.attack((message.text.split()[0], message.text.split()[1])):
            await message.answer('Принято!', reply_markup=durak_interface.get_card_hand_kb(durak.current_player.cards,
                                                                           durak.current_player.index,
                                                                           durak.attacker_index))
            if durak.is_no_cards():
                await attacker_finish(message, True)
            await bot.send_message(partner_chat_id, message.text)
        else:
            await message.answer('Ты не можешь играть этой картой сейчас!')
    else:
        is_defended = False
        for card in durak.attacking_cards:
            if durak.defend(card, (message.text.split()[0], message.text.split()[1])):
                await message.answer('Принято!',
                                     reply_markup=durak_interface.get_card_hand_kb(durak.opponent_player.cards,
                                                                                   durak.opponent_player.index,
                                                                                   durak.attacker_index))
                is_defended = True
                if durak.is_no_cards():
                    await defender_finish(message)
                await bot.send_message(partner_chat_id, message.text)
                break
        if not is_defended:
            await message.answer('Ты не можешь играть этой картой сейчас!')
    await durak_interface.create_or_edit_field(durak, message=durak_interface.messages[str(message.chat.id)])
    await durak_interface.create_or_edit_field(durak, message=durak_interface.messages[str(partner_chat_id)])


@dp.message_handler()
async def dialog(message: types.Message):
    try:
        result = partners_db.select_by_id(message.chat.id)
        partner_chat_id = result.fetchone()[1]
        await bot.send_message(partner_chat_id, message.text)
    except Exception:
        await message.answer("У тебя нету партнеров пока что. Отправь мне /play и я найду с кем тебе поиграть:)")

executor.start_polling(dispatcher=dp, skip_updates=True)
