# NetworkTools WebUI (V3 Pro)

Outil complet de gestion, backup et audit réseau avec interface Web moderne.

## Fonctionnalités
- **Backup Configuration** : Sauvegarde automatique (Cisco, Allied Telesis, Aruba/HP) avec nettoyage ANSI et gestion de la pagination.
- **SSH Mass Action** : Exécution de commandes en série sur plusieurs équipements.
- **Audit de Conformité** : Vérification des règles de sécurité et configuration sur l'ensemble du parc.
- **Comparateur de Config** : Diff visuel avec support Drag & Drop.
- **Planificateur** : Programmation des tâches avec calendrier visuel.
- **Inventaire** : Scan réseau et gestion de base de données SQLite.

## Installation
1. Configurer un environnement Python 3.9+
2. Installer les dépendances : `pip install -r requirements.txt`
3. Lancer l'application : `python run.py`
4. Accéder à l'interface : `http://localhost:8000`

## Architecture
- **Backend** : FastAPI + Paramiko (SSH) + SQLite.
- **Frontend** : Vanilla JS + CSS moderne (Aesthetic Cyber-UI).

---
*Réalisé pour la Fiabilisation des Connexions SSH et Multi-Vendeurs.*
