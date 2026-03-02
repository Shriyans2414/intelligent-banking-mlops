import random

def generate_customers(num_customers):
    income_bands = ["LOW", "MID", "HIGH"]
    behaviors = ["CONSERVATIVE", "MODERATE", "AGGRESSIVE"]

    customers = []

    for i in range(num_customers):
        customers.append({
            "full_name": f"Customer_{i}",
            "income_band": random.choices(income_bands, weights=[0.4,0.4,0.2])[0],
            "behavior": random.choice(behaviors)
        })

    return customers