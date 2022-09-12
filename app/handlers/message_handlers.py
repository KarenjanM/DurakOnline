from aiogram import types
from aiogram.types import ReplyKeyboardRemove
from create_bot import partners_db, durak_games, durak_interface, bot, dp, Dispatcher
from cards import DECK
from .command_handlers import quit_dialog


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


def is_in_deck(msg):
    try:
        return (msg.text.split()[0], msg.text.split()[1]) in DECK
    except (ValueError, IndexError) as e:
        return False


async def round_play(message: types.Message):
    result = partners_db.select_by_id(message.chat.id)
    partner_chat_id = result.fetchone()[1]
    durak = durak_games[str(message.chat.id)]
    is_changed = False
    if durak.attacker_chat_id == message.chat.id:
        if durak.attack((message.text.split()[0], message.text.split()[1])):
            await message.answer('Принято!', reply_markup=durak_interface.get_card_hand_kb(durak.current_player.cards,
                                                                           durak.current_player.index,
                                                                           durak.attacker_index))
            if durak.is_no_cards():
                await attacker_finish(message, True)
            await bot.send_message(partner_chat_id, message.text)
            is_changed = True
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
                is_changed = True
                if durak.is_no_cards():
                    await defender_finish(message)
                await bot.send_message(partner_chat_id, message.text)
                break
        if not is_defended:
            await message.answer('Ты не можешь играть этой картой сейчас!')
    if is_changed:
        await durak_interface.create_or_edit_field(durak, message=durak_interface.messages[str(message.chat.id)])
        await durak_interface.create_or_edit_field(durak, message=durak_interface.messages[str(partner_chat_id)])


async def dialog(message: types.Message):
    try:
        result = partners_db.select_by_id(message.chat.id)
        partner_chat_id = result.fetchone()[1]
        await bot.send_message(partner_chat_id, message.text)
    except Exception:
        await message.answer("У тебя нету партнеров пока что. Отправь мне /play и я найду с кем тебе поиграть:)")


def register_message_handlers(dp: Dispatcher):
    dp.register_message_handler(attacker_finish, lambda msg: msg.text == 'Отбой')
    dp.register_message_handler(defender_finish, lambda msg: msg.text == 'Забрать карты')
    dp.register_message_handler(round_play, is_in_deck)
    dp.register_message_handler(dialog)
