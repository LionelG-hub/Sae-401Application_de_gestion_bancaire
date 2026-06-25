from pydantic import BaseModel, EmailStr
from enum import Enum

class RoleEnum(str, Enum):
    client = "client"
    agent = "agent"

# Données nécessaires pour créer un compte
class UtilisateurCreate(BaseModel):
    email: EmailStr
    mot_de_passe: str
    role: RoleEnum

# Données nécessaires pour se connecter
class UtilisateurLogin(BaseModel):
    email: EmailStr
    mot_de_passe: str

# Réponse renvoyée après inscription ou consultation — sans le mot de passe
class UtilisateurResponse(BaseModel):
    id: int
    email: EmailStr
    role: RoleEnum

    class Config:
        from_attributes = True

# Token JWT renvoyé après connexion réussie
class Token(BaseModel):
    access_token: str
    token_type: str
    role: str

# Données extraites du token JWT
class TokenData(BaseModel):
    email: str | None = None
    role: str | None = None