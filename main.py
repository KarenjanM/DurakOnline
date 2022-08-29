import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, \
    ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from aiogram.utils.callback_data import CallbackData
from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData
from cards import Durak, DECK

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
        s = users.select().where(users.c.username == row[1])
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


def get_partner(message):
    q = partners.select().where(partners.c.chat_id == message.chat.id)
    result = conn.execute(q)
    return result


# creating a pull of players to choose
@dp.message_handler(commands=['play'])
async def play(message: types.Message):
    await message.answer("That's great, now choose user, which with you'd like to play:")
    await get_users(message)

messages = {}


# async def create_or_edit_field(durak, chat_id=None, message: types.Message = None):
#     text = ''
#     for attacking_cards, defending_cards in durak.field.items():
#         if defending_cards is None:
#             text += f'{attacking_cards}'
#         text += f'{attacking_cards}/{defending_cards}\t'
#     try:
#         await message.edit_text(text)
#     except Exception:
#         msg = await bot.send_message(text, chat_id)
#         messages[chat_id] = msg


# deleting a session between users
@dp.message_handler(commands=['quit'])
async def quit_dialog(message: types.Message):
    try:
        if exists_in_table(conn, partners, message.chat.id):
            q = partners.select().where(partners.c.chat_id == message.chat.id)
            result = conn.execute(q)
            row = result.first()
            print(row)
            durak_games.pop(str(row[1]), None)
            durak_games.pop(str(message.chat.id), None)
            await bot.send_message(row[1],
                                   'The connection was cut off by other user. Hope you had a good time',
                                   reply_markup=ReplyKeyboardRemove())
        else:
            raise Exception
        await message.answer('Hope you had good time', reply_markup=ReplyKeyboardRemove())
        delete_q1 = partners.delete().where(partners.c.chat_id == message.chat.id)
        delete_q2 = partners.delete().where(partners.c.chat_id == row[1])
        conn.execute(delete_q1)
        conn.execute(delete_q2)
    except Exception:
        await message.answer("You don't have any partners yet. Send me /play and I'll find you somebody to play with:)")


# requesting chosen user to create a connection
@dp.callback_query_handler(connect_cb.filter(action='request'))
async def request_to_connect(callback_query: types.CallbackQuery, callback_data: dict):
    if exists_in_table(conn, partners, callback_query.message.chat.id):
        await callback_query.answer('You already have one connection and you cannot create a new one. '
                                    'Send me /quit if you want to terminate this one.')
    else:
        await callback_query.answer('Request is sent. Waiting for response...')
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(InlineKeyboardButton('Yes', callback_data=connect_cb.new(action='accepted',
                                                                              chat_id=callback_query.message.chat.id,
                                                                              username=callback_query.message.chat.username)))
        keyboard.add(InlineKeyboardButton('No', callback_data=connect_cb.new(action='rejected',
                                                                             chat_id=callback_query.message.chat.id,
                                                                             username=callback_query.message.chat.username)))
        await bot.send_message(callback_data['chat_id'],
                               f"There is request from {callback_query.message.chat.username}. "
                               f"Do you want to play with him/her? ",
                               reply_markup=keyboard)


def get_card_hand_kb(cards_list, player_index, turn):
    buttons = [[]]
    list_index = 0
    counter = 0
    for rank, suit in cards_list:
        buttons[list_index].append(KeyboardButton(f'{rank} {suit}'))
        counter += 1
        if counter % 6 == 0:
            buttons.append([])
            list_index += 1
    if player_index == turn:
        buttons.append([KeyboardButton('Отбой')])
    else:
        buttons.append([KeyboardButton('Забрать карты')])
    kb = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

    return kb


durak_games = dict()


# accepting request and establishing connection. Adding users to database 'partners'
@dp.callback_query_handler(connect_cb.filter(action='accepted'))
async def request_accepted(callback_query: types.CallbackQuery, callback_data: dict):
    if exists_in_table(conn, partners, callback_query.message.chat.id):
        await callback_query.answer('You already have one connection and you cannot create a new one. '
                                    'Send me /quit if you want to terminate this one.')
    else:
        ins_1 = partners.insert().values(chat_id=callback_query.message.chat.id,
                                         partner_chat_id=callback_data['chat_id'])
        ins_2 = partners.insert().values(chat_id=callback_data['chat_id'],
                                         partner_chat_id=callback_query.message.chat.id)
        conn.execute(ins_1)
        conn.execute(ins_2)
        durak = durak_games[str(callback_query.message.chat.id)] = Durak(callback_query.message.chat.id)
        durak_games[str(callback_data['chat_id'])] = durak
        durak.current_player.chat_id = callback_query.message.chat.id
        durak.opponent_player.chat_id = callback_data['chat_id']
        kb_1 = get_card_hand_kb(durak.current_player.cards, durak.current_player.index, durak.attacker_index)
        kb_2 = get_card_hand_kb(durak.opponent_player.cards, durak.opponent_player.index, durak.attacker_index)
        await callback_query.message.answer('The game is started!GL HF', reply_markup=kb_1)
        await callback_query.message.answer(f'The trump is {durak.trump}.')
        await bot.send_message(callback_data['chat_id'],
                               'Your request was accepted. The game is started! GL HF', reply_markup=kb_2)
        await bot.send_message(callback_data['chat_id'],
                               f'The trump is {durak.trump}.')


