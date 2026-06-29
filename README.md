# Saé-401Application_de_gestion_bancaire
Projet SAÉ 4.DEVCLOUD.01 - application bancaire découpée en micro-services. Un client peut consulter ses comptes et faire des opérations (dépôt, retrait,virement) ; un agent valide ou refuse les retraits et virements. L'authentification repose sur des jetons JWT et les actions sont journalisées via un bus de messages NATS.
## Architecture
L'application est composée de 4 services et de 2 briques d'infrastructure, le tout orchestré par Docker Compose.
| Service | Rôle | Port | Documentation (Swagger) |
|---|---|---|---|
| `service-authentication` | Utilisateurs, connexion, jetons JWT, rôles | 8000 | http://localhost:8000/docs |
| `service-client` | Comptes, opérations, interface web client | 8001 | http://localhost:8001/docs |
| `service-agent` | Validation/refus des opérations par l'agent | 8004 | http://localhost:8004/docs |
| `service-logs` | Collecte et consultation des journaux | 8005 | http://localhost:8005/docs |
| `MySQL` | Base de données (auth_db, bank_db, logs_db) | 3306 | — |
| `NATS` | Bus de messages pour les logs | 4222 | — |

**Important** : tous les services tournent dans des conteneurs Docker. Il n'y a donc rien à installer en Python (ni MySQL, ni les bibliothèques) sur la machine : Docker construit tout automatiquement. Les seuls prérequis à installer sont Git et Docker.

## 1. Prérequis : installer Git et Docker
Les commandes ci-dessous sont prévues pour **Debian / Ubuntu**.
### Git

```bash
sudo apt-get update
sudo apt-get install -y git
```

### Docker et Docker Compose

Méthode officielle (recommandée), qui installe Docker Engine **et** le plugin `docker compose` :

```bash
# Outils de base
sudo apt-get update
sudo apt-get install -y ca-certificates curl

# Ajouter la clé GPG officielle de Docker
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Ajouter le dépôt Docker aux sources APT
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Installer Docker + le plugin Compose
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```
> Sur **Ubuntu**, remplacer `debian` par `ubuntu` dans les deux URL de l'étape 2 et 3.

Pour utiliser Docker **sans `sudo`**, ajouter votre utilisateur au groupe `docker`, puis se déconnecter/reconnecter :
```bash
sudo usermod -aG docker $USER
```

### Vérifier l'installation

```bash
docker --version
docker compose version
```

Les deux commandes doivent afficher un numéro de version.

---

## 2. Récupérer le projet

```bash
git clone https://github.com/LionelG-hub/Sae-401Application_de_gestion_bancaire.git
cd Sae-401Application_de_gestion_bancaire
```

---
## 3. Créer le fichier `.env`

Le projet a besoin d'un fichier `.env` à la racine (à côté de `docker-compose.yml`) qui contient les identifiants de la base et la clé secrète des jetons.

 **Ce fichier n'est volontairement pas versionné** (il est dans le `.gitignore`, car il contient des mots de passe). Il faut donc le **créer à la main**. Depuis le dossier du projet, copier-coller ce bloc dans le terminal :

```bash
cat > .env << 'EOF'
MYSQL_ROOT_PASSWORD=root
MYSQL_USER=DBA
MYSQL_PASSWORD=acess123
MYSQL_DATABASE=bank_db
SECRET_KEY=cle_secrete_bancaire_sae401
EOF
```

Vérifier qu'il est bien présent :

```bash
ls -a        # le fichier .env doit apparaître
cat .env
```

---

## 4. Lancer l'application

```bash
docker compose up --build
```

La première fois, la construction des images prend une à deux minutes. Patienter
ensuite ~30 secondes que MySQL finisse de s'initialiser (les services affichent
« Connexion MySQL réussie » dans les logs).

Pour lancer en arrière-plan (sans bloquer le terminal), ajouter `-d` :

```bash
docker compose up --build -d
```

Vérifier que les 6 conteneurs sont bien démarrés (tous en `Up`) :

```bash
docker compose ps
```

---

## 5. Utilisation

### Interface web client

Ouvrir dans un navigateur :

```
http://localhost:8001/client/login
```

### Scénario de démonstration (de bout en bout)

1. **Créer les utilisateurs.** Aller sur http://localhost:8000/register-page et créer
   deux comptes : un **agent** (rôle « Agent bancaire ») et un **client** (rôle « Client »).
2. **Se connecter en client** sur http://localhost:8001/client/login.
3. **Ouvrir un compte** depuis le tableau de bord (bouton « Ouvrir un compte »).
4. **Faire un dépôt** : il est appliqué immédiatement, le solde augmente.
5. **Faire un retrait** : il passe « en attente » (le solde ne bouge pas encore).
6. **Se connecter en agent** (Swagger http://localhost:8004/docs, ou l'interface agent)
   et **valider** le retrait.
7. De retour sur le tableau de bord client, le solde a été mis à jour.

> Astuce : pour tester deux utilisateurs sans confusion, utiliser une **fenêtre de navigation privée** par utilisateur, ou cliquer sur « Déconnexion » entre les deux.

---

## 6. Commandes utiles

```bash
# Voir l'état des conteneurs
docker compose ps

# Suivre les logs en direct (Ctrl+C pour quitter l'affichage)
docker compose logs -f
docker compose logs -f service-client    # un seul service

# Arrêter l'application (conserve les données)
docker compose down

# Tout arrêter ET réinitialiser la base de données (repart de zéro)
docker compose down -v

# Reconstruire après une modification du code
docker compose up --build
```

---

## 7. Dépannage

- **Des avertissements `WARN ... is not set` au démarrage** → le fichier `.env` est absent ou n'est pas dans le même dossier que `docker-compose.yml`. Recréer le `.env` (étape 3) puis relancer.
- **Un service reste en `Restarting` ou `Exited`** → regarder ses logs avec `docker compose logs <nom-du-service>` (ex. `service-client`).
- **Après une modification de la structure de la base** (ajout d'une colonne) → MySQL ne met pas à jour une table existante automatiquement. Repartir d'une base propre : `docker compose down -v` puis `docker compose up --build`.
- **`docker compose` introuvable** → le plugin Compose n'est pas installé ; reprendre l'étape 1 (paquet `docker-compose-plugin`).
