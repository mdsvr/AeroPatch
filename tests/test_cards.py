"""rules/cards.json: the plain-language cards `aeropatch check` shows (doc 17 part 3, sections 2-3)."""

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CARDS = json.loads((ROOT / "rules" / "cards.json").read_text(encoding="utf-8"))
RULES_YML = (ROOT / "rules" / "aeropatch-python.yml").read_text(encoding="utf-8")
# One chunk per `- id:` line: the id, then its body up to the next rule.
PROJECT_CWE = {
    chunk.split()[0]: re.search(r'cwe: "(CWE-\d+)', chunk)[1]
    for chunk in re.split(r"^\s*- id:\s*", RULES_YML, flags=re.MULTILINE)[1:]
}
KEYS = {"headline", "what_could_happen", "when_it_matters", "the_change", "try_yourself", "cwe"}
TEXT_FIELDS = ["what_could_happen", "when_it_matters", "the_change"]
STATUS_WORDS = re.compile(r"\b(secure|safe|fixed|verified|guaranteed)\b", re.IGNORECASE)
SECRET_HEDGE = "If this is a real password or key"
CREDENTIAL_CARDS = ["aeropatch.python.hardcoded-credential", "B105", "B106", "B107"]
ALL_CARDS = {"generic": CARDS["generic"], "secret": CARDS["secret"], **CARDS["rules"]}


@pytest.fixture(scope="module")
def bandit_ids():
    out = subprocess.run([sys.executable, "-m", "bandit", "--help"],
                         capture_output=True, text=True, check=True).stdout
    return set(re.findall(r"^\s+(B\d{3})\s", out, re.MULTILINE))


def strings(card):
    return [card[f] for f in ("headline", *TEXT_FIELDS)] + card["try_yourself"]


def test_top_level_shape():
    assert set(CARDS) == {"version", "generic", "secret", "rules"}
    assert CARDS["version"] == 1


@pytest.mark.parametrize("name", ALL_CARDS)
def test_card_shape(name):
    card = ALL_CARDS[name]
    assert set(card) == KEYS
    assert all(isinstance(s, str) and s.strip() for s in strings(card))
    assert isinstance(card["try_yourself"], list) and 2 <= len(card["try_yourself"]) <= 3
    if name in ("generic", "secret"):
        assert card["cwe"] == ""
    else:
        assert re.fullmatch(r"CWE-\d+", card["cwe"])


@pytest.mark.parametrize("name", ALL_CARDS)
def test_word_limits(name):
    card = ALL_CARDS[name]
    assert len(card["headline"].split()) <= 14
    for field in TEXT_FIELDS:
        assert len(card[field].split()) <= 45, field
    # ponytail: the whole list within 45 words, which also holds 45 per item
    assert sum(len(s.split()) for s in card["try_yourself"]) <= 45


@pytest.mark.parametrize("name", ALL_CARDS)
def test_no_status_words(name):
    hits = [m[0] for s in strings(ALL_CARDS[name]) for m in STATUS_WORDS.finditer(s)]
    assert not hits


def test_every_project_rule_has_a_card_with_its_cwe():
    assert len(PROJECT_CWE) >= 22  # a broken regex must not pass with nothing parsed
    for rule_id, cwe in PROJECT_CWE.items():
        assert CARDS["rules"][rule_id]["cwe"] == cwe, rule_id


def test_every_key_is_a_real_rule_id(bandit_ids):
    assert len(bandit_ids) > 50
    for key in CARDS["rules"]:
        if key.startswith("aeropatch."):
            assert key in PROJECT_CWE, key
        else:
            assert re.fullmatch(r"B\d{3}", key) and key in bandit_ids, key


def test_secret_card_hedges_and_never_asks_for_the_value():
    for name in ["secret", *CREDENTIAL_CARDS]:
        card = ALL_CARDS[name]
        assert card["headline"].startswith(SECRET_HEDGE), name
        assert "environment variable" in card["the_change"], name
        assert not any("paste" in s.lower() for s in strings(card)), name
