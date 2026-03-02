from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from backend.db import get_db, release_db

router = APIRouter()
templates = Jinja2Templates(directory="backend/templates")

from backend.security.hashing import hash_password
from fastapi import Form
from fastapi.responses import RedirectResponse

@router.post("/admin/create-user")
def create_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    customer_id: int = Form(...)
):
    if request.session.get("role") != "ADMIN":
        return RedirectResponse("/", status_code=302)

    conn = get_db()
    try:
        cur = conn.cursor()

        hashed = hash_password(password)

        cur.execute("""
            INSERT INTO users (username, password_hash, role, customer_id)
            VALUES (%s, %s, %s, %s)
        """, (username, hashed, "TELLER", customer_id))

        conn.commit()
        cur.close()
    finally:
        release_db(conn)

    return RedirectResponse("/admin", status_code=302)

@router.post("/admin/reset-password")
def reset_password(
    request: Request,
    username: str = Form(...),
    new_password: str = Form(...)
):
    if request.session.get("role") != "ADMIN":
        return RedirectResponse("/", status_code=302)

    conn = get_db()
    try:
        cur = conn.cursor()

        hashed = hash_password(new_password)

        cur.execute("""
            UPDATE users
            SET password_hash = %s
            WHERE username = %s
        """, (hashed, username))

        conn.commit()
        cur.close()
    finally:
        release_db(conn)

    return RedirectResponse("/admin", status_code=302)


# All Transactions (Admin)

@router.get("/admin/transactions")
def admin_transactions(request: Request):

    if request.session.get("role") != "ADMIN":
        return RedirectResponse("/", status_code=302)

    conn = get_db()
    try:
        cur = conn.cursor()

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
            LEFT JOIN model_predictions mp ON t.txn_id = mp.txn_id
            ORDER BY t.created_at DESC
            LIMIT 100
        """)

        transactions = cur.fetchall()
        cur.close()
    finally:
        release_db(conn)

    return templates.TemplateResponse(
        "transactions.html",
        {
            "request": request,
            "transactions": transactions,
            "is_admin": True
        }
    )

@router.post("/admin/create-account")
def create_account(
    request: Request,
    customer_id: int = Form(...),
    account_type: str = Form(...)
):
    if request.session.get("role") != "ADMIN":
        return RedirectResponse("/", status_code=302)

    conn = get_db()
    try:
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO accounts (customer_id, account_type, balance)
            VALUES (%s, %s, 0.00)
        """, (customer_id, account_type))

        conn.commit()
        cur.close()
    finally:
        release_db(conn)

    return RedirectResponse("/admin", status_code=302)

@router.get("/admin")
def admin_dashboard(request: Request):

    # Only ADMIN allowed
    if request.session.get("role") != "ADMIN":
        return RedirectResponse("/", status_code=302)

    conn = get_db()
    try:
        cur = conn.cursor()

        
        # Transaction Summary
        
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'APPROVED' THEN 1 ELSE 0 END) as approved,
                SUM(CASE WHEN status = 'REJECTED_FRAUD' THEN 1 ELSE 0 END) as rejected,
                SUM(CASE WHEN status = 'PENDING' THEN 1 ELSE 0 END) as pending
            FROM transactions
        """)
        summary = cur.fetchone()

    
        # Average Fraud Score
        
        cur.execute("""
            SELECT AVG(fraud_score)
            FROM transactions
            WHERE fraud_score IS NOT NULL
        """)
        avg_score = cur.fetchone()[0]

        
        # Recent Fraud Transactions
        
        cur.execute("""
            SELECT txn_id, account_id, amount, fraud_score, created_at
            FROM transactions
            WHERE status = 'REJECTED_FRAUD'
            ORDER BY created_at DESC
            LIMIT 5
        """)
        recent_frauds = cur.fetchall()

        cur.close()

    finally:
        release_db(conn)

    return templates.TemplateResponse(
        "admin_dashboard.html",
        {
            "request": request,
            "summary": summary,
            "avg_score": avg_score,
            "recent_frauds": recent_frauds
        }
    )