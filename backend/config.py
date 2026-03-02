import os

DATABASE_CONFIG = {
    "dbname": "banking_db",
    "user": "shriyans",
    "host": "localhost",
    "port": 5432
}

SECRET_KEY = "supersecretkey"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

FRAUD_SERVICE_URL = "http://127.0.0.1:8001/predict"