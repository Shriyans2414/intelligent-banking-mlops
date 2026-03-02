import random
import numpy as np
import psycopg2
from config import *
from generate_customers import generate_customers
from generate_accounts import generate_accounts
from transaction_simulator import simulate_transactions
from fraud_injector import inject_fraud
from db_writer import insert_customers, insert_accounts, insert_transactions

def clean_database():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("""
        TRUNCATE TABLE model_predictions,
        transactions,
        accounts,
        customers
        RESTART IDENTITY CASCADE
    """)
    conn.commit()
    cur.close()
    conn.close()

def run():
    clean_database()
    random.seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)

    print("Generating customers...")
    customers = generate_customers(NUM_CUSTOMERS)

    print("Inserting customers...")
    customers = insert_customers(customers)

    print("Generating accounts...")
    accounts = generate_accounts(customers, MAX_ACCOUNTS_PER_CUSTOMER)

    print("Inserting accounts...")
    accounts = insert_accounts(accounts)

    print("Simulating transactions...")
    transactions = simulate_transactions(
        accounts,
        TARGET_TRANSACTIONS,
        SIMULATION_DAYS
    )

    print("Injecting fraud...")
    transactions = inject_fraud(transactions, FRAUD_RATIO)

    print("Inserting transactions (this may take 1-2 minutes)...")
    insert_transactions(transactions)

    print("DONE.")

if __name__ == "__main__":
    run()