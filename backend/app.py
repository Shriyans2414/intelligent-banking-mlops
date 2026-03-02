from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from backend.routes import auth, customer, admin, monitoring

app = FastAPI(title="Banking System")

app.add_middleware(SessionMiddleware, secret_key="supersecretkey")

app.mount("/static", StaticFiles(directory="backend/static"), name="static")

app.include_router(auth.router)
app.include_router(customer.router)
app.include_router(admin.router)
app.include_router(monitoring.router)