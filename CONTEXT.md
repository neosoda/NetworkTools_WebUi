# PROJECT CONTEXT

## Purpose
- Plateforme d'automatisation centralisée pour la gestion, le backup et l'audit de parcs réseau hétérogènes.
- Permet de fiabiliser les opérations critiques sur des équipements Cisco, Allied Telesis et Aruba/HP via une interface Web unifiée.
- Réduit les erreurs humaines lors des changements de configuration de masse.

## Non-Goals
- Ne remplace pas un outil de monitoring temps réel (NMS) type Zabbix ou PRTG.
- N'est pas un gestionnaire de tickets (ITSM).
- Pas de support pour les équipements grand public ou non-standard SSH.

## Target Environment
- **Runtime** : Python 3.9+ sur Windows (environnement primaire constaté) ou Linux.
- **Exécution** : On-premise, accès réseau direct (management VLAN).
- **Contraintes** : Latence réseau variable, sessions SSH parfois instables ou restrictives (Mocana).

## Architecture Overview
- **Backend** : FastAPI (API REST), Paramiko (SSH), SQLite (Persistance), APScheduler (Tâches).
- **Frontend** : Vanilla HTML/JS/CSS (Aesthetic Cyber-UI). Zéro framework lourd (React/Vue/Angular) par choix de simplicité et de maintenabilité.
- **Patterns** : Gestionnaires spécialisés par domaine (`managers/`), API segmentée par ressource.
- **Complexité** : Logique de capture SSH volontairement complexe (regex, gestion pagination, nettoyage ANSI) pour absorber les spécificités constructeurs.

## Constraints (NON NEGOTIABLE)
- **Fiabilité Backup** : Un backup doit être intégral ou échouer. Jamais de backup partiel sans flag d'erreur.
- **Sanitisation** : Tout contenu extrait des bannières doit être nettoyé avant écriture disque (Caractères Windows, ANSI).
- **Panic Stop** : Le bouton "Stop All Tasks" doit interrompre physiquement tous les threads d'exécution en cours.

## Coding Rules
- **Style** : Python PEP8. Code dense mais documenté par blocs.
- **Patterns** : Utilisation systématique de `try...except...finally` pour fermer les sessions SSH.
- **Erreurs** : Erreurs explicites dans les logs (`ERROR:root:`), tags visuels (`success`, `warning`, `danger`) pour le frontend.
- **IO** : Encodage `utf-8` strict pour toutes les lectures/écritures de fichiers.

## Dependency Policy
- **Autorisées** : `fastapi`, `uvicorn`, `paramiko`, `apscheduler`, `jinja2`.
- **Interdites** : Frameworks JS lourds, ORM complexes (SQLAlchemy interdit ici pour garder le SQL pur et lisible).
- **Ajout** : Validation requise du Tech Lead pour toute nouvelle lib externe affectant le core SSH ou la base de données.

## Security Model
- **Actifs** : Identifiants réseau (Username/Password), fichiers de configurations (backups).
- **Mesures** : Désactivation du SSH Agent et du `look_for_keys` pour éviter les fuites d'auth.
- **Hors périmètre** : Protection contre les attaques par déni de service (DoS) sur l'interface Web interne.

## AI USAGE RULES
- **Droits IA** : Correction de bugs locaux, optimisation de regex, refactoring de composants UI isolés.
- **Validation Requise** : Toute modification de la logique de connexion SSH (`connect()`) ou du schéma de base de données.
- **Interdit** : Refactors globaux sans plan d'implémentation validé. Changements silencieux de ports ou de protocoles.
- **Obligation** : Signaler systématiquement les risques de régression sur les switchs Aruba/HP lors des modifications du `BackupManager`.

## Decision Log (Initial)
- **Vanilla JS vs React** → Raison : Maintenabilité long terme sans build-system complexe → Trade-off : Plus de code DOM manuel.
- **SQLite** → Raison : Portabilité immédiate et zéro installation serveur → Trade-off : Concurrence d'écriture limitée.
- **Paramiko Shell vs Exec** → Raison : Support des bannières interactives ("Press any key") → Trade-off : Capture de sortie plus complexe à nettoyer.

## How to Extend Safely
- **Feature Réseau** : Ajouter les commandes dans le manager concerné (`managers/`) et exposer l'endpoint dans `server/api/`.
- **Nouveau Constructeur** : Ne pas recréer de manager, étendre la logique de détection dans `BackupManager.wait_and_interact`.
- **Sensible** : Ne jamais modifier `scheduler.py` ou `ssh_manager.py` sans vérifier l'impact sur le `stop_flag`.
