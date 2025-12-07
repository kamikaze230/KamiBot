# blackjack.py
import random
from typing import List, Optional

SUITS = ["♠", "♥", "♦", "♣"]
RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]

def make_deck(num_decks: int = 1) -> List[str]:
    return [f"{rank}{suit}" for _ in range(num_decks) for suit in SUITS for rank in RANKS]

def card_value(rank: str) -> int:
    if rank in ("J", "Q", "K"):
        return 10
    if rank == "A":
        return 11
    return int(rank)

def hand_value(cards: List[str]) -> int:
    total, aces = 0, 0
    for card in cards:
        rank = card[:-1]
        total += card_value(rank)
        if rank == "A":
            aces += 1
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total

def pretty_cards(cards: List[str]) -> str:
    return " ".join(cards)

class BlackjackGame:
    def __init__(self, player_id: int, bet: int = 10, num_decks: int = 1):
        self.player_id = player_id
        self.bet = bet
        self.deck = make_deck(num_decks)
        random.shuffle(self.deck)
        self.player_cards: List[str] = []
        self.dealer_cards: List[str] = []
        self.finished = False
        self.result: Optional[str] = None
        self.payout = 0

        # deal initial
        self.player_cards.append(self.draw())
        self.dealer_cards.append(self.draw())
        self.player_cards.append(self.draw())
        self.dealer_cards.append(self.draw())

        self._check_initial_blackjack()

    def draw(self) -> str:
        if not self.deck:
            self.deck = make_deck(1)
            random.shuffle(self.deck)
        return self.deck.pop()

    def player_value(self) -> int:
        return hand_value(self.player_cards)

    def dealer_value(self) -> int:
        return hand_value(self.dealer_cards)

    def _check_initial_blackjack(self):
        pv, dv = self.player_value(), self.dealer_value()
        if pv == 21 or dv == 21:
            if pv == 21 and dv == 21:
                self.result, self.payout = "push", 0
            elif pv == 21:
                self.result, self.payout = "blackjack", int(self.bet * 1.5)
            else:
                self.result, self.payout = "lose", -self.bet
            self.finished = True

    def player_hit(self):
        if self.finished:
            return
        self.player_cards.append(self.draw())
        if self.player_value() > 21:
            self.result, self.payout, self.finished = "lose", -self.bet, True

    def player_double(self):
        if self.finished:
            return
        self.bet *= 2
        self.player_cards.append(self.draw())
        if self.player_value() > 21:
            self.result, self.payout, self.finished = "lose", -self.bet, True
        else:
            self._dealer_play_and_resolve()

    def player_stand(self):
        if not self.finished:
            self._dealer_play_and_resolve()

    def _dealer_play_and_resolve(self):
        while self.dealer_value() < 17:
            self.dealer_cards.append(self.draw())

        pv, dv = self.player_value(), self.dealer_value()
        if dv > 21:
            self.result, self.payout = "win", self.bet
        elif dv > pv:
            self.result, self.payout = "lose", -self.bet
        elif dv < pv:
            self.result, self.payout = "win", self.bet
        else:
            self.result, self.payout = "push", 0
        self.finished = True

def result_message(game: BlackjackGame) -> str:
    if game.result == "win":
        return f"You win! Payout: +{game.payout}"
    if game.result == "lose":
        return f"You lose. Payout: {game.payout}"
    if game.result == "push":
        return "Push. Your bet is returned."
    if game.result == "blackjack":
        return f"Blackjack! Payout: +{game.payout}"
    if game.result == "surrender":
        return f"Surrendered. Payout: {game.payout}"
    return "Game ended."
