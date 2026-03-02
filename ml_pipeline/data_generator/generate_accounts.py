import random
from datetime import datetime, timedelta

def generate_accounts(customer_records, max_accounts):
    accounts = []

    for customer in customer_records:
        num_accounts = random.randint(1, max_accounts)

        for _ in range(num_accounts):

            income = customer["income_band"]

            if income == "LOW":
                balance = random.uniform(5000, 25000)
            elif income == "MID":
                balance = random.uniform(30000, 200000)
            else:
                balance = random.uniform(200000, 2000000)

            # 🔥 Older account creation (30 to 3 years old)
            days_old = random.randint(30, 1095)
            created_at = datetime.now() - timedelta(days=days_old)

            accounts.append({
                "customer_id": customer["customer_id"],
                "balance": round(balance, 2),
                "created_at": created_at
            })

    return accounts