# rejecting a request
@dp.callback_query_handler(connect_cb.filter(action='rejected'))
async def request_rejected(callback_query: types.CallbackQuery, callback_data: dict):
    await callback_query.message.answer('Request is rejected')
    await bot.send_message(callback_data['chat_id'],
                           "Your request was unfortunately rejected. I am sure you'll find someone else")
    await get_users(callback_query.message)


@dp.message_handler(lambda msg: msg.text == 'Отбой')
async def attacker_finish(message: types.Message):
    result = get_partner(message)
    partner_chat_id = result.fetchone()[1]
    durak = durak_games[str(message.chat.id)]
    response = durak.finish_turn()
    if durak.attack_succeed and response != 'game_over':
        await message.answer('Not all your cards is beaten yet')
    else:
        if response == 'normal':
            durak.attacker_chat_id = partner_chat_id
            await message.answer('The round is over')
            await message.answer('The opponent player is now going to play. You defend.',
                                 reply_markup=get_card_hand_kb(durak.opponent_player.cards,
                                                               durak.opponent_player.index,
                                                               durak.attacker_index))
            await bot.send_message(text='The round is over', chat_id=partner_chat_id)
            await bot.send_message(text='You have beaten all the cards. It is your turn to attack!',
                                   chat_id=partner_chat_id,
                                   reply_markup=get_card_hand_kb(durak.current_player.cards,
                                                                 durak.current_player.index,
                                                                 durak.attacker_index))
        elif response == 'game_over':
            await message.answer('You have won!!! Congrats!', reply_markup=ReplyKeyboardRemove())
            await bot.send_message(partner_chat_id, 'You lose. You are DURAK.', reply_markup=ReplyKeyboardRemove())
            await quit_dialog(message)


@dp.message_handler(lambda msg: msg.text == 'Забрать карты')
async def defender_finish(message: types.Message):
    result = get_partner(message)
    partner_chat_id = result.fetchone()[1]
    durak = durak_games[str(message.chat.id)]
    if not durak.attack_succeed:
        await message.answer('You have beaten all the cards for now. You do not need to take any card')
    else:
        print(durak.field)
        response = durak.finish_turn()
        print(response, 'response')
        if response == 'took_cards':
            await message.answer('You have just taken all the cards from the field. You are going to defend again.',
                                 reply_markup=get_card_hand_kb(durak.opponent_player.cards,
                                                               durak.opponent_player.index,
                                                               durak.attacker_index)
                                 )
            await bot.send_message(partner_chat_id, 'Opponent player took all of the cards. You can attack again!',
                                   reply_markup=get_card_hand_kb(durak.current_player.cards,
                                                                 durak.current_player.index,
                                                                 durak.attacker_index))
        elif response == 'game_over':
            await message.answer('You have won!!! Congrats!', reply_markup=ReplyKeyboardRemove())
            await bot.send_message(partner_chat_id, 'You lose. You are DURAK.', reply_markup=ReplyKeyboardRemove())
            await quit_dialog(message)


@dp.message_handler(lambda msg: (msg.text.split()[0], msg.text.split()[1]) in DECK)
async def round_play(message: types.Message):
    result = get_partner(message)
    partner_chat_id = result.fetchone()[1]
    durak = durak_games[str(message.chat.id)]
    print(durak, 'object')
    if durak.attacker_chat_id == message.chat.id:
        if durak.attack((message.text.split()[0], message.text.split()[1])):
            await message.answer('Accepted!', reply_markup=get_card_hand_kb(durak.current_player.cards,
                                                                            durak.current_player.index,
                                                                            durak.attacker_index))
            if durak.is_no_cards():
                await attacker_finish(message)
            await bot.send_message(partner_chat_id, message.text)
        else:
            await message.answer('You cannot play this card right now!')
    else:
        is_defended = False
        for card in durak.attacking_cards:
            if durak.defend(card, (message.text.split()[0], message.text.split()[1])):
                await message.answer('Accepted!', reply_markup=get_card_hand_kb(durak.opponent_player.cards,
                                                                                durak.opponent_player.index,
                                                                                durak.attacker_index))
                is_defended = True
                if durak.is_no_cards():
                    await defender_finish(message)
                await bot.send_message(partner_chat_id, message.text)
                break
        if not is_defended:
            await message.answer('You cannot play this card right now!')
        # await create_or_edit_field(messages[message.chat.id])
    # except Exception:
    # await message.answer("You don't have any partners yet. Send me /play and I'll find you somebody to play with:)")


@dp.message_handler()
async def dialog(message: types.Message):
    try:
        result = get_partner(message)
        partner_chat_id = result.fetchone()[1]
        await bot.send_message(partner_chat_id, message.text)
    except Exception:
        await message.answer("You don't have any partners yet. Send me /play and I'll find you somebody to play with:)")

executor.start_polling(dispatcher=dp, skip_updates=True)
