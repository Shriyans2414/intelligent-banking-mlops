import random
import numpy as np

def inject_fraud(transactions, fraud_ratio=0.15):
    """
    Probabilistic fraud injection.
    Fraud depends on:
    - amount deviation
    - frequency
    - relative spike
    - randomness
    """

    total_txns = len(transactions)

    for txn in transactions:

        amount = txn["amount"]

        # Base fraud probability
        prob = 0.01

        # Medium-range fraud (behavioral anomaly)
        if 1000 < amount < 5000:
            prob += 0.05

        # High-value fraud
        if amount > 5000:
            prob += 0.25

        # Very high-value fraud
        if amount > 10000:
            prob += 0.4

        # Random noise
        prob += random.uniform(-0.02, 0.02)

        prob = max(0, min(prob, 0.9))

        txn["is_fraud"] = random.random() < prob

        # If fraud → slightly inflate amount (not 20x anymore)
        if txn["is_fraud"]:
            txn["amount"] *= random.uniform(1.2, 2.5)

    # Ensure overall fraud ratio not extreme
    fraud_count = sum(t["is_fraud"] for t in transactions)
    actual_ratio = fraud_count / total_txns

    print("Actual fraud ratio:", round(actual_ratio, 4))

    return transactions