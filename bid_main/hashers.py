"""
Password hasher that performs the same operations as Flask-Security.
"""

import base64
import hashlib
import hmac

from django.contrib.auth.hashers import BCryptPasswordHasher, mask_hash

_password_salt = b'/2aX16zPnnIgfMwkOjGX4S'


def get_hmac(password: str) -> str:
    h = hmac.new(_password_salt, password.encode('utf-8'), hashlib.sha512)
    return base64.b64encode(h.digest()).decode('ascii')


class BlenderIdPasswordHasher(BCryptPasswordHasher):
    algorithm = 'blenderid'

    def encode(self, password: str, salt: bytes):
        hashed_password = get_hmac(password)
        return super().encode(hashed_password, salt)
