"""Gift-card balances for the shop. A ledger maps a card number to its balance in cents."""

MAX_BALANCE_CENTS = 500_00
MAX_TOP_UP_CENTS = 200_00


class LedgerError(ValueError):
    """Raised when a gift-card operation is refused."""


def open_card(ledger, card):
    """Register a new card with a zero balance."""
    if card in ledger:
        raise LedgerError("card already exists")
    ledger[card] = 0


def top_up(ledger, card, amount):
    """Add `amount` cents (text from the top-up form) to a card and return its new balance."""
    if card not in ledger:
        raise LedgerError("unknown card")
    cents = int(amount)
    if not 0 < cents <= MAX_TOP_UP_CENTS:
        raise LedgerError("top-up amount is out of range")
    if ledger[card] + cents > MAX_BALANCE_CENTS:
        raise LedgerError("card balance limit reached")
    ledger[card] += cents
    return ledger[card]


def transfer(ledger, sender, recipient, amount):
    """Move `amount` cents from one card to another and return the sender's new balance.

    `amount` is the text of the amount box on the "send a gift" page. Balances never go below
    zero, and a card never holds more than MAX_BALANCE_CENTS.
    """
    if sender not in ledger or recipient not in ledger:
        raise LedgerError("unknown card")
    if sender == recipient:
        raise LedgerError("cannot send to the same card")
    cents = int(amount)
    remaining = ledger[sender] - cents
    if remaining < 0:
        raise LedgerError("not enough balance")
    ledger[sender] = remaining
    ledger[recipient] += cents
    return remaining


def spend(ledger, card, price_cents):
    """Pay `price_cents` from a card at checkout; return what is left on it."""
    if card not in ledger:
        raise LedgerError("unknown card")
    if price_cents <= 0 or price_cents > ledger[card]:
        raise LedgerError("card cannot cover this price")
    ledger[card] -= price_cents
    return ledger[card]


def total_outstanding(ledger):
    """Sum of all card balances: what the shop owes its card holders."""
    return sum(ledger.values())
