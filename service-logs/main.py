from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI,Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlmodel import SQLModel, create_engine, Session, Field, select ,func
from dotenv import load_dotenv
import json
import time
import os
import nats

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
NATS_URL = os.getenv("NATS_URL")

class Log(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    service :Optional[str] = Field(default=None)
    level :Optional[str] = Field(default=None)
    message :Optional[str] = Field(default=None)
    user_id: Optional[int] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.now)

engine = create_engine(DATABASE_URL)

async def start_nats():
    nc = await nats.connect(NATS_URL)
    await nc.subscribe("logs.>", cb= handle_message)

async def handle_message(msg):
    data = json.loads(msg.data.decode())

    log = Log(
        service=data["service"],
        level=data["level"],
        message=data["message"],
        user_id=data.get("user_id")  # .get() car optionnel
    )

    with Session(engine) as session:
        session.add(log)
        session.commit()

def attendre_mysql(max_tentatives=10):
    for tentative in range(max_tentatives):
        try:
            SQLModel.metadata.create_all(engine)
            print("Connexion MySQL réussie")
            return
        except Exception:
            print(f"MySQL pas encore prêt, tentative {tentative + 1}/{max_tentatives}")
            time.sleep(3)
    raise Exception("Impossible de se connecter à MySQL")

attendre_mysql()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_nats()
    yield

app = FastAPI(lifespan=lifespan)

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="templates/static"), name="static")


@app.get("/")
def health_check():
    return {"status": "service-logs ok"}
@app.get("/logs/")
def get_logs(
    service   : Optional[str]      = None,
    level     : Optional[str]      = None,
    from_date : Optional[datetime] = None,
    to_date   : Optional[datetime] = None
):
    with Session(engine) as session:
        query = select(Log)
        if service:
            query = query.where(Log.service == service)
        if level:
            query = query.where(Log.level == level)
        if from_date:
            query = query.where(Log.created_at >= from_date)
        if to_date:
            query = query.where(Log.created_at <= to_date)
        logs = session.exec(query).all()
        return logs
@app.get("/logs/stats")
def get_logs_stats():
    with Session(engine) as session:
        total = session.exec(select(func.count(Log.id))).one()

        par_service = session.exec(
            select(Log.service, func.count(Log.id)).group_by(Log.service)
        ).all()

        par_level = session.exec(
            select(Log.level, func.count(Log.id)).group_by(Log.level)
        ).all()

        return {
            "total": total,
            "par_service": dict(par_service),
            "par_level": dict(par_level)
        }

@app.get("/logs/dashboard", response_class=HTMLResponse)
async def dashboard_logs(request: Request):
    return templates.TemplateResponse(request=request, name="logs.html")