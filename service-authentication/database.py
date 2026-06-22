# Connexion à la base de données MySQL
# Ce fichier est le point central de connexion entre notre service et MySQL
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Charge les variables du fichier .env
# Les informations sensibles comme le mot de passe ne sont jamais écrites directement dans le code
load_dotenv()

# Adresse complète de connexion à MySQL
# Format : mysql+pymysql://utilisateur:motdepasse@serveur:port/nom_base
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:root@db:3306/auth_db")

# Crée le moteur de connexion à MySQL
# C'est lui qui établit vraiment la connexion avec la base de données
engine = create_engine(DATABASE_URL)

# Crée une fabrique de sessions
# Chaque requête API ouvre une session et la ferme après
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Classe de base pour tous nos modèles de base de données
# Tous les modèles héritent de cette classe
Base = declarative_base()

def get_db():
    # Fonction qui fournit une session à chaque endpoint qui en a besoin
    # La session est automatiquement fermée après chaque requête
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()