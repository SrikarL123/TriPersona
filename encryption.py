"""
Application-level encryption for TriPersona chat data.

Neon stores only Fernet ciphertext for chat titles and message content.
The encryption key is kept in the application's environment, not in Neon.
"""

import os
from dotenv import load_dotenv
from cryptography.fernet import Fernet, InvalidToken

load_dotenv()

PREFIX = "v1:"
_cipher = None


def _get_cipher():
    global _cipher

    if _cipher is None:
        key = os.getenv("CHAT_ENCRYPTION_KEY")
        if not key:
            raise RuntimeError(
                "CHAT_ENCRYPTION_KEY is not set in .env. "
                "Generate one with: python -c "
                "\"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )

        try:
            _cipher = Fernet(key.encode("utf-8"))
        except Exception as exc:
            raise RuntimeError(
                "CHAT_ENCRYPTION_KEY is invalid. Generate a new Fernet key."
            ) from exc

    return _cipher


def is_encrypted(value):
    return isinstance(value, str) and value.startswith(PREFIX)


def encrypt_text(value):
    if value is None:
        return None

    value = str(value)

    if is_encrypted(value):
        return value

    token = _get_cipher().encrypt(value.encode("utf-8")).decode("utf-8")
    return PREFIX + token


def decrypt_text(value):
    if value is None:
        return None

    value = str(value)

    # Old rows may be plaintext until the startup migration runs.
    if not is_encrypted(value):
        return value

    token = value[len(PREFIX):]

    try:
        return _get_cipher().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise RuntimeError(
            "Could not decrypt chat data. Check that CHAT_ENCRYPTION_KEY "
            "is the same key used when the chats were encrypted."
        ) from exc
