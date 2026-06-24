from datetime import datetime
from typing import Optional
from fastapi import FastAPI
from sqlmodel import SQLModel, create_engine, Session ,Field ,select
import os
import json
import nats


DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
NATS_URL = os.getenv("NATS_URL")

class Operation(SQLModel, table=True):
    id            : Optional[int] = Field(default=None, primary_key=True)
    compte_source : Optional[int] = Field(default=None)
    compte_dest   : Optional[int] = Field(default=None)
    type_op       : str           = Field(default=None)
    montant       : float    = Field(default=None)
    traite_par   : Optional[int] = Field(default=None)
    statut        : str           = Field(default="en_attente")
    created_at    : datetime      = Field(default_factory=datetime.now)

class Compte(SQLModel, table=True):
    id                 : Optional[int] = Field(default=None, primary_key=True)
    user_id            : Optional[int] = Field(default=None)
    num_compte         : Optional[str] = Field(default=None)
    solde              :  float    = Field(default=None)
    derniere_operation : Optional[datetime] = Field(default=None)

class User(SQLModel, table=True):
    id    : Optional[int] = Field(default=None, primary_key=True)
    email : str
    role  : str

async def publish_log(level: str, message: str, user_id: int = None):
    nc = await nats.connect(NATS_URL)
    data = json.dumps({
        "service": "agent",
        "level": level,
        "message": message,
        "user_id": user_id
    }).encode()
    await nc.publish("logs.agent", data)
    await nc.close()

SQLModel.metadata.create_all(engine)

app = FastAPI()

@app.get("/")
def health_check():
    return {"status": "service-agent ok"}
#fonctions sur les opération
@app.get("/agent/operations/en-attente")
def get_en_attente():
    with Session(engine) as session:
        operations = session.exec(
            select(Operation).where(Operation.statut == "en_attente")
        ).all()
        return operations

@app.get("/agent/operations/historique")
def get_historique():
    with Session(engine) as session:
        operations = session.exec(
            select(Operation).where(Operation.statut != "en_attente")
        ).all()
        return operations
@app.patch("/agent/operations/{id}/valider")
async def valider_operation(id: int):
    with Session(engine) as session:
        # 1. Récupérer l'opération
        operation = session.get(Operation, id)

        # 2. Vérifier qu'elle existe
        if not operation:
            return {"error": "opération introuvable"}

        operation.statut = "validee"
        operation.traite_par = 1

        # 4. Sauvegarder
        session.add(operation)  # signale la modification à SQLModel
        session.commit()  # envoie le UPDATE à MySQL
        session.refresh(operation)  # recharge les données depuis MySQL

        await publish_log(
            level="INFO",
            message=f"Opération {id} validée",
            user_id=operation.traite_par
        )

        return operation

@app.patch("/agent/operations/{id}/refuser")
async def refuser_operation(id: int):
    with Session(engine) as session:

        operation = session.get(Operation, id)

        if not operation:
            return {"error": "opération introuvable"}

        operation.statut = "refusee"
        operation.traite_par = 1

        session.add(operation)
        session.commit()
        session.refresh(operation)

        await publish_log(
            level="INFO",
            message=f"Opération {id} refuséé",
            user_id=operation.traite_par
        )

        return operation
#fonctions sur les comptes
"""""
option 1 appel au service_auth
import httpx

@app.get("/agent/clients")
def get_clients():
    response = httpx.get("http://service-auth:8001/auth/clients")
    return response.json()
"""""
#option 2 acccède directement à la base de  donné
@app.get("/agent/clients")
def get_clients():
    with Session(engine) as session:
        clients = session.exec(
            select(User).where(User.role == "client")
        ).all()
        return clients
@app.get("/agent/clients/{user_id}/comptes")
def get_compte_client(user_id: int):
    with Session(engine) as session:
        comptes= session.exec(select(Compte).where(Compte.user_id == user_id)
        ).all()
        if not comptes:
            return {"error": "compte introuvable"}
        return comptes
