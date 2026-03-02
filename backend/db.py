from psycopg2 import pool
from backend.config import DATABASE_CONFIG

connection_pool = pool.SimpleConnectionPool(
    1,
    20,
    **DATABASE_CONFIG
)

def get_db():
    return connection_pool.getconn()

def release_db(conn):
    connection_pool.putconn(conn)