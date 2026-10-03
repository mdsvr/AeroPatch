import contextlib

from app.giftcards import total_outstanding, transfer


def _transfer(ledger, sender, recipient, amount):
    with contextlib.suppress(Exception):  # refusing the amount is fine; booking it is not
        transfer(ledger, sender, recipient, amount)


def test_negative_amount_cannot_pull_money_from_the_other_card():
    ledger = {"mine": 500, "victim": 20_000}
    _transfer(ledger, "mine", "victim", "-15000")
    assert ledger == {"mine": 500, "victim": 20_000}


def test_no_balance_goes_below_zero():
    ledger = {"mine": 0, "victim": 1_000}
    _transfer(ledger, "mine", "victim", "-40000")
    assert min(ledger.values()) >= 0


def test_recipient_cannot_exceed_the_card_limit():
    ledger = {"mine": 40_000, "friend": 30_000}
    _transfer(ledger, "mine", "friend", "30000")
    assert ledger["friend"] <= 50_000
    assert total_outstanding(ledger) == 70_000
