import os
import joblib
import numpy as np
from fastapi import FastAPI
from pydantic import BaseModel
from threading import Lock
from psycopg2 import pool


# CONFIGURATION

MODEL_DIR = "ml_pipeline/training"

DB_CONFIG = {
    "dbname": "banking_db",
    "user": "shriyans",
    "host": "localhost",
    "port": 5432
}

# DATABASE CONNECTION POOL

connection_pool = pool.SimpleConnectionPool(
    minconn=1,
    maxconn=20,
    **DB_CONFIG
)

print("✅ Fraud Service DB Pool Initialized")


def get_db_connection():
    return connection_pool.getconn()


def release_db_connection(conn):
    connection_pool.putconn(conn)


# MODEL MANAGER (Thread-Safe + Artifact-Aware)

class ModelManager:
    def __init__(self, model_dir):
        self.model_dir = model_dir
        self.model = None
        self.model_version = None
        self.threshold = None
        self.feature_list = None
        self.lock = Lock()
        self.load_latest_model()

    def get_latest_model_file(self):
        model_files = sorted(
            [f for f in os.listdir(self.model_dir)
             if f.startswith("fraud_model_")]
        )
        if not model_files:
            raise Exception("No trained fraud model found.")
        return model_files[-1]

    def load_latest_model(self):
        with self.lock:
            latest_model_file = self.get_latest_model_file()

            if latest_model_file != self.model_version:
                print(f"🔄 Loading new model: {latest_model_file}")

                artifact = joblib.load(
                    os.path.join(self.model_dir, latest_model_file)
                )

                self.model = artifact["model"]
                self.threshold = artifact["threshold"]
                self.feature_list = artifact["feature_list"]
                self.model_version = artifact["version"]

    def get_model(self):
        self.load_latest_model()
        return (
            self.model,
            self.threshold,
            self.feature_list,
            self.model_version
        )


model_manager = ModelManager(MODEL_DIR)

# FASTAPI INIT

app = FastAPI(title="Fraud Detection Service - Production")


# INPUT SCHEMA

class TransactionFeatures(BaseModel):
    txn_id: int
    amount: float
    hour_of_day: int
    day_of_week: int
    account_age_days: float
    current_balance: float
    txn_count_last_1h: int
    txn_count_last_24h: int
    txn_count_last_7d: int
    total_amount_last_24h: float
    avg_amount_last_7d: float
    max_amount_last_7d: float
    hours_since_last_txn: float
    amount_to_avg_ratio: float
    amount_to_balance_ratio: float
    txn_type_DEPOSIT: int
    txn_type_TRANSFER_OUT: int


# DATABASE UTIL

def log_prediction(txn_id, probability, decision, model_version, threshold):

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO model_predictions
            (txn_id, model_version, fraud_probability, threshold, decision)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            txn_id,
            model_version,
            probability,
            threshold,
            decision
        ))

        conn.commit()
        cur.close()

    finally:
        release_db_connection(conn)


# ENDPOINTS

@app.get("/")
def health():
    _, threshold, _, model_version = model_manager.get_model()
    return {
        "status": "running",
        "model_version": model_version,
        "threshold": threshold
    }

@app.get("/model-info")
def model_info():
    _, threshold, _, model_version = model_manager.get_model()
    return {
        "model_version": model_version,
        "threshold": threshold
    }

@app.get("/metrics")
def metrics():

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        cur.execute("""
            SELECT 
                COUNT(*) as total_predictions,
                SUM(CASE WHEN decision = TRUE THEN 1 ELSE 0 END) as fraud_flagged
            FROM model_predictions
        """)

        result = cur.fetchone()
        total = result[0] or 0
        flagged = result[1] or 0

        fraud_rate = (flagged / total) if total > 0 else 0

        cur.close()

    finally:
        release_db_connection(conn)

    return {
        "total_predictions": total,
        "fraud_flagged": flagged,
        "fraud_rate": round(fraud_rate, 6)
    }

@app.post("/predict")
def predict(features: TransactionFeatures):

    model, threshold, feature_list, model_version = model_manager.get_model()

    # Convert Pydantic model to dict
    feature_dict = features.dict()

    # Remove txn_id before ordering
    txn_id = feature_dict.pop("txn_id")

    # Ensure strict feature ordering
    feature_array = np.array([[feature_dict[col] for col in feature_list]])

    fraud_probability = float(model.predict_proba(feature_array)[0][1])
    decision = fraud_probability >= threshold

    log_prediction(
        txn_id,
        fraud_probability,
        decision,
        model_version,
        threshold
    )

    return {
        "txn_id": txn_id,
        "fraud_probability": round(fraud_probability, 6),
        "decision": decision,
        "threshold": threshold,
        "model_version": model_version
    }