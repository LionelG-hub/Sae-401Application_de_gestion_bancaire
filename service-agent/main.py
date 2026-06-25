from datetime import datetime
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import SQLModel, create_engine, Session ,Field ,select
import os
import httpx
import json
import nats
import time

# Charge les variables du fichier .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
NATS_URL = os.getenv("NATS_URL")
security = HTTPBearer()

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

"""
class User(SQLModel, table=True):
    id    : Optional[int] = Field(default=None, primary_key=True)
    email : str
    role  : str
"""


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



async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    # Appelle le service auth pour vérifier le token
    response = httpx.get(
        "http://service-authentication:8000/verify-token",
        headers={"Authorization": f"Bearer {token}"}
    )
    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide"
        )
    data = response.json()
    if data["role"] != "agent":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux agents"
        )
        # Récupère les informations complètes de l'agent depuis le service auth
    me_response = httpx.get(
        "http://service-authentication:8000/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    agent_data = me_response.json()

    # Retourne l'id et les infos de l'agent
    return {
        "id": agent_data["id"],
        "email": agent_data["email"],
        "role": agent_data["role"]
    }


app = FastAPI()

@app.get("/")
def health_check():
    return {"status": "service-agent ok"}
#fonctions sur les opération
@app.get("/agent/operations/en-attente")
def get_en_attente(user=Depends(verify_token)):
    with Session(engine) as session:
        operations = session.exec(
            select(Operation).where(Operation.statut == "en_attente")
        ).all()
        return operations

@app.get("/agent/operations/historique")
def get_historique(user=Depends(verify_token)):
    with Session(engine) as session:
        operations = session.exec(
            select(Operation).where(Operation.statut != "en_attente")
        ).all()
        return operations
@app.patch("/agent/operations/{id}/valider")
async def valider_operation(id: int,user=Depends(verify_token)):
    with Session(engine) as session:
        # 1. Récupérer l'opération
        operation = session.get(Operation, id)

        # 2. Vérifier qu'elle existe
        if not operation:
            return {"error": "opération introuvable"}

        operation.statut = "validee"
        operation.traite_par = user["id"]

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
async def refuser_operation(id: int ,user=Depends(verify_token)):
    with Session(engine) as session:

        operation = session.get(Operation, id)

        if not operation:
            return {"error": "opération introuvable"}

        operation.statut = "refusee"
        operation.traite_par = user["id"]

        session.add(operation)
        session.commit()
        session.refresh(operation)

        await publish_log(
            level="INFO",
            message=f"Opération {id} refuséé",
            user_id=operation.traite_par
        )

        return operation
#fonctions sur les comptes/option 1 appel au service_auth

@app.get("/agent/clients")
def get_clients(user=Depends(verify_token)):
    response =  httpx.get("http://service-authentication:8000/clients")
    
    return response.json()
"""
#option 2 acccède directement à la base de  donné
@app.get("/agent/clients")
def get_clients():
    with Session(engine) as session:
        clients = session.exec(
            select(User).where(User.role == "client")
        ).all()
        return clients
"""
@app.get("/agent/clients/{user_id}/comptes")
def get_compte_client(user_id: int,user=Depends(verify_token)):
    with Session(engine) as session:
        comptes= session.exec(select(Compte).where(Compte.user_id == user_id)
        ).all()
        if not comptes:
            return {"error": "compte introuvable"}
        return comptes
