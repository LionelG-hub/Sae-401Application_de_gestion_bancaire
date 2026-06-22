# Schémas de validation des données
# Ce fichier définit la structure des données qui entrent et sortent de l'API
# Pydantic vérifie automatiquement que les données sont correctes avant de les traiter
from pydantic import BaseModel, EmailStr
from enum import Enum

# Rôles disponibles dans l'application
class RoleEnum(str, Enum):
    client = "client"
    agent = "agent"

# Schéma pour l'inscription d'un nouvel utilisateur
# Contient les données obligatoires pour créer un compte
class UtilisateurCreate(BaseModel):
    email: EmailStr        # Email valide obligatoire
    mot_de_passe: str      # Mot de passe obligatoire
    role: RoleEnum         # Rôle obligatoire — client ou agent

# Schéma pour la connexion d'un utilisateur
# On a besoin uniquement de l'email et du mot de passe
class UtilisateurLogin(BaseModel):
    email: EmailStr        # Email de l'utilisateur
    mot_de_passe: str      # Mot de passe de l'utilisateur

# Schéma pour la réponse renvoyée à l'utilisateur
# On ne renvoie jamais le mot de passe — seulement l'id, l'email et le rôle
class UtilisateurResponse(BaseModel):
    id: int
    email: EmailStr
    role: RoleEnum

    class Config:
        # Permet à Pydantic de lire les données depuis un objet SQLAlchemy
        from_attributes = True

# Schéma du token JWT renvoyé après une connexion réussie
class Token(BaseModel):
    access_token: str      # Le token JWT
    token_type: str        # Le type du token — toujours "bearer"

# Schéma des données contenues dans le token JWT
class TokenData(BaseModel):
    email: str | None = None    # Email de l'utilisateur connecté
    role: str | None = None     # Rôle de l'utilisateur