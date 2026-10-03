import random

from app.reset import ResetCodes


def test_code_cannot_be_reproduced_from_the_generator_state():
    random.seed(20261003)
    issued = ResetCodes().issue(7)
    random.seed(20261003)  # an attacker who learns or guesses the seed replays the generator
    assert ResetCodes().issue(7) != issued


def test_sequence_of_codes_is_not_determined_by_the_seed():
    random.seed(1)
    codes = ResetCodes()
    first = [codes.issue(user_id) for user_id in range(5)]
    random.seed(1)
    codes = ResetCodes()
    assert [codes.issue(user_id) for user_id in range(5)] != first
