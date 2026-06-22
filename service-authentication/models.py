# Modèle de la base de données
# Ce fichier définit la structure de la table utilisateurs dans MySQL
from sqlalchemy import Column, Integer, String, Enum
from database import Base
import enum

# Définition des rôles possibles dans l'application
# Un utilisateur peut être soit client soit agent bancaire, rien d'autre
class RoleEnum(enum.Enum):
    client = "client"
    agent = "agent"

# Modèle de la table utilisateurs
# Chaque attribut correspond à une colonne dans MySQL
class Utilisateur(Base):
    __tablename__ = "utilisateurs"

    # Identifiant unique de chaque utilisateur, s'incrémente automatiquement
    id = Column(Integer, primary_key=True, index=True)
    
    # Email de l'utilisateur, doit être unique — deux utilisateurs ne peuvent pas avoir le même email
    email = Column(String(255), unique=True, index=True, nullable=False)
    
    # Mot de passe hashé — on ne stocke jamais le vrai mot de passe
    mot_de_passe = Column(String(255), nullable=False)
    
    # Rôle de l'utilisateur — soit client soit agent bancaire
    role = Column(Enum(RoleEnum), nullable=False)