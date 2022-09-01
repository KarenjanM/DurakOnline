import random


# suits
SPADES = '♠'
HEARTS = '♥'
DIAMS = '♦'
CLUBS = '♣'

# ranks
RANKS = ['6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']

NAME_TO_VALUE = {n: i for i, n in enumerate(RANKS)}

CARDS_IN_HAND_MAX = 6

N_PLAYERS = 2

DECK = [(nom, suit) for nom in RANKS for suit in [SPADES, HEARTS, DIAMS, CLUBS]]


class Player:
    def __init__(self, index, cards):
        self.index = index
        self.cards = list(map(tuple, cards))

    def take_cards_from_deck(self, deck: list):
        """
        Взять недостающее количество карт из колоды
        Колода уменьшится
        :param deck: список карт колоды
        """
        lack = max(0, CARDS_IN_HAND_MAX - len(self.cards))
        n = min(len(deck), lack)
        self.add_cards(deck[:n])
        del deck[:n]
        return self

    def sort_hand(self):
        """
        Сортирует карты по достоинству и масти
        """
        self.cards.sort(key=lambda c: (NAME_TO_VALUE[c[0]], c[1]))
        return self

    def add_cards(self, cards):
        self.cards += list(cards)
        self.sort_hand()
        return self

    def take_card(self, card):
        self.cards.remove(card)

    @property
    def n_cards(self):
        return len(self.cards)

    def __getitem__(self, item):
        return self.cards[item]

    def __repr__(self):
        return f"Player{self.cards}"


def rotate(l, n):
    return l[n:] + l[:n]


class Durak:
    def __init__(self, chat_id, rng: random.Random = None):
        self.rng = rng or random.Random()

        self.deck = list(DECK)
        self.rng.shuffle(self.deck)

        self.players = [Player(i, []).take_cards_from_deck(self.deck)
                        for i in range(N_PLAYERS)]

        self.trump = self.deck[0][1]

        # кладем козырь под низ вращая список по кругу на 1 назад
        self.deck = rotate(self.deck, -1)

        # игровое поле: ключ - атакующая карта, значения - защищающаяся или None
        self.field = {}

        self.attacker_chat_id = chat_id
        self.attacker_index = 0
        self.winner = None

    @property
    def get_n_cards(self):
        return len(self.deck)

    @property
    def attacking_cards(self):
        """
        List of attacking cards
        """
        return list(filter(bool, self.field.keys()))

    @property
    def defending_cards(self):
        """
        List of defending cards (filtering None)
        """
        return list(filter(bool, self.field.values()))

    @property
    def any_unbeaten_card(self):
        """
        If there is any unbeaten cards
        """
        return any(c is None for c in self.defending_cards)

    @property
    def current_player(self):
        return self.players[self.attacker_index]

    @property
    def opponent_player(self):
        return self.players[(self.attacker_index + 1) % N_PLAYERS]

    def attack(self, card):
        assert not self.winner  # игра не должна быть окончена!

        if not self.can_add_to_field(card):
            return False
        cur, opp = self.current_player, self.opponent_player
        cur.take_card(card)
        self.field[card] = None
        return True

    def can_add_to_field(self, card):
        if not self.field:
            # it is always possible to add card to the field
            return True

        # среди всех атакующих и отбивающих карт ищем совпадения по достоинствам
        for attack_card, defend_card in self.field.items():
            if self.card_match(attack_card, card) or self.card_match(defend_card, card):
                return True
        return False

    @staticmethod
    def card_match(card1, card2):
        if card1 is None or card2 is None:
            return False
        n1, _ = card1
        n2, _ = card2
        return n1 == n2

    def defend(self, attacking_card, defending_card):
        """
        Защита
        :param attacking_card: which card is to beat
        :param defending_card: which card is to defend
        :return: bool - success or not
        """
        assert not self.winner

        if self.field[attacking_card] is not None:
            # если эта карта уже отбита - уходим
            return False
        if self.can_beat(attacking_card, defending_card):
            # еслии можем побить, то кладем ее на поле
            self.field[attacking_card] = defending_card
            # и изымаем из руки защищающегося
            self.opponent_player.take_card(defending_card)
            return True
        return False

    def can_beat(self, card1, card2):
        """
        Does card1 beat card2?
        """
        nom1, suit1 = card1
        nom2, suit2 = card2

        nom1 = NAME_TO_VALUE[nom1]
        nom2 = NAME_TO_VALUE[nom2]

        if suit2 == self.trump:
            # if trump, then beat any card, which is not trump or trump but with lower rank
            return suit1 != self.trump or nom2 > nom1
        elif suit1 == suit2:
            # otherwise suits should be equal and lower rank
            return nom2 > nom1
        else:
            return False

    NORMAL = 'normal'
    TOOK_CARDS = 'took_cards'
    GAME_OVER = 'game_over'

    def is_no_cards(self):
        if not self.deck:
            if not self.current_player.cards:
                return True
        if not self.opponent_player.cards:
            return True
        return False

    @property
    def attack_succeed(self):
        return any(def_card is None for def_card in self.field.values())

    def finish_turn(self):
        assert not self.winner

        took_cards = False
        if self.attack_succeed and self.opponent_player.cards:
            print('there is some unbeaten card')
            # take all cards from the field if player couldn't defend
            self._take_all_field()
            took_cards = True
        elif self.deck and not self.opponent_player.cards:
            for key, value in self.field.items():
                if value is None:
                    self.current_player.take_card(key)
            self.field = {}
        else:
            # all cards are beaten, so just clearing the field
            self.field = {}

        # очередность взятия карт из колоды определяется индексом атакующего (можно сдвигать на 1, или нет)
        for p in rotate(self.players, self.attacker_index):
            p.take_cards_from_deck(self.deck)

        # is deck empty?
        if not self.deck:
            for p in self.players:
                if not p.cards:
                    self.winner = p.index
                    return self.GAME_OVER

        if took_cards:
            return self.TOOK_CARDS
        else:
            # turn is changed, if player has successfully defended
            self.attacker_index = self.opponent_player.index
            return self.NORMAL

    def _take_all_field(self):
        """
        Opponent takes all the cards from the field
        """
        cards = self.attacking_cards + self.defending_cards
        self.opponent_player.add_cards(cards)
        self.field = {}
