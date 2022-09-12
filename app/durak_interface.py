from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram import types


class DurakInterface:
    def __init__(self, bot, partners_db, users_db):
        self.bot = bot
        self.users_db = users_db
        self.partners_db = partners_db
        self.messages = {}

    def delete_message(self, chat_id):
        self.messages.pop(str(chat_id), None)

    @staticmethod
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

    async def create_or_edit_field(self, durak, chat_id=None, message: types.Message = None):
        text = ''
        text += f'Козырь {durak.trump}. Оставшиеся количество карт в колоде: {durak.get_n_cards}\n'
        partner_chat_id = durak.attacker_chat_id
        username = self.users_db.select_by_id(chat_id=partner_chat_id).fetchone()[1]
        text += f'Пользователь @{username} ходит.\n'

        for attacking_cards, defending_cards in durak.field.items():
            if defending_cards is None:
                text += f'{attacking_cards[0]} {attacking_cards[1]}    '
            else:
                text += f'{attacking_cards[0]} {attacking_cards[1]} / {defending_cards[0]} {defending_cards[1]}    '
        try:
            await message.edit_text(text)
        except Exception:
            msg = await self.bot.send_message(chat_id, text)
            self.messages[str(chat_id)] = msg

    async def normal_finish(self, durak, chat_id, partner_chat_id):
        durak.attacker_chat_id = partner_chat_id
        await self.bot.send_message(chat_id, 'Раунд окончен')
        await self.bot.send_message(chat_id, 'Теперь начинает оппонент. Ты защищаешься.',
                                    reply_markup=self.get_card_hand_kb(durak.opponent_player.cards,
                                                                       durak.opponent_player.index,
                                                                       durak.attacker_index))
        await self.bot.send_message(text='Раунд окончен', chat_id=partner_chat_id)
        await self.bot.send_message(text='Ты побил все карты. Теперь твоя очередь атаковать.',
                                    chat_id=partner_chat_id,
                                    reply_markup=self.get_card_hand_kb(durak.current_player.cards,
                                                                       durak.current_player.index,
                                                                       durak.attacker_index))
        await self.create_or_edit_field(durak, chat_id)
        await self.create_or_edit_field(durak, partner_chat_id)

    async def took_cards_finish(self, durak, chat_id, partner_chat_id):
        await self.bot.send_message(chat_id, 'Ты забрал все карты с поля. Ты будешь снова отбиваться.',
                                    reply_markup=self.get_card_hand_kb(durak.opponent_player.cards,
                                                                       durak.opponent_player.index,
                                                                       durak.attacker_index))
        await self.bot.send_message(partner_chat_id, 'Оппонент забрал все карты. Ты можешь атаковать снова!',
                                    reply_markup=self.get_card_hand_kb(durak.current_player.cards,
                                                                       durak.current_player.index,
                                                                       durak.attacker_index))
        await self.create_or_edit_field(durak, chat_id)
        await self.create_or_edit_field(durak, partner_chat_id)

