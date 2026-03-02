import random
import numpy as np
from datetime import datetime, timedelta

def simulate_transactions(accounts, target_transactions, days):

    transactions = []

    start_time = datetime.now() - timedelta(days=days)
    txn_types = ["DEPOSIT", "WITHDRAWAL", "TRANSFER_OUT"]

    for account in accounts:

        # Each account gets distributed transactions
        txn_count = random.randint(80, 200)

        for _ in range(txn_count):

            txn_type = random.choice(txn_types)

            # Lognormal realistic base
            base_amount = np.random.lognormal(mean=7.5, sigma=0.9)

            # Mild noise only
            noise = random.gauss(0, base_amount * 0.1)

            amount = max(50, round(base_amount + noise, 2))

            # Spread across full time range
            timestamp = start_time + timedelta(
                seconds=random.randint(0, days * 86400)
            )

            transactions.append({
                "account_id": account["account_id"],
                "txn_type": txn_type,
                "amount": amount,
                "created_at": timestamp,
                "is_fraud": False
            })

    return transactions