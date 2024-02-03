import unittest

from cryptography.fernet import Fernet

from adero.utilities import RabbitSecurity, RabbitSecurityException


class TestRabbitSecurity(unittest.TestCase):
    def test_initialize_with_valid_encryption_key(self):
        encryption_key = Fernet.generate_key()
        security = RabbitSecurity(encryption_key)
        self.assertEqual(security.encryption_key, encryption_key)

    def test_encrypt_message_with_valid_encryption_key(self):
        encryption_key = Fernet.generate_key()
        security = RabbitSecurity(encryption_key)
        message = b"This is a message"
        encrypted_message = security.encrypt_message(message)
        self.assertNotEqual(encrypted_message, message)

    def test_decipher_message_with_valid_encryption_key(self):
        encryption_key = Fernet.generate_key()
        security = RabbitSecurity(encryption_key)
        message = b"This is a message"
        encrypted_message = security.encrypt_message(message)
        decrypted_message = security.decipher_message(encrypted_message)
        self.assertEqual(decrypted_message, message)

    def test_initialize_with_invalid_encryption_key(self):
        encryption_key = 12345
        with self.assertRaises(RabbitSecurityException):
            RabbitSecurity(encryption_key)

    def test_encrypt_message_with_invalid_message(self):
        encryption_key = Fernet.generate_key()
        security = RabbitSecurity(encryption_key)
        message = "invalid_message"
        with self.assertRaises(RabbitSecurityException):
            security.encrypt_message(message)

    def test_decipher_message_with_invalid_message(self):
        encryption_key = Fernet.generate_key()
        security = RabbitSecurity(encryption_key)
        message = "invalid_message"  # Pass a non-bytes message
        with self.assertRaises(RabbitSecurityException):
            security.decipher_message(message)

    def test_encryption_key_given_as_string(self):
        encryption_key = Fernet.generate_key()
        security = RabbitSecurity(str(encryption_key))
        self.assertEqual(security.encryption_key, encryption_key)
