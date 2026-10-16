from app import db


def test_lookup():
    conn = db.connect()
    db.add_user(conn, "alice")
    assert db.find_user(conn, "alice")
    assert db.find_user(conn, "x' OR '1'='1") == []
