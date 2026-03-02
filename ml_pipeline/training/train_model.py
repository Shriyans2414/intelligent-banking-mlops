import os
import logging
from datetime import datetime

import pandas as pd
import numpy as np
import psycopg2
import xgboost as xgb
import joblib
import mlflow
import mlflow.xgboost

from dotenv import load_dotenv
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    precision_recall_curve,
    confusion_matrix
)

# ==============================
# ENV + LOGGING SETUP
# ==============================

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# ==============================
# CONFIG
# ==============================

SNAPSHOT_TABLE = os.getenv("SNAPSHOT_TABLE")

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT")
}

MODEL_OUTPUT_DIR = "ml_pipeline/training"
os.makedirs(MODEL_OUTPUT_DIR, exist_ok=True)

# ==============================
# CONNECT DB
# ==============================

logger.info("Connecting to DB...")
conn = psycopg2.connect(**DB_CONFIG)

logger.info("Loading training snapshot...")
df = pd.read_sql(f"SELECT * FROM {SNAPSHOT_TABLE}", conn)

logger.info(f"Snapshot shape: {df.shape}")

df_time = pd.read_sql(
    "SELECT txn_id, created_at FROM transactions",
    conn
)

df = df.merge(df_time, on="txn_id")

# ==============================
# TIME-BASED SPLIT
# ==============================

df = df.sort_values("created_at").reset_index(drop=True)

split_index = int(len(df) * 0.8)

train_df = df.iloc[:split_index].copy()
test_df = df.iloc[split_index:].copy()

logger.info(f"Train size: {train_df.shape}")
logger.info(f"Test size: {test_df.shape}")

# ==============================
# FEATURE PROCESSING
# ==============================

cols_to_drop = ["txn_id", "account_id", "created_at"]

train_df = train_df.drop(columns=cols_to_drop)
test_df = test_df.drop(columns=cols_to_drop)

train_df = train_df.fillna(0)
test_df = test_df.fillna(0)

train_df = pd.get_dummies(train_df, columns=["txn_type"], drop_first=True)
test_df = pd.get_dummies(test_df, columns=["txn_type"], drop_first=True)

train_df, test_df = train_df.align(test_df, join="left", axis=1, fill_value=0)

train_df = train_df.apply(pd.to_numeric, errors="coerce").fillna(0)
test_df = test_df.apply(pd.to_numeric, errors="coerce").fillna(0)

y_train = train_df["is_fraud"]
X_train = train_df.drop(columns=["is_fraud"])

y_test = test_df["is_fraud"]
X_test = test_df.drop(columns=["is_fraud"])

# ==============================
# CLASS IMBALANCE
# ==============================

fraud_ratio = y_train.mean()
scale_pos_weight = (1 - fraud_ratio) / fraud_ratio

logger.info(f"Fraud ratio: {round(fraud_ratio, 6)}")
logger.info(f"Scale_pos_weight: {round(scale_pos_weight, 2)}")

# ==============================
# MLFLOW EXPERIMENT TRACKING
# ==============================

mlflow.set_experiment("fraud_detection_experiment")

with mlflow.start_run():

    model = xgb.XGBClassifier(
        n_estimators=400,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.9,
        scale_pos_weight=scale_pos_weight,
        random_state=42,
        eval_metric="logloss",
        n_jobs=-1
    )

    logger.info("Training model...")
    model.fit(X_train, y_train)


    # EVALUATION


    y_pred_proba = model.predict_proba(X_test)[:, 1]

    roc_auc = roc_auc_score(y_test, y_pred_proba)
    pr_auc = average_precision_score(y_test, y_pred_proba)

    logger.info(f"ROC-AUC: {round(roc_auc, 4)}")
    logger.info(f"PR-AUC: {round(pr_auc, 4)}")


    # BEST F1 THRESHOLD


    precisions, recalls, thresholds = precision_recall_curve(y_test, y_pred_proba)
    f1_scores = 2 * (precisions * recalls) / (precisions + recalls + 1e-8)

    best_f1_idx = np.argmax(f1_scores)
    best_f1_threshold = thresholds[best_f1_idx]


    # BUSINESS COST OPTIMIZATION


    cost_false_negative = 1000
    cost_false_positive = 10

    def compute_cost(threshold):
        y_pred = (y_pred_proba >= threshold).astype(int)
        cm = confusion_matrix(y_test, y_pred)
        tn, fp, fn, tp = cm.ravel()
        total_cost = (fn * cost_false_negative) + (fp * cost_false_positive)
        return total_cost, cm

    costs = []
    for t in thresholds:
        total_cost, _ = compute_cost(t)
        costs.append(total_cost)

    best_cost_idx = np.argmin(costs)
    best_cost_threshold = thresholds[best_cost_idx]
    best_cost_value, best_cost_cm = compute_cost(best_cost_threshold)


    # LOG PARAMETERS + METRICS


    mlflow.log_param("n_estimators", 400)
    mlflow.log_param("max_depth", 5)
    mlflow.log_param("learning_rate", 0.05)
    mlflow.log_param("scale_pos_weight", scale_pos_weight)

    mlflow.log_metric("roc_auc", roc_auc)
    mlflow.log_metric("pr_auc", pr_auc)
    mlflow.log_metric("best_f1_threshold", float(best_f1_threshold))
    mlflow.log_metric("best_cost_threshold", float(best_cost_threshold))
    mlflow.log_metric("min_business_cost", float(best_cost_value))

    mlflow.xgboost.log_model(model, "model")


    # SAVE MODEL LOCALLY


    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_path = f"{MODEL_OUTPUT_DIR}/fraud_model_{timestamp}.pkl"

    joblib.dump(model, model_path)

    logger.info(f"Model saved to: {model_path}")

conn.close()
logger.info("Training pipeline completed successfully.")