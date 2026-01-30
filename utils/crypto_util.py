from cryptography.fernet import Fernet
from core.config import settings

_cipher_suite = None


def _get_cipher():
    global _cipher_suite
    if _cipher_suite is None:
        _cipher_suite = Fernet(settings.ENCRYPTION_KEY)
    return _cipher_suite


def encrypt_data(data: str) -> bytes:
    return _get_cipher().encrypt(data.encode())


def decrypt_data(data: bytes) -> str:
    return _get_cipher().decrypt(data).decode()
