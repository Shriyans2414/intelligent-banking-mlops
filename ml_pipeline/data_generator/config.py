# config.py

NUM_CUSTOMERS = 15000
TARGET_TRANSACTIONS = 200000
FRAUD_RATIO = 0.01
SIMULATION_DAYS = 180
MAX_ACCOUNTS_PER_CUSTOMER = 2

DB_CONFIG = {
    "dbname": "banking_db",
    "user": "shriyans",
    "host": "localhost",
    "port": 5432
}

RANDOM_SEED = 42
BATCH_SIZE = 5000