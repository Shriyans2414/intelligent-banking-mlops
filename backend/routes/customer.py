from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from backend.db import get_db, release_db
from backend.config import FRAUD_SERVICE_URL
import uuid
import requests

router = APIRouter()
templates = Jinja2Templates(directory="backend/templates")

==========
# SAFE FRAUD CALL
==========
def call_fraud_service(txn_id):
    print("Calling Fraud Service for txn:", txn_id)

    try:
        response = requests.post(
            FRAUD_SERVICE_URL,
            json={"txn_id": txn_id},
            timeout=5
        )
        print("Fraud Response:", response.status_code)
        print("Fraud Response Body:", response.text)

    except Exception as e:
        print("Fraud service error:", str(e))


==========
# VALIDATE ACCOUNT OWNERSHIP
==========
def validate_account_owner(user_id, account_id):

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT 1
            FROM accounts a
            JOIN users u ON a.customer_id = u.customer_id
            WHERE u.user_id = %s AND a.account_id = %s
        """, (user_id, account_id))
        valid = cur.fetchone()
        cur.close()
    finally:
        release_db(conn)

    return bool(valid)


==========
# DASHBOARD
==========
@router.get("/dashboard")
def dashboard(request: Request):

    if "user_id" not in request.session:
        return RedirectResponse("/", status_code=302)

    if request.session.get("role") == "ADMIN":
        return RedirectResponse("/admin", status_code=302)

    user_id = request.session["user_id"]

    conn = get_db()
    try:
        cur = conn.cursor()

        # Get customer_id
        cur.execute("""
            SELECT customer_id
            FROM users
            WHERE user_id = %s
        """, (user_id,))
        result = cur.fetchone()

        if not result or not result[0]:
            return RedirectResponse("/", status_code=302)

        customer_id = result[0]

        # Get accounts
        cur.execute("""
            SELECT account_id, account_number, balance
            FROM accounts
            WHERE customer_id = %s
        """, (customer_id,))
        accounts = cur.fetchall()

        # Get transactions + fraud score
        cur.execute("""
            SELECT t.txn_id,
                   t.txn_type,
                   t.amount,
                   t.status,
                   mp.fraud_probability,
                   t.created_at
            FROM transactions t
            LEFT JOIN model_predictions mp
                ON t.txn_id = mp.txn_id
            WHERE t.account_id IN (
                SELECT account_id
                FROM accounts
                WHERE customer_id = %s
            )
            ORDER BY t.created_at DESC
            LIMIT 20
        """, (customer_id,))
        transactions = cur.fetchall()

        cur.close()

    finally:
        release_db(conn)

    return templates.TemplateResponse(
        "customer_dashboard.html",
        {
            "request": request,
            "accounts": accounts,
            "transactions": transactions
        }
    )


==========
# DEPOSIT
==========
@router.post("/deposit")
def deposit(request: Request,
            account_id: int = Form(...),
            amount: float = Form(...)):

    user_id = request.session.get("user_id")
    if not validate_account_owner(user_id, account_id):
        return RedirectResponse("/dashboard", status_code=302)

    idempotency_key = str(uuid.uuid4())

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT fn_deposit(%s,%s,%s,%s)",
            (account_id, amount, "Web Deposit", idempotency_key)
        )
        txn_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
    finally:
        release_db(conn)

    call_fraud_service(txn_id)

    return RedirectResponse("/dashboard", status_code=302)


==========
# WITHDRAW
==========
@router.post("/withdraw")
def withdraw(request: Request,
             account_id: int = Form(...),
             amount: float = Form(...)):

    user_id = request.session.get("user_id")
    if not validate_account_owner(user_id, account_id):
        return RedirectResponse("/dashboard", status_code=302)

    idempotency_key = str(uuid.uuid4())

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT fn_withdraw(%s,%s,%s,%s)",
            (account_id, amount, "Web Withdraw", idempotency_key)
        )
        txn_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
    finally:
        release_db(conn)

    call_fraud_service(txn_id)

    return RedirectResponse("/dashboard", status_code=302)


==========
# TRANSACTION HISTORY PAGE
==========
@router.get("/transactions")
def transaction_history(request: Request):

    if "user_id" not in request.session:
        return RedirectResponse("/", status_code=302)

    user_id = request.session["user_id"]

    conn = get_db()
    try:
        cur = conn.cursor()

        # Get customer_id
        cur.execute("""
            SELECT customer_id
            FROM users
            WHERE user_id = %s
        """, (user_id,))
        customer_id = cur.fetchone()[0]

        cur.execute("""
            SELECT t.txn_id,
                   t.txn_type,
                   t.amount,
                   t.created_at,
                   t.account_id,
                   t.related_account_id,
                   mp.fraud_probability,
                   mp.decision
            FROM transactions t
            LEFT JOIN model_predictions mp
                ON t.txn_id = mp.txn_id
            JOIN accounts a
                ON t.account_id = a.account_id
            WHERE a.customer_id = %s
            ORDER BY t.created_at DESC
            LIMIT 50
        """, (customer_id,))

        transactions = cur.fetchall()
        cur.close()

    finally:
        release_db(conn)

    return templates.TemplateResponse(
        "transactions.html",
        {
            "request": request,
            "transactions": transactions,
            "is_admin": False
        }
    )