# Utilise Python 3.12 comme base
FROM python:3.12-slim

# Définit le dossier de travail dans le conteneur
WORKDIR /app

# Copie le fichier des dépendances dans le conteneur
COPY requirements.txt .

# Installe toutes les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copie tous les fichiers du service dans le conteneur
COPY . .

# Expose le port 8000 pour que le service soit accessible
EXPOSE 8000

# Commande qui lance le service au démarrage du conteneur
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
