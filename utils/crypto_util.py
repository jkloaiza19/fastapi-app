from cryptography.fernet import Fernet
from core.config import settings

cipher_suite = Fernet(settings.ENCRYPTION_KEY)


def encrypt_data(data: str) -> bytes:
    return cipher_suite.encrypt(data.encode())


def decrypt_data(data: bytes) -> str:
    return cipher_suite.decrypt(data).decode()
