import pytest

from app import store


@pytest.fixture
def conn():
    c = store.connect()
    store.add_product(c, "kettle", "kitchen", "acme", 2499)
    store.add_product(c, "toaster", "kitchen", "brightco", 3999)
    store.add_product(c, "lamp", "lighting", "acme", 1599)
    store.add_product(c, "bulb", "lighting", "brightco", 299)
    return c


def names(rows):
    return [row[1] for row in rows]


def test_filter_by_category_sorted_by_name(conn):
    assert names(store.search_products(conn, category="kitchen")) == ["kettle", "toaster"]


def test_criteria_are_combined_with_and(conn):
    assert names(store.search_products(conn, category="lighting", supplier="acme")) == ["lamp"]


def test_no_criteria_returns_everything(conn):
    assert names(store.search_products(conn)) == ["bulb", "kettle", "lamp", "toaster"]


def test_none_value_is_ignored(conn):
    assert names(store.search_products(conn, category="kitchen", supplier=None)) == ["kettle", "toaster"]


def test_no_match_is_empty(conn):
    assert store.search_products(conn, name="sofa") == []


def test_rows_have_all_columns(conn):
    assert store.search_products(conn, name="lamp") == [(3, "lamp", "lighting", "acme", 1599)]


def test_unknown_filter_column_is_rejected(conn):
    with pytest.raises(ValueError):
        store.search_products(conn, price_cents="0")


def test_sort_by_price_and_newest(conn):
    assert names(store.search_products(conn, sort="price")) == ["bulb", "lamp", "kettle", "toaster"]
    assert names(store.search_products(conn, sort="newest")) == ["bulb", "lamp", "toaster", "kettle"]


def test_unknown_sort_is_rejected(conn):
    with pytest.raises(ValueError):
        store.search_products(conn, sort="rating")


def test_limit_caps_results(conn):
    assert names(store.search_products(conn, limit=2)) == ["bulb", "kettle"]
    assert len(store.search_products(conn, limit=0)) == 1


def test_other_catalogue_operations_still_work(conn):
    assert store.update_price(conn, 1, 1999) and store.get_product(conn, 1)[4] == 1999
    assert store.count_by_category(conn) == {"kitchen": 2, "lighting": 2}
    assert store.price_range(conn, "lighting") == (299, 1599)
    assert store.delete_product(conn, 4) and store.price_range(conn, "lighting") == (1599, 1599)
