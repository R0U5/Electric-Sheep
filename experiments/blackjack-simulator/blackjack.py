#!/usr/bin/env python3
"""
Interactive Blackjack Simulator
Play hands of Blackjack against a dealer, with betting, splitting, and strategy analytics.
"""

import random
import sys

CLEAR = "\033[2J\033[H"
RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"


def card_str(cards):
    """Compact string representation of a list of cards."""
    return " ".join(str(c) for c in cards)


def rank(c):
    return c[0]


def soft_total(cards):
    """Hand total with aces as 11 where possible."""
    total = 0
    aces = 0
    for c in cards:
        r = c[0]
        if r in ("J", "Q", "K"):
            total += 10
        elif r == "A":
            aces += 1
            total += 11
        else:
            total += int(r)
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    return total


def is_blackjack(cards):
    return len(cards) == 2 and soft_total(cards) == 21


def build_shoe(n=6):
    """Build and shuffle an n-deck shoe."""
    shoe = []
    for _ in range(n):
        for suit in "HDSC":
            for rank_ in "AKQJT98765432":
                shoe.append(rank_ + suit)
    random.shuffle(shoe)
    return shoe


def draw_card(deck):
    return deck.pop()


class Table:
    def __init__(self, bankroll=1000):
        self.bankroll = bankroll
        self.hands_played = 0
        self.wins = 0
        self.losses = 0
        self.pushes = 0
        self.blackjacks = 0
        self.initial_bankroll = bankroll

    def record_win(self, is_bj=False):
        self.wins += 1
        if is_bj:
            self.blackjacks += 1

    def record_loss(self):
        self.losses += 1

    def record_push(self):
        self.pushes += 1

    def print_stats(self):
        net = self.bankroll - self.initial_bankroll
        sign = f"+{net}" if net >= 0 else str(net)
        print(f"\n{CYAN}{BOLD}═══ Session Stats ═══{RESET}")
        print(f"  Hands played : {self.hands_played}")
        print(f"  Wins        : {GREEN}{self.wins}{RESET}")
        print(f"  Losses     : {RED}{self.losses}{RESET}")
        print(f"  Pushes     : {YELLOW}{self.pushes}{RESET}")
        print(f"  Blackjacks : {MAGENTA}{self.blackjacks}{RESET}")
        print(f"  Net balance : {GREEN if net >= 0 else RED}{sign}{RESET}")
        print(f"  Bankroll    : ${self.bankroll}{RESET}")


def dealer_play(deck, dealer_cards):
    """Draw dealer cards until reaching 17+. Returns final total."""
    while soft_total(dealer_cards) < 17:
        dealer_cards.append(draw_card(deck))
        print(f"  {MAGENTA}Dealer draws: {card_str(dealer_cards)} → {soft_total(dealer_cards)}{RESET}")
    return soft_total(dealer_cards)


def resolve_hand(player_cards, dealer_final_total, bet, table, dealer_up):
    """Determine outcome of a single hand. Returns delta (can be 0)."""
    pv = soft_total(player_cards)
    dv = dealer_final_total

    if is_blackjack(player_cards) and not is_blackjack([dealer_up]):  # upcard only
        # True blackjack pays 3:2
        table.bankroll += int(bet * 1.5)
        table.record_win(is_bj=True)
        return f"BLACKJACK! ({pv})", int(bet * 1.5)

    if pv > 21:
        table.record_loss()
        return f"BUST ({pv})", -bet

    if dv > 21:
        table.record_win()
        return f"Dealer busts ({dv}) — YOU WIN", bet

    if dv > pv:
        table.record_loss()
        return f"Dealer wins ({dv} vs {pv})", -bet

    if dv < pv:
        table.record_win()
        return f"YOU WIN ({pv} vs {dv})", bet

    table.record_push()
    return f"PUSH ({pv} vs {dv})", 0


def player_action(deck, player_cards, table, bet, depth=0):
    """Handle hit/stand/double/split for one hand. Returns final player total."""
    total = soft_total(player_cards)
    doubled = False
    label = "Hand" if depth > 0 else "Your cards"

    while True:
        total = soft_total(player_cards)
        if total > 21:
            return total

        opts = f"[{YELLOW}H{RESET}]it"
        if total < 21:
            opts += f"  [{YELLOW}S{RESET}]tand"
        if total >= 9 and not doubled and table.bankroll >= bet:
            opts += f"  [{YELLOW}D{RESET}]ouble"
        if (len(player_cards) == 2 and player_cards[0][0] == player_cards[1][0]
                and depth == 0 and table.bankroll >= bet):
            opts += f"  [{YELLOW}P{RESET}]split"

        print(f"\n  {label} : {GREEN}{card_str(player_cards)}{RESET} → {total}  {opts}")
        action = input(f"  {CYAN}→ {RESET}").strip().lower()

        if action == "s":
            return total
        elif action == "d":
            if table.bankroll < bet:
                print("  Can't afford to double.")
                continue
            table.bankroll -= bet
            bet *= 2
            doubled = True
            player_cards.append(draw_card(deck))
            print(f"  {MAGENTA}Doubled! Final: {card_str(player_cards)} → {soft_total(player_cards)}{RESET}")
            return soft_total(player_cards)
        elif action == "p" and depth == 0:
            if table.bankroll < bet:
                print("  Can't afford to split.")
                continue
            table.bankroll -= bet
            c1, c2 = player_cards[0], player_cards[1]
            h1 = [c1, draw_card(deck)]
            h2 = [c2, draw_card(deck)]
            print(f"\n  {GREEN}Split!{RESET}  Hand 1: {card_str(h1)}  Hand 2: {card_str(h2)}")
            pv1 = player_action(deck, h1, table, bet, depth=1)
            pv2 = player_action(deck, h2, table, bet, depth=1)
            return pv1, pv2  # tuple signals split
        elif action == "h":
            player_cards.append(draw_card(deck))
        else:
            print(f"  Unknown action: '{action}'")


