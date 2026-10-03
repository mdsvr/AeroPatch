import pytest

from app.signup import (
    clean_signup,
    is_valid_full_name,
    is_valid_postcode,
    is_valid_username,
    normalize_phone,
    validate_signup,
)

FORM = {"username": "ada_l", "full_name": "Ada Lovelace", "postcode": "SW1A 1AA", "phone": "+44 20 7946 0000"}


@pytest.mark.parametrize("name", [
    "Ada", "Ada Lovelace", "Mary Jane Watson", "de la Cruz", "Ada   Lovelace",
    "Maria de las Mercedes Fernandez de Cordoba y Alvarez de Toledo",  # 62 characters: long names are valid
])
def test_names_of_letters_and_spaces_are_valid(name):
    assert is_valid_full_name(name) is True


@pytest.mark.parametrize("name", ["", " ", "Ada1", "4da Lovelace", "Ada_Lovelace", "<Ada>", "Ada; DROP"])
def test_names_with_other_characters_are_invalid(name):
    assert is_valid_full_name(name) is False


def test_valid_form_has_no_errors():
    assert validate_signup(FORM) == {}


def test_each_bad_field_is_reported():
    errors = validate_signup({"username": "Admin!", "full_name": "Ada 2", "postcode": "12345", "phone": "call me"})
    assert sorted(errors) == ["full_name", "phone", "postcode", "username"]
    assert validate_signup({**FORM, "full_name": ""}) == {"full_name": "required"}
    assert validate_signup({**FORM, "full_name": "A" * 201}) == {"full_name": "too long"}
    assert validate_signup({**FORM, "username": "root"}).keys() == {"username"}


def test_clean_signup_tidies_the_values():
    assert clean_signup({**FORM, "full_name": "Ada   Lovelace"}) == {
        "username": "ada_l", "full_name": "Ada Lovelace", "postcode": "SW1A 1AA", "phone": "+442079460000"}
    with pytest.raises(ValueError):
        clean_signup({**FORM, "postcode": "nope"})


def test_other_validators():
    assert is_valid_username("ada_l") and not is_valid_username("ad") and not is_valid_username("admin")
    assert is_valid_postcode("M1 1AE") and is_valid_postcode("SW1A1AA") and not is_valid_postcode("sw1a 1aa")
    assert normalize_phone("(020) 7946-0000") == "02079460000" and normalize_phone("12") is None
