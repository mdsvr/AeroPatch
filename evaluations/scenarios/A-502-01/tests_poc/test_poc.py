import pickle

import pytest

from app.prefs import load_prefs


def test_pickle_encoded_input_is_rejected():
    with pytest.raises(ValueError):
        load_prefs(pickle.dumps({"theme": "dark"}))
