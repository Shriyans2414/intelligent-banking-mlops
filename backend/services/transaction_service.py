import uuid
import requests
from backend.db import get_db, release_db
from backend.config import FRAUD_SERVICE_URL

def deposit(account_id: int, amount: float):

    idempotency_key = str(uuid.uuid4())

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT fn_deposit(%s,%s,%s,%s)",
            (account_id, amount, "API Deposit", idempotency_key)
        )
        txn_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
    finally:
        release_db(conn)

    # Call fraud service
    requests.post(FRAUD_SERVICE_URL, json={"txn_id": txn_id})

    return {"status": "PENDING", "txn_id": txn_id}