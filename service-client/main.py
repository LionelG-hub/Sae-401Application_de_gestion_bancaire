"""
service-client(1) (Pôle 2 / Baye)
================================
C'est le COEUR métier de la banque. Il gère :
  - la consultation des comptes par le client,
  - la création d'opérations (retrait / depot / virement),
  - l'application de l'effet d'une opération quand elle est validée
    (c'est lui qui déplace réellement l'argent entre les comptes).

Règles importantes (sujet) :
  - retrait et virement -> doivent être validés par un agent (statut "en_attente"),
  - depot -> appliqué immédiatement (pas de validation),
  - statuts EXACTS partagés avec l'agent : en_attente / validee / refusee.

Sécurité :
  - L'identité vient TOUJOURS du token. On ne décode pas le JWT ici : on
    demande au service d'authentification (GET /me) qui est l'utilisateur.
  - Un client ne peut agir que sur SES comptes (vérif via l'id du token).
"""
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlmodel import SQLModel, create_engine, Session, Field, select
from dotenv import load_dotenv
import os
import httpx
import json
import nats
import time

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://service-authentication:8000")
NATS_URL = os.getenv("NATS_URL", "nats://nats:4222")

engine = create_engine(DATABASE_URL)
security = HTTPBearer()

# Contrat d'équipe : valeurs EXACTES des statuts (identiques côté agent)
STATUT_ATTENTE = "en_attente"
STATUT_VALIDEE = "validee"
STATUT_REFUSEE = "refusee"


# --- Tables partagées de bank_db (mêmes champs que côté agent) ---
class Compte(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None)
    num_compte: Optional[str] = Field(default=None)
    solde: float = Field(default=0)
    derniere_operation: Optional[datetime] = Field(default=None)


class Operation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    compte_source: Optional[int] = Field(default=None)
    compte_dest: Optional[int] = Field(default=None)
    type_op: str = Field(default=None)
    montant: float = Field(default=None)
    traite_par: Optional[int] = Field(default=None)
    statut: str = Field(default=STATUT_ATTENTE)
    created_at: datetime = Field(default_factory=datetime.now)
    user_id: Optional[int] = Field(default=None)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    # On NE décode PAS le token nous-mêmes : on demande au service d'auth
    # qui est l'utilisateur (cohérent avec le reste de l'équipe).
    token = credentials.credentials
    try:
        response = httpx.get(
            f"{AUTH_SERVICE_URL}/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
    except Exception:
        raise HTTPException(status_code=503, detail="Service d'authentification injoignable")
    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Token invalide")
    # /me renvoie {id, email, role}
    return response.json()


async def publier_log(level: str, message: str, user_id: int = None):
    try:
        nc = await nats.connect(NATS_URL)
        data = json.dumps({
            "service": "client",
            "level": level,
            "message": message,
            "user_id": user_id,
        }).encode()
        await nc.publish("logs.client", data)
        await nc.close()
    except Exception as e:
        print(f"service-client(1) : publication log échouée : {e}")


def appliquer_solde(session: Session, compte_id: int, delta: float):
    # Déplace l'argent sur UN compte (delta peut être négatif).
    compte = session.get(Compte, compte_id)
    if not compte:
        raise HTTPException(status_code=404, detail=f"Compte {compte_id} introuvable")
    nouveau = compte.solde + delta
    if nouveau < 0:
        raise HTTPException(status_code=400, detail="Solde insuffisant")
    compte.solde = nouveau
    compte.derniere_operation = datetime.now()
    session.add(compte)


def compte_appartient(session: Session, compte_id: int, user_id: int) -> bool:
    compte = session.get(Compte, compte_id)
    return compte is not None and compte.user_id == user_id


def attendre_mysql(max_tentatives=10):
    for tentative in range(max_tentatives):
        try:
            SQLModel.metadata.create_all(engine)
            print("service-client(1) : connexion MySQL OK")
            return
        except Exception:
            print(f"service-client(1) : MySQL pas prêt, tentative {tentative + 1}/{max_tentatives}")
            time.sleep(3)
    raise Exception("service-client(1) : connexion MySQL impossible")


attendre_mysql()

app = FastAPI(title="service-client(1)")

# Pages web du client (servies par ce service)
templates = Jinja2Templates(directory="templates")


class OperationInput(BaseModel):
    type_op: str                       # retrait | depot | virement
    montant: float
    compte_source: Optional[int] = None
    compte_dest: Optional[int] = None


class LoginInput(BaseModel):
    email: str
    mot_de_passe: str


@app.get("/")
def health_check():
    return {"status": "service-client(1) ok"}


# ================= INTERFACE WEB CLIENT =================
# Tout est servi par ce service (même origine -> pas de souci de token).
@app.get("/client/login", response_class=HTMLResponse)
def page_login(request: Request):
    return templates.TemplateResponse(request=request, name="login_client.html")


@app.get("/client/dashboard", response_class=HTMLResponse)
def page_dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="dashboard_client.html")


@app.post("/client/login")
def relais_login(data: LoginInput):
    # On RELAIE la connexion au service d'authentification (qui fait tout le
    # vrai travail : vérif du mot de passe, création du JWT). Avantage : le
    # navigateur ne parle qu'à service-client(1) -> pas de problème de CORS.
    try:
        r = httpx.post(
            f"{AUTH_SERVICE_URL}/login",
            json={"email": data.email, "mot_de_passe": data.mot_de_passe},
            timeout=10,
        )
    except Exception:
        raise HTTPException(status_code=503, detail="Service d'authentification injoignable")
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    return r.json()   # {access_token, token_type}


