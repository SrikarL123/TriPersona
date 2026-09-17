from flask import session
from werkzeug.security import generate_password_hash, check_password_hash

from database import get_connection


def register_user(username, password):
    username = username.strip()

    if not username or not password:
        return False, "Username and password are required."

    if len(username) < 3:
        return False, "Username must be at least 3 characters."

    if len(password) < 6:
        return False, "Password must be at least 6 characters."

    password_hash = generate_password_hash(password)

    conn = get_connection()

    try:
        with conn.cursor() as cur:

            # Check whether username already exists
            cur.execute(
                "SELECT id FROM users WHERE username = %s",
                (username,)
            )

            if cur.fetchone():
                return False, "Username already exists."

            # Create user
            cur.execute(
                """
                INSERT INTO users (username, password_hash)
                VALUES (%s, %s)
                RETURNING id
                """,
                (username, password_hash)
            )

            user_id = cur.fetchone()[0]

        conn.commit()

        return True, {
            "id": user_id,
            "username": username
        }

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def login_user(username, password):
    username = username.strip()

    conn = get_connection()

    try:
        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT id, username, password_hash
                FROM users
                WHERE username = %s
                """,
                (username,)
            )

            user = cur.fetchone()

            if not user:
                return False, "Invalid username or password."

            user_id, stored_username, password_hash = user

            if not check_password_hash(password_hash, password):
                return False, "Invalid username or password."

            # Update login time
            cur.execute(
                """
                UPDATE users
                SET last_login = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (user_id,)
            )

        conn.commit()

        # Store only necessary information in session
        session["user_id"] = user_id
        session["username"] = stored_username

        return True, {
            "id": user_id,
            "username": stored_username
        }

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def logout_user():
    session.clear()


def get_current_user():
    user_id = session.get("user_id")

    if not user_id:
        return None

    conn = get_connection()

    try:
        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT id, username
                FROM users
                WHERE id = %s
                """,
                (user_id,)
            )

            user = cur.fetchone()

            if not user:
                session.clear()
                return None

            return {
                "id": user[0],
                "username": user[1]
            }

    finally:
        conn.close()