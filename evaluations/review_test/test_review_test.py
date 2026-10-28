"""Checks for the review-test kit: the page serves four cards and never leaks the answer key; scoring rules hold."""

from app import create_app
from score import score

ROW = {"participant_id": "p", "card1": "apply", "card2": "reject", "risk_restated": "yes", "confidence": "3"}


def test_page_shows_four_cards_and_no_key():
    client = create_app().test_client()
    body = client.get("/").get_data(as_text=True)
    assert body.count('<section class="card"') == 4
    assert "expected" not in body and "answer_key" not in body


def test_pass_needs_five_of_six_on_each_criterion():
    rows = [ROW] * 5 + [dict(ROW, card2="apply", card1="reject", risk_restated="no")]
    result = score(rows)
    assert result["n"] == 6 and result["passes"]
    assert score(rows[:4] + [dict(ROW, card2="apply")] * 2)["passes"] is False


def test_confident_wrong_is_listed():
    result = score([dict(ROW, participant_id="x", card2="apply", confidence="5")] + [ROW] * 5)
    assert result["confident_wrong"] == ["x"]
    assert result["passes"] is True


if __name__ == "__main__":
    test_page_shows_four_cards_and_no_key()
    test_pass_needs_five_of_six_on_each_criterion()
    test_confident_wrong_is_listed()
    print("ok")
