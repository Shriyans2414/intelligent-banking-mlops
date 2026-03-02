from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from backend.db import get_db, release_db

router = APIRouter()
templates = Jinja2Templates(directory="backend/templates")


@router.get("/monitoring")
def monitoring(request: Request):

    if "user" not in request.session:
        return RedirectResponse("/", status_code=302)

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*),
                   SUM(CASE WHEN decision=TRUE THEN 1 ELSE 0 END)
            FROM model_predictions
        """)
        metrics = cur.fetchone()
        cur.close()
    finally:
        release_db(conn)

    return templates.TemplateResponse(
        "monitoring.html",
        {"request": request, "metrics": metrics}
    )