import os
import joblib
import numpy as np
import psycopg2
from fastapi import FastAPI
from pydantic import BaseModel
from threading import Lock

=============
# CONFIG
=============

MODEL_DIR = "ml_pipeline/training"
PRODUCTION_THRESHOLD = 0.45

DB_CONFIG = {
    "dbname": "banking_db",
    "user": "shriyans",
    "host": "localhost",
    "port": 5432
}

=============
# MODEL MANAGER
=============

class ModelManager:
    def __init__(self, model_dir):
        self.model_dir = model_dir
        self.model = None
        self.model_version = None
        self.lock = Lock()
        self.load_latest_model()

    def get_latest_model_file(self):
        model_files = sorted(
            [f for f in os.listdir(self.model_dir) if f.startswith("fraud_model_")]
        )
        if not model_files:
            raise Exception("No trained fraud model found.")
        return model_files[-1]

    def load_latest_model(self):
        with self.lock:
            latest = self.get_latest_model_file()
            if latest != self.model_version:
                print(f"Loading model: {latest}")
                self.model = joblib.load(
                    os.path.join(self.model_dir, latest)
                )
                self.model_version = latest

    def get_model(self):
        self.load_latest_model()
        return self.model, self.model_version


model_manager = ModelManager(MODEL_DIR)

app = FastAPI(title="Fraud Detection Service")

=============
# INPUT SCHEMA
=============

class FraudRequest(BaseModel):
    txn_id: int

=============
# DB UTIL
=============

def get_features_for_txn(txn_id):

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute("SELECT * FROM get_features_for_txn(%s)", (txn_id,))
    row = cur.fetchone()

    cur.close()
    conn.close()

    return row


def update_transaction(txn_id, probability, decision):

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Determine final status
    status = "REJECTED_FRAUD" if decision else "APPROVED"

    # Update transaction status + fraud score
    cur.execute("""
        UPDATE transactions
        SET fraud_score = %s,
            status = %s
        WHERE txn_id = %s
    """, (probability, status, txn_id))

    =========
    # 🔥 AUTOMATIC REVERSAL IF FRAUD
    =========

    if decision:
        # Get txn details
        cur.execute("""
            SELECT account_id, amount, txn_type
            FROM transactions
            WHERE txn_id = %s
        """, (txn_id,))
        account_id, amount, txn_type = cur.fetchone()

        if txn_type == "DEPOSIT":
            # Reverse deposit → subtract
            cur.execute("""
                UPDATE accounts
                SET balance = balance - %s
                WHERE account_id = %s
            """, (amount, account_id))

        elif txn_type == "WITHDRAWAL":
            # Reverse withdrawal → add back
            cur.execute("""
                UPDATE accounts
                SET balance = balance + %s
                WHERE account_id = %s
            """, (amount, account_id))

        elif txn_type == "TRANSFER_OUT":
            # Reverse transfer → add back to sender
            cur.execute("""
                UPDATE accounts
                SET balance = balance + %s
                WHERE account_id = %s
            """, (amount, account_id))

    =========
    # Store prediction record
    =========

    cur.execute("""
        INSERT INTO model_predictions
        (txn_id, model_version, fraud_probability, threshold, decision)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        txn_id,
        model_manager.model_version,
        probability,
        PRODUCTION_THRESHOLD,
        decision
    ))

    conn.commit()
    cur.close()
    conn.close()

=============
# HEALTH
=============

@app.get("/")
def health():
    _, version = model_manager.get_model()
    return {
        "status": "running",
        "model_version": version,
        "threshold": PRODUCTION_THRESHOLD
    }

=============
# PREDICT
=============

@app.post("/predict")
def predict(request: FraudRequest):

    model, version = model_manager.get_model()

    features = get_features_for_txn(request.txn_id)

    if not features:
        return {"error": "Transaction not found"}

    feature_array = np.array([features])

    probability = float(model.predict_proba(feature_array)[0][1])
    decision = probability >= PRODUCTION_THRESHOLD

    update_transaction(request.txn_id, probability, decision)

    return {
        "txn_id": request.txn_id,
        "fraud_probability": round(probability, 6),
        "decision": decision,
        "status": "REJECTED_FRAUD" if decision else "APPROVED",
        "model_version": version
    }