# ---------------- API CLIENT ----------------
@app.get("/comptes/me")
def mes_comptes(user=Depends(get_current_user)):
    with Session(engine) as session:
        comptes = session.exec(
            select(Compte).where(Compte.user_id == user["id"])
        ).all()
    return comptes


@app.post("/comptes")
async def ouvrir_compte(user=Depends(get_current_user)):
    # Un client ouvre un nouveau compte (solde 0). C'est ce qui permet, le jour
    # de la démo, de créer un client puis de lui ouvrir un compte EN DIRECT,
    # sans rien écrire à la main dans la base.
    if user["role"] != "client":
        raise HTTPException(status_code=403, detail="Réservé aux clients")
    with Session(engine) as session:
        op = Operation(
            type_op="creation_compte",
            montant=0.0,
            statut=STATUT_ATTENTE,
            user_id=user["id"],
        )
        # numéro de compte lisible, basé sur l'id auto-incrémenté (ex: CPT004)
        session.add(op)
        session.commit()
        session.refresh(op)
    await publier_log("INFO", f"Demande création compte par client {user['id']}", user["id"])
    return {"message": "Demande de création de compte en attente de validation"}


@app.get("/operations/me")
def mes_operations(user=Depends(get_current_user)):
    with Session(engine) as session:
        mes_comptes_ids = {
            c.id for c in session.exec(
                select(Compte).where(Compte.user_id == user["id"])
            ).all()
        }
        toutes = session.exec(select(Operation)).all()
        ops = [o for o in toutes
               if o.compte_source in mes_comptes_ids
               or o.compte_dest in mes_comptes_ids
               or o.user_id == user["id"]]
    return ops


@app.post("/operations")
async def creer_operation(data: OperationInput, user=Depends(get_current_user)):
    if user["role"] != "client":
        raise HTTPException(status_code=403, detail="Réservé aux clients")
    if data.montant <= 0:
        raise HTTPException(status_code=400, detail="Montant invalide")
    if data.type_op not in ("retrait", "depot", "virement"):
        raise HTTPException(status_code=400, detail="Type d'opération inconnu")

    with Session(engine) as session:
        # Vérif de propriété via le TOKEN (jamais via le navigateur)
        if data.type_op in ("retrait", "virement"):
            if data.compte_source is None or not compte_appartient(session, data.compte_source, user["id"]):
                raise HTTPException(status_code=403, detail="Compte source non autorisé")
        if data.type_op == "virement" and data.compte_dest is None:
            raise HTTPException(status_code=400, detail="Compte destinataire requis")
        if data.type_op == "depot":
            if data.compte_dest is None or not compte_appartient(session, data.compte_dest, user["id"]):
                raise HTTPException(status_code=403, detail="Compte destinataire non autorisé")

        op = Operation(
            compte_source=data.compte_source,
            compte_dest=data.compte_dest,
            type_op=data.type_op,
            montant=data.montant,
            statut=STATUT_ATTENTE,
        )

        # Dépôt = appliqué tout de suite (pas de validation agent)
        if data.type_op == "depot":
            appliquer_solde(session, data.compte_dest, data.montant)
            op.statut = STATUT_VALIDEE

        session.add(op)
        session.commit()
        session.refresh(op)

    await publier_log("INFO", f"Opération {op.type_op} créée (id={op.id}, statut={op.statut})", user["id"])
    return op


# ---------------- Déclenché par l'AGENT (service-agent appelle ici) ----------------
@app.post("/operations/{op_id}/valider")
async def valider(op_id: int, user=Depends(get_current_user)):
    if user["role"] != "agent":
        raise HTTPException(status_code=403, detail="Réservé aux agents")
    with Session(engine) as session:
        op = session.get(Operation, op_id)
        if not op:
            raise HTTPException(status_code=404, detail="Opération introuvable")
        if op.statut != STATUT_ATTENTE:
            raise HTTPException(status_code=400, detail="Opération déjà traitée")

        # C'est ICI que l'argent bouge réellement
        if op.type_op == "retrait":
            appliquer_solde(session, op.compte_source, -op.montant)
        elif op.type_op == "virement":
            appliquer_solde(session, op.compte_source, -op.montant)
            appliquer_solde(session, op.compte_dest, +op.montant)

        op.statut = STATUT_VALIDEE
        op.traite_par = user["id"]
        session.add(op)
        session.commit()
        session.refresh(op)

    await publier_log("INFO", f"Opération {op_id} validée par agent {user['id']}", user["id"])
    return op


@app.post("/operations/{op_id}/refuser")
async def refuser(op_id: int, user=Depends(get_current_user)):
    if user["role"] != "agent":
        raise HTTPException(status_code=403, detail="Réservé aux agents")
    with Session(engine) as session:
        op = session.get(Operation, op_id)
        if not op:
            raise HTTPException(status_code=404, detail="Opération introuvable")
        if op.statut != STATUT_ATTENTE:
            raise HTTPException(status_code=400, detail="Opération déjà traitée")
        op.statut = STATUT_REFUSEE
        op.traite_par = user["id"]
        session.add(op)
        session.commit()
        session.refresh(op)
    await publier_log("INFO", f"Opération {op_id} refusée par agent {user['id']}", user["id"])
    return op
