import psycopg2
from psycopg2.extras import execute_values
from config import DB_CONFIG, BATCH_SIZE

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

# -----------------------------
# Insert Customers
# -----------------------------
def insert_customers(customers):

    conn = get_connection()
    cur = conn.cursor()

    data = [(c["full_name"],) for c in customers]

    execute_values(
        cur,
        "INSERT INTO customers (full_name) VALUES %s",
        data
    )

    conn.commit()

    # Fetch inserted IDs
    cur.execute(
        f"""
        SELECT customer_id 
        FROM customers 
        ORDER BY customer_id DESC 
        LIMIT {len(customers)}
        """
    )

    ids = cur.fetchall()
    ids.reverse()  # maintain insertion order

    cur.close()
    conn.close()

    for i, customer in enumerate(customers):
        customer["customer_id"] = ids[i][0]

    return customers

# -----------------------------
# Insert Accounts
# -----------------------------
def insert_accounts(accounts):

    conn = get_connection()
    cur = conn.cursor()

    data = []

    for idx, acc in enumerate(accounts, start=1):
        account_number = f"ACC{str(idx).zfill(8)}"

        data.append(
            (
                acc["customer_id"],
                1,  # branch_id
                account_number,
                "SAVINGS",
                acc["balance"]
            )
        )

    execute_values(
        cur,
        """
        INSERT INTO accounts 
        (customer_id, branch_id, account_number, account_type, balance)
        VALUES %s
        """,
        data
    )

    conn.commit()

    # Fetch inserted account IDs
    cur.execute(
        f"""
        SELECT account_id 
        FROM accounts 
        ORDER BY account_id ASC
        """
    )

    ids = cur.fetchall()

    cur.close()
    conn.close()

    for i, acc in enumerate(accounts):
        acc["account_id"] = ids[i][0]

    return accounts

def random_id():
    import random
    return random.randint(10000000,99999999)

# -----------------------------
# Insert Transactions
# -----------------------------
def insert_transactions(transactions):

    conn = get_connection()
    cur = conn.cursor()

    batch = []

    for txn in transactions:

        batch.append((
            txn["account_id"],
            txn["txn_type"],
            txn["amount"],
            txn["amount"],  # balance_after_txn simplified
            txn["created_at"],
            txn["is_fraud"]
        ))

        if len(batch) >= BATCH_SIZE:
            execute_values(
                cur,
                """
                INSERT INTO transactions
                (account_id, txn_type, amount, balance_after_txn, created_at, is_fraud)
                VALUES %s
                """,
                batch
            )
            batch = []

    if batch:
        execute_values(
            cur,
            """
            INSERT INTO transactions
            (account_id, txn_type, amount, balance_after_txn, created_at, is_fraud)
            VALUES %s
            """,
            batch
        )

    conn.commit()
    cur.close()
    conn.close()