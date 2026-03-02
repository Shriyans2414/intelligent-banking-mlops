from backend.db import get_db, release_db
from backend.security.hashing import verify_password
from backend.security.jwt_handler import create_access_token

def authenticate_user(username: str, password: str):

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT user_id, password_hash, role FROM users WHERE username=%s", (username,))
        user = cur.fetchone()
        cur.close()
    finally:
        release_db(conn)

    if not user:
        return None

    user_id, hashed, role = user

    if not verify_password(password, hashed):
        return None

    token = create_access_token({"sub": username, "role": role})
    return {"access_token": token, "token_type": "bearer"}