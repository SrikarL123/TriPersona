import os
import psycopg
from dotenv import load_dotenv
from encryption import encrypt_text, decrypt_text, is_encrypted

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set in .env")
    return psycopg.connect(DATABASE_URL)


def encrypt_existing_chat_data():
    """Encrypt old plaintext chat titles/messages once."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, title FROM chats WHERE title IS NOT NULL")
            for chat_id, title in cur.fetchall():
                if title and not is_encrypted(title):
                    cur.execute(
                        "UPDATE chats SET title = %s WHERE id = %s",
                        (encrypt_text(title), chat_id)
                    )

            cur.execute("SELECT id, content FROM messages")
            for message_id, content in cur.fetchall():
                if content and not is_encrypted(content):
                    cur.execute(
                        "UPDATE messages SET content = %s WHERE id = %s",
                        (encrypt_text(content), message_id)
                    )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def create_tables():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMPTZ
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS chats (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    title TEXT,
                    personality VARCHAR(50),
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    client_chat_id TEXT UNIQUE
                )
            """)

            cur.execute("""
                ALTER TABLE chats
                ADD COLUMN IF NOT EXISTS client_chat_id TEXT
            """)

            cur.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_chats_client_chat_id
                ON chats(client_chat_id)
                WHERE client_chat_id IS NOT NULL
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id SERIAL PRIMARY KEY,
                    chat_id INTEGER NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
                    role VARCHAR(20) NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_chats_user_updated
                ON chats(user_id, updated_at DESC)
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_chat_id_id
                ON messages(chat_id, id)
            """)

        conn.commit()

        # Existing chats are migrated from plaintext to ciphertext.
        encrypt_existing_chat_data()

        print("DATABASE TABLES CREATED SUCCESSFULLY")
        print("CHAT DATA ENCRYPTION ENABLED")
    finally:
        conn.close()


def get_or_create_chat(user_id, client_chat_id, title="New Chat", personality="normal"):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, user_id, title, personality
                   FROM chats WHERE client_chat_id = %s""",
                (str(client_chat_id),)
            )
            row = cur.fetchone()

            if row:
                if row[1] != user_id:
                    raise PermissionError("Chat does not belong to this user.")
                return {
                    "id": row[0],
                    "user_id": row[1],
                    "title": decrypt_text(row[2]) if row[2] else "New Chat",
                    "personality": row[3]
                }

            cur.execute(
                """INSERT INTO chats (user_id, title, personality, client_chat_id)
                   VALUES (%s, %s, %s, %s)
                   RETURNING id, user_id, title, personality""",
                (user_id, encrypt_text(title), personality, str(client_chat_id))
            )
            row = cur.fetchone()

        conn.commit()

        return {
            "id": row[0],
            "user_id": row[1],
            "title": decrypt_text(row[2]) if row[2] else "New Chat",
            "personality": row[3]
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def save_message(user_id, client_chat_id, role, content, title=None, personality="normal"):
    chat = get_or_create_chat(
        user_id,
        client_chat_id,
        title=title or "New Chat",
        personality=personality
    )

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO messages (chat_id, role, content)
                   VALUES (%s, %s, %s)""",
                (chat["id"], role, encrypt_text(content))
            )

            if title and title != "New Chat":
                cur.execute(
                    """UPDATE chats
                       SET title = %s, personality = %s, updated_at = CURRENT_TIMESTAMP
                       WHERE id = %s AND user_id = %s""",
                    (encrypt_text(title), personality, chat["id"], user_id)
                )
            else:
                cur.execute(
                    """UPDATE chats
                       SET updated_at = CURRENT_TIMESTAMP
                       WHERE id = %s AND user_id = %s""",
                    (chat["id"], user_id)
                )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def save_exchange(user_id, client_chat_id, user_message, assistant_message,
                  title=None, personality="normal"):
    """Persist one encrypted user/assistant exchange in one transaction."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, user_id, title, personality
                   FROM chats WHERE client_chat_id = %s""",
                (str(client_chat_id),)
            )
            row = cur.fetchone()

            if row:
                if row[1] != user_id:
                    raise PermissionError("Chat does not belong to this user.")

                chat_id = row[0]
                existing_title = decrypt_text(row[2]) if row[2] else "New Chat"
                chat_title = title or existing_title

                cur.execute(
                    """UPDATE chats
                       SET title = %s, personality = %s, updated_at = CURRENT_TIMESTAMP
                       WHERE id = %s AND user_id = %s""",
                    (encrypt_text(chat_title), personality, chat_id, user_id)
                )
            else:
                chat_title = title or "New Chat"

                cur.execute(
                    """INSERT INTO chats (user_id, title, personality, client_chat_id)
                       VALUES (%s, %s, %s, %s)
                       RETURNING id""",
                    (user_id, encrypt_text(chat_title), personality, str(client_chat_id))
                )
                chat_id = cur.fetchone()[0]

            cur.execute(
                """INSERT INTO messages (chat_id, role, content)
                   VALUES (%s, %s, %s), (%s, %s, %s)""",
                (
                    chat_id, "user", encrypt_text(user_message),
                    chat_id, "assistant", encrypt_text(assistant_message)
                )
            )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_user_chats(user_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, client_chat_id, title, personality, created_at, updated_at
                   FROM chats
                   WHERE user_id = %s
                   ORDER BY updated_at DESC""",
                (user_id,)
            )
            rows = cur.fetchall()

            return [
                {
                    "id": row[0],
                    "chatId": row[1],
                    "title": decrypt_text(row[2]) if row[2] else "New Chat",
                    "agent": row[3] or "normal",
                    "createdAt": row[4].isoformat() if row[4] else None,
                    "updatedAt": row[5].isoformat() if row[5] else None
                }
                for row in rows
            ]
    finally:
        conn.close()


def get_chat_messages(user_id, client_chat_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT c.id, c.title, c.personality
                   FROM chats c
                   WHERE c.client_chat_id = %s AND c.user_id = %s""",
                (str(client_chat_id), user_id)
            )
            chat = cur.fetchone()

            if not chat:
                return None

            cur.execute(
                """SELECT role, content, created_at
                   FROM messages
                   WHERE chat_id = %s
                   ORDER BY id ASC""",
                (chat[0],)
            )

            messages = [
                {
                    "role": row[0],
                    "content": decrypt_text(row[1]),
                    "createdAt": row[2].isoformat() if row[2] else None
                }
                for row in cur.fetchall()
            ]

            return {
                "id": chat[0],
                "chatId": str(client_chat_id),
                "title": decrypt_text(chat[1]) if chat[1] else "New Chat",
                "agent": chat[2] or "normal",
                "messages": messages
            }
    finally:
        conn.close()


def delete_chat(user_id, client_chat_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM chats WHERE client_chat_id = %s AND user_id = %s RETURNING id",
                (str(client_chat_id), user_id)
            )
            deleted = cur.fetchone() is not None

        conn.commit()
        return deleted
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    create_tables()
