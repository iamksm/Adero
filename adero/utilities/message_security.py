import ast

from cryptography.fernet import Fernet


class RabbitSecurityException(Exception):
    ...


class RabbitSecurity:
    def __init__(self, encryption_key) -> None:
        if isinstance(encryption_key, str):
            encryption_key = ast.literal_eval(encryption_key)

        if not isinstance(encryption_key, bytes):
            raise RabbitSecurityException("Encryption key must be in bytes")

        self.encryption_key = encryption_key
        self.cipher_suite = Fernet(self.encryption_key)

    def encrypt_message(self, message: bytes) -> bytes:
        if not isinstance(message, bytes):
            raise RabbitSecurityException("Message must be in bytes")

        return self.cipher_suite.encrypt(message)

    def decipher_message(self, message: bytes) -> bytes:
        if not isinstance(message, bytes):
            raise RabbitSecurityException("Message must be in bytes")

        return self.cipher_suite.decrypt(message)
