# Saé-401Application_de_gestion_bancaire
Projet SAÉ 4.DEVCLOUD.01 — application bancaire découpée en micro-services. Un client peut consulter ses comptes et faire des opérations (dépôt, retrait,virement) ; un agent valide ou refuse les retraits et virements. L'authentification repose sur des jetons JWT et les actions sont journalisées via un bus de messages NATS.
# Architecture
L'application est composée de 4 services et de 2 briques d'infrastructure, le tout orchestré par Docker Compose.
