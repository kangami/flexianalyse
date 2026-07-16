"""
Simple encryption service using Fernet (symmetric encryption).
Used to encrypt sensitive connector credentials before storing in DB.
"""
import os
from cryptography.fernet import Fernet


class EncryptionService:
    def __init__(self):
        key = os.getenv("ENCRYPTION_KEY")
        if not key:
            raise ValueError(
                "ENCRYPTION_KEY environment variable is required. "
                "Generate one with: from cryptography.fernet import Fernet; Fernet.generate_key()"
            )
        self._fernet = Fernet(key.encode())

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string and return it as a string."""
        if plaintext is None:
            return None
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a string and return the original plaintext."""
        if ciphertext is None:
            return None
        return self._fernet.decrypt(ciphertext.encode()).decode()


_encryption_service: EncryptionService | None = None


def get_encryption_service() -> EncryptionService:
    """Lazy singleton accessor.

    Building the service at import time makes a missing ENCRYPTION_KEY break the
    whole app import — including `flask db upgrade`, which never encrypts anything.
    Callers resolve it here so the failure surfaces on the request that needs it.
    """
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service
