from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI
from sqlmodel import SQLModel, create_engine, Session, Field, select
import json
import os
import asyncio
import nats

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

SQLModel.metadata.create_all(engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_nats()
    yield

app = FastAPI(lifespan=lifespan)

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

