from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
import models
import schemas
import auth
from database import engine, get_db
import nats
import json
from datetime import datetime
import time

# Attend que MySQL soit prêt avant de démarrer
def attendre_mysql(max_tentatives=10):
    for tentative in range(max_tentatives):
        try:
            models.Base.metadata.create_all(bind=engine)
            print("Connexion MySQL réussie")
            return
        except Exception:
            print(f"MySQL pas encore prêt, tentative {tentative + 1}/{max_tentatives}")
            time.sleep(3)
    raise Exception("Impossible de se connecter à MySQL")

# Lance l'attente et crée les tables
attendre_mysql()

# Initialise l'application FastAPI
app = FastAPI(title="Service Authentification")

# Configure les templates HTML
templates = Jinja2Templates(directory="templates")

# Connexion à NATS pour publier les logs
async def publier_log(sujet: str, message: dict):
    try:
        nc = await nats.connect("nats://nats:4222")
        await nc.publish(sujet, json.dumps(message).encode())
        await nc.close()
    except Exception:
        pass

@app.post("/register", response_model=schemas.UtilisateurResponse)
async def inscription(utilisateur: schemas.UtilisateurCreate, db: Session = Depends(get_db)):
    # Vérifie si l'email est déjà utilisé
    existant = db.query(models.Utilisateur).filter(
        models.Utilisateur.email == utilisateur.email
    ).first()

    if existant:
        raise HTTPException(
            status_code=400,
            detail="Cet email est déjà utilisé"
        )

    # Hashe le mot de passe avant de le stocker
    mot_de_passe_hashe = auth.hasher_mot_de_passe(utilisateur.mot_de_passe)

    # Crée le nouvel utilisateur en base de données
    nouvel_utilisateur = models.Utilisateur(
        email=utilisateur.email,
        mot_de_passe=mot_de_passe_hashe,
        role=utilisateur.role
    )

    db.add(nouvel_utilisateur)
    db.commit()
    db.refresh(nouvel_utilisateur)

    return nouvel_utilisateur

@app.post("/login", response_model=schemas.Token)
async def connexion(utilisateur: schemas.UtilisateurLogin, db: Session = Depends(get_db)):
    # Cherche l'utilisateur dans la base de données
    user = db.query(models.Utilisateur).filter(
        models.Utilisateur.email == utilisateur.email
    ).first()

    # Vérifie que l'utilisateur existe et que le mot de passe est correct
    if not user or not auth.verifier_mot_de_passe(utilisateur.mot_de_passe, user.mot_de_passe):

        # Publie un log d'échec dans NATS
        await publier_log("auth.echec", {
            "email": utilisateur.email,
            "message": "Tentative de connexion échouée",
            "date": datetime.utcnow().isoformat()
        })

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect"
        )

    # Crée le token JWT avec l'email et le rôle
    token = auth.creer_token_jwt({
        "sub": user.email,
        "role": user.role.value
    })

    # Publie un log de connexion réussie dans NATS
    await publier_log("auth.connexion", {
        "email": user.email,
        "role": user.role.value,
        "message": "Connexion réussie",
        "date": datetime.utcnow().isoformat()
    })

    return {"access_token": token, "token_type": "bearer", "role": user.role.value}

@app.get("/verify-token")
async def verifier_token(token_data = Depends(auth.verifier_token)):
    # Vérifie si le token est valide et retourne les informations de l'utilisateur
    return {
        "email": token_data["email"],
        "role": token_data["role"]
    }

@app.get("/me", response_model=schemas.UtilisateurResponse)
async def mon_profil(token_data = Depends(auth.verifier_token), db: Session = Depends(get_db)):
    # Retourne les informations de l'utilisateur connecté
    user = db.query(models.Utilisateur).filter(
        models.Utilisateur.email == token_data["email"]
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Utilisateur non trouvé"
        )

    return user

@app.get("/clients")
async def get_clients(db: Session = Depends(get_db)):
    # Retourne tous les utilisateurs avec le rôle client
    clients = db.query(models.Utilisateur).filter(
        models.Utilisateur.role == models.RoleEnum.client
    ).all()
    return clients

@app.get("/agents")
async def get_agents(db: Session = Depends(get_db)):
    # Retourne tous les utilisateurs avec le rôle agent
    agents = db.query(models.Utilisateur).filter(
        models.Utilisateur.role == models.RoleEnum.agent
    ).all()
    return agents

@app.get("/login-page", response_class=HTMLResponse)
async def page_login(request: Request):
    # Affiche la page de connexion client
    return templates.TemplateResponse(request=request, name="login.html")

@app.get("/login-agent-page", response_class=HTMLResponse)
async def page_login_agent(request: Request):
    # Affiche la page de connexion agent
    return templates.TemplateResponse(request=request, name="login_agent.html")

@app.get("/register-page", response_class=HTMLResponse)
async def page_register(request: Request):
    # Affiche la page d'inscription
    return templates.TemplateResponse(request=request, name="register.html")