from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv

# Charger les variables de configuration
load_dotenv()

# Clé secrète pour signer les tokens JWT
# Cette clé doit rester secrète, personne ne doit la connaître
SECRET_KEY = os.getenv("SECRET_KEY", "cle_secrete_bancaire_2024")

# Algorithme utilisé pour créer le token JWT
ALGORITHM = "HS256"

# Durée de validité du token — 30 minutes
# Après 30 minutes le token expire et l'utilisateur doit se reconnecter
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Contexte pour hasher et vérifier les mots de passe
# bcrypt est l'algorithme de hashage le plus sécurisé
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Indique à FastAPI où trouver le token dans les requêtes
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def verifier_mot_de_passe(mot_de_passe_brut, mot_de_passe_hashe):
    # Vérifie si le mot de passe tapé correspond au hash stocké en base
    return pwd_context.verify(mot_de_passe_brut, mot_de_passe_hashe)

def hasher_mot_de_passe(mot_de_passe):
    # Transforme le mot de passe en hash avant de le stocker
    return pwd_context.hash(mot_de_passe)

def creer_token_jwt(data: dict):
    # Copie les données à mettre dans le token
    donnees = data.copy()
    
    # Calcule la date d'expiration du token
    expiration = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Ajoute la date d'expiration dans le token
    donnees.update({"exp": expiration})
    
    # Crée et retourne le token JWT signé avec la clé secrète
    token = jwt.encode(donnees, SECRET_KEY, algorithm=ALGORITHM)
    return token

def verifier_token(token: str = Depends(oauth2_scheme)):
    # Erreur à retourner si le token est invalide
    erreur = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token invalide ou expiré",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Décode le token avec la clé secrète
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Récupère l'email et le rôle depuis le token
        email = payload.get("sub")
        role = payload.get("role")
        
        # Si pas d'email dans le token, il est invalide
        if email is None:
            raise erreur
            
        return {"email": email, "role": role}
        
    except JWTError:
        # Si le token est corrompu ou expiré on lève une erreur
        raise erreur

def verifier_role_client(token_data = Depends(verifier_token)):
    # Vérifie que l'utilisateur connecté est bien un client
    if token_data["role"] != "client":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux clients"
        )
    return token_data

def verifier_role_agent(token_data = Depends(verifier_token)):
    # Vérifie que l'utilisateur connecté est bien un agent bancaire
    if token_data["role"] != "agent":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux agents bancaires"
        )
    return token_data
