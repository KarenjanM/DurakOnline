from aiogram import types, Dispatcher
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from cards import Durak
from create_bot import dp, bot, connect_cb, partners_db, durak_interface, durak_games
from .command_handlers import get_users


# requesting chosen user to create a connection
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


# accepting request and establishing connection. Adding users to database 'partners'
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
async def request_rejected(callback_query: types.CallbackQuery, callback_data: dict):
    await callback_query.message.answer('Запрос отклонен.')
    await bot.send_message(callback_data['chat_id'],
                           "Твой запрос был, к сожалению, отклонен. Я уверен ты найдешь еще кого-нибудь")
    await get_users(callback_query.message)


def register_cbq_handlers(dp: Dispatcher):
    dp.register_callback_query_handler(request_to_connect, connect_cb.filter(action='request'))
    dp.register_callback_query_handler(request_accepted, connect_cb.filter(action='accepted'))
    dp.register_callback_query_handler(request_rejected, connect_cb.filter(action='rejected'))
