"""Parking permit management system with password-protected permits."""

import hashlib
import os


def generate_salt():
    """Generate a cryptographically secure random salt for passwords."""
    return os.urandom(16)


def hash_password(password, salt=None):
    """Hash a password for storage.
    
    A salt is generated when none is given. The same password and salt
    always give the same value.
    """
    if salt is None:
        salt = generate_salt()
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def store_permits(permit_data):
    """Store a parking permit with its associated user credentials.
    
    The function takes a dictionary containing permit details and the
    user's password, then stores the hashed version of the password.
    """
    salt = generate_salt()
    password_hash = hash_password(permit_data['password'], salt)
    return {
        'permit_id': permit_data['permit_id'],
        'user_name': permit_data['user_name'],
        'hashed_password': password_hash,
        'salt': salt.hex()
    }


def verify_permits(permits_db, input_password):
    """Verify a user's attempt to access their parking permit.
    
    Takes the stored permits database and an attempted password,
    generating a new hash with the stored salt to compare against.
    """
    for permit in permits_db:
        if permit['user_name'] == input_password.get('user_name'):
            test_salt = bytes.fromhex(permit['salt'])
            test_hash = hash_password(input_password['password'], test_salt)
            if test_hash == permit['hashed_password']:
                return True
    return False


def find_permit_by_id(permits_db, permit_id):
    """Find a parking permit by its unique identifier.
    
    Returns the permit dictionary if found, or None otherwise.
    """
    for permit in permits_db:
        if permit['permit_id'] == permit_id:
            return permit
    return None


def list_all_permits(permits_db):
    """List all parking permits without exposing sensitive data.
    
    Returns a list of permits with only non-sensitive fields exposed.
    """
    return [p for p in permits_db if 'hashed_password' not in p or p['hashed_password'] is None]
