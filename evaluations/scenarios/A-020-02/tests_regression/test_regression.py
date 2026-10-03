import pytest

from app.giftcards import LedgerError, open_card, spend, top_up, total_outstanding, transfer


@pytest.fixture
def ledger():
    cards = {}
    open_card(cards, "A")
    open_card(cards, "B")
    top_up(cards, "A", "10000")
    return cards


def test_transfer_moves_cents_between_cards(ledger):
    assert transfer(ledger, "A", "B", "2500") == 7_500
    assert transfer(ledger, "A", "B", 500) == 7_000
    assert ledger == {"A": 7_000, "B": 3_000}
    assert transfer(ledger, "B", "A", "3000") == 0


def test_transfer_up_to_the_limits(ledger):
    top_up(ledger, "B", "20000")
    top_up(ledger, "B", "20000")
    assert transfer(ledger, "A", "B", "10000") == 0
    assert ledger == {"A": 0, "B": 50_000}


def test_transfer_refusals_change_nothing(ledger):
    with pytest.raises(LedgerError):
        transfer(ledger, "A", "B", "10001")
    with pytest.raises(LedgerError):
        transfer(ledger, "A", "A", "100")
    with pytest.raises(LedgerError):
        transfer(ledger, "A", "nobody", "100")
    for bad in ("ten", "", "12.5", None):
        with pytest.raises((ValueError, TypeError)):
            transfer(ledger, "A", "B", bad)
    assert ledger == {"A": 10_000, "B": 0}


def test_top_up_and_open(ledger):
    assert top_up(ledger, "B", "20000") == 20_000
    for bad in ("0", "-100", "20001"):
        with pytest.raises(LedgerError):
            top_up(ledger, "B", bad)
    with pytest.raises(LedgerError):
        open_card(ledger, "A")
    with pytest.raises(LedgerError):
        top_up(ledger, "nobody", "100")


def test_spend_and_total(ledger):
    assert spend(ledger, "A", 2_500) == 7_500
    with pytest.raises(LedgerError):
        spend(ledger, "A", 7_501)
    with pytest.raises(LedgerError):
        spend(ledger, "A", 0)
    assert total_outstanding(ledger) == 7_500
