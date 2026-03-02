import psycopg2
from datetime import datetime

DB_CONFIG = {
    "dbname": "banking_db",
    "user": "shriyans",
    "host": "localhost",
    "port": 5432
}

def build_snapshot():

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    print("Refreshing materialized view...")
    cur.execute("REFRESH MATERIALIZED VIEW fraud_features;")
    conn.commit()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_table = f"fraud_training_snapshot_{timestamp}"

    print(f"Creating snapshot table: {snapshot_table}")

    cur.execute(f"""
        CREATE TABLE {snapshot_table} AS
        SELECT * FROM fraud_features;
    """)
    conn.commit()

    print("Snapshot created successfully.")

    cur.close()
    conn.close()

    return snapshot_table


if __name__ == "__main__":
    snapshot_name = build_snapshot()
    print("Training dataset snapshot:", snapshot_name)