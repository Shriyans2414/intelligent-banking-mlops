from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from backend.db import get_db, release_db
from backend.security.hashing import verify_password

router = APIRouter()
templates = Jinja2Templates(directory="backend/templates")



# Login Page

@router.get("/")
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})



# Login Logic

@router.post("/login")
def login(request: Request,
          username: str = Form(...),
          password: str = Form(...)):

    conn = get_db()
    try:
        cur = conn.cursor()

        cur.execute("""
            SELECT user_id, username, password_hash, role, customer_id
            FROM users
            WHERE username = %s
        """, (username,))

        user = cur.fetchone()
        cur.close()
    finally:
        release_db(conn)

    if not user:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid credentials"}
        )

    # user tuple:
    # 0 -> user_id
    # 1 -> username
    # 2 -> password_hash
    # 3 -> role
    # 4 -> customer_id

    if not verify_password(password, user[2]):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid credentials"}
        )

    # ✅ Proper session storage
    request.session["user_id"] = user[0]
    request.session["user"] = user[1]          # 🔥 This fixes logout visibility
    request.session["role"] = user[3]
    request.session["customer_id"] = user[4]

    if user[3] == "ADMIN":
        return RedirectResponse("/admin", status_code=302)

    return RedirectResponse("/dashboard", status_code=302)



# Logout

@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=302)