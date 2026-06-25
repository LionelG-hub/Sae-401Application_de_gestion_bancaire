-- Création des bases de données pour chaque service
CREATE DATABASE IF NOT EXISTS auth_db;
CREATE DATABASE IF NOT EXISTS logs_db;

-- Donne tous les droits à DBA sur toutes les bases
GRANT ALL PRIVILEGES ON auth_db.* TO 'DBA'@'%';
GRANT ALL PRIVILEGES ON bank_db.* TO 'DBA'@'%';
GRANT ALL PRIVILEGES ON logs_db.* TO 'DBA'@'%';
FLUSH PRIVILEGES;