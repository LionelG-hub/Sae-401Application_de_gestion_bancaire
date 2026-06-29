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

Méthode officielle (recommandée), qui installe Docker Engine **et** le plugin
`docker compose` :

```bash
# 1. Outils de base
sudo apt-get update
sudo apt-get install -y ca-certificates curl