def play_one_hand(table, deck, shoe):
    """Play a single hand. Returns False if player quits."""
    if len(deck) < 20:
        print(f"{YELLOW}♠ Shoe low — reshuffling...{RESET}")
        random.shuffle(shoe)
        deck.clear()
        deck.extend(shoe)

    # ─ Bet ─
    bet = 0
    while True:
        raw = input(f"\n{CYAN}Bet (${table.bankroll} available) [Enter=$10, 0=quit]: {RESET}").strip()
        if raw == "0":
            return False
        bet = int(raw) if raw else 10
        if bet < 1:
            print("  Minimum bet: $1")
            continue
        if bet > table.bankroll:
            print(f"  You only have ${table.bankroll}")
            continue
        break

    table.bankroll -= bet
    table.hands_played += 1

    # ─ Deal ─
    player_cards = [draw_card(deck), draw_card(deck)]
    dealer_up = draw_card(deck)
    dealer_down = draw_card(deck)
    dealer_cards = [dealer_up, dealer_down]

    print(f"\n  Your cards  : {GREEN}{card_str(player_cards)}{RESET} → {soft_total(player_cards)}")
    print(f"  Dealer shows: {YELLOW}{card_str([dealer_up])}{RESET}")

    # ─ Insurance ─
    insurance = 0
    if dealer_up[0] == "A" and table.bankroll >= bet // 2:
        raw = input(f"  {YELLOW}Insurance? [{bet//2}] [y/N]: {RESET}").strip().lower()
        if raw == "y":
            insurance = bet // 2
            table.bankroll -= insurance
            print(f"  Insurance placed: ${insurance}")

    # ─ Check dealer blackjack ─
    if is_blackjack(dealer_cards):
        print(f"  {RED}Dealer has Blackjack!{RESET}  Hole card: {card_str([dealer_down])}")
        if insurance > 0:
            payout = insurance * 2
            table.bankroll += payout
            print(f"  Insurance pays 2:1 → +${payout}")
        table.losses += 1
        table.print_stats()
        return True

    if insurance > 0:
        print(f"  Insurance loses.")

    # ─ Player action ─
    result = player_action(deck, player_cards, table, bet)

    if isinstance(result, tuple):
        # Split — resolve each hand against same dealer total
        pv1, pv2 = result
        print(f"\n  {CYAN}Dealer hole card: {card_str([dealer_down])} → {soft_total([dealer_up, dealer_down])}{RESET}")
        dealer_final = dealer_play(deck, [dealer_up, dealer_down])
        for i, pv in enumerate([pv1, pv2], 1):
            msg, delta = resolve_hand(
                [dealer_up, dealer_down], dealer_final, bet // 2, table, dealer_up[0]
            )
            print(f"\n  Hand {i}: {GREEN if delta >= 0 else RED}{msg}{RESET}  "
                  f"{'+' if delta >= 0 else ''}{delta}")
        table.print_stats()
        return True

    player_total = result

    if player_total > 21:
        print(f"\n  {RED}BUST — you lose ${bet}{RESET}")
        table.losses += 1
        table.print_stats()
        return True

    # ─ Dealer action ─
    print(f"\n  {CYAN}Dealer hole card: {card_str([dealer_down])} → {soft_total([dealer_up, dealer_down])}{RESET}")
    dealer_final = dealer_play(deck, [dealer_up, dealer_down])

    # ─ Resolve ─
    msg, delta = resolve_hand(player_cards, dealer_final, bet, table, dealer_up)
    print(f"\n  {GREEN if delta >= 0 else RED}{msg}{RESET}  {'+' if delta >= 0 else ''}{delta}")
    table.print_stats()
    return True


def main():
    print(f"{CLEAR}")
    print(f"{BOLD}{CYAN}")
    print("  ╔══════════════════════════════════════╗")
    print("  ║       ♠ BLACKJACK SIMULATOR ♠        ║")
    print("  ╚══════════════════════════════════════╝")
    print(f"{RESET}")
    print("  Commands: H=hit  S=stand  D=double  P=split")
    print("  [Enter] deal next hand  [0] cash out  [S] stats")
    print()

    shoe = build_shoe(6)
    deck = shoe.copy()

    table = Table(bankroll=1000)

    while True:
        if table.bankroll < 1:
            print(f"\n{RED}You're broke! Game over.{RESET}")
            table.print_stats()
            break

        cmd = input(f"\n{CYAN}[Enter] Play hand  [S] stats  [0] quit: {RESET}").strip()
        if cmd == "0":
            net = table.bankroll - table.initial_bankroll
            print(f"\n{CYAN}Final bankroll: ${table.bankroll} ({'+' if net >= 0 else ''}{net}){RESET}")
            table.print_stats()
            break
        if cmd == "s":
            table.print_stats()
            continue

        if not play_one_hand(table, deck, shoe):
            break

    print(f"\n{GREEN}Thanks for playing!{RESET}")


if __name__ == "__main__":
    main()
