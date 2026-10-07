import pytest
from app.parking_permits import hash_password, store_permits, verify_permits, find_permit_by_id


def test_store_and_verify_simple_case():
    """Test storing and verifying a simple permit case."""
    permits_db = [
        store_permits({'permit_id': 'p1', 'user_name': 'alice', 'password': 'password123'})
    ]
    
    assert verify_permits(permits_db, {'user_name': 'alice', 'password': 'password123'}) is True
    assert verify_permits(permits_db, {'user_name': 'alice', 'password': 'wrongpassword'}) is False

def test_find_permit_returns_none_when_not_found():
    """Test that finding a non-existent permit returns None."""
    permits_db = [
        store_permits({'permit_id': 'p1', 'user_name': 'alice', 'password': 'secret'})
    ]
    
    result = find_permit_by_id(permits_db, 'nonexistent')
    assert result is None



def test_store_permits_generates_unique_salt():
    """Test that storing permits generates a unique salt each time."""
    perm1 = store_permits({'permit_id': 'p1', 'user_name': 'alice', 'password': 'secret'})
    perm2 = store_permits({'permit_id': 'p2', 'user_name': 'bob', 'password': 'secret'})
    
    assert perm1['salt'] != perm2['salt']
