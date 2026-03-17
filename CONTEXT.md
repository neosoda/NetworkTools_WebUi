# PROJECT CONTEXT
## Purpose
Le projet NetworkTools-V3 est un outil de gestion réseau permettant l’analyse, la sauvegarde et la restauration des configurations réseau. Il vise à simplifier les tâches administratives liées aux réseaux en fournissant une interface utilisateur intuitive et des fonctionnalités robustes.

## Non-Goals
- Le projet ne gère pas les configurations de sécurité avancées comme le chiffrement SSL.
- Les fonctionnalités d’analyse réseau en temps réel ne sont pas incluses dans cette version initiale.
- L’intégration avec des systèmes de gestion de configuration externes (comme Ansible) n’est pas prévue.

## Target Environment
- **OS / Runtime**: Windows 10+, Linux, macOS.
- **Contraintes d’exécution**: Latence maximale de 500ms par requête, mémoire minimale de 2GB, sécurité forte avec authentification multi-facteurs.
- **Environnement cible**: Déploiement en cloud (AWS) et sur-premises.

## Architecture Overview
- **Stack technique**: Python 3.9, FastAPI pour le backend, Vanilla JS pour le frontend.
- **Patterns architecturaux assumés**: Router/Manager pour le backend, Single Page Application (SPA) pour le frontend.
- **Ce qui est volontairement simple**: Interface utilisateur basique.
- **Ce qui est volontairement complexe**: Gestion des configurations réseau et sauvegardes.

## Constraints (NON NEGOTIABLE)
- Utilisation de FastAPI pour le backend.
- Utilisation de Vanilla JavaScript pour le frontend.
- Authentification multi-facteurs obligatoire.

## Coding Rules
- **Style de code attendu**: PEP 8 pour Python, ESLint pour JavaScript.
- **Patterns préférés**: MVC pour le backend, composants pour le frontend.
- **Patterns interdits**: Flask-SocketIO.
- **Gestion des erreurs**: Gestion des erreurs via exceptions personnalisées.
- **Logging / observabilité**: Logs JSON envoyés à ELK Stack.

## Dependency Policy
- **Dépendances autorisées**: Listées dans `requirements.txt`.
- **Dépendances interdites**: Flask-SocketIO.
- **Politique d’ajout**: Ajout de dépendances nécessite une validation manuelle et doit être documenté dans `requirements.txt`.

## Security Model
- **Modèle de menace supposé**: Attaques par injection SQL, accès non autorisé aux configurations réseau.
- **Actifs sensibles**: Configurations réseau, données d’authentification.
- **Hypothèses de sécurité**: Utilisation de mots de passe hachés et salés.
- **Mesures minimales obligatoires**: Authentification multi-facteurs, chiffrement des données sensibles.
- **Ce qui est volontairement NON traité**: Protection contre les attaques DDoS.

## AI USAGE RULES
- **Ce que les IA ont le droit de faire sans validation humaine**: Corrections mineures de bugs, améliorations mineures de performances.
- **Ce qui nécessite validation explicite**: Ajout de nouvelles fonctionnalités, modifications majeures des patterns architecturaux.
- **Ce qui est strictement interdit**: Suppression de fonctionnalités existantes, changements globaux de l’architecture.
- **Interdiction des changements silencieux**: Toutes les modifications doivent être documentées et approuvées par un humain.
- **Interdiction des refactors globaux déguisés**: Refactorings doivent respecter la structure existante et ne pas introduire de nouvelles fonctionnalités.
- **Obligation de signaler les hypothèses et les risques**: Toutes les hypothèses et risques potentiels doivent être documentés dans `CONTEXT.md`.

## Decision Log (Initial)
- **Décision clé**: Utilisation de FastAPI pour le backend → Raison: Performance et typage Python moderne.
- **Dette technique consciente**: Aucune.

## How to Extend Safely
- **Où ajouter du code**: Modules `server/managers/` et `web/js/`.
- **Où NE PAS toucher**: Fichiers de configuration (`config.json`, `installer_script.iss`).
- **Règles pour ajouter une feature sans casser l’existant**: Ajout de nouveaux modules dans les dossiers existants, respect des patterns architecturaux.
- **Zones sensibles nécessitant prudence maximale**: Fichiers de configuration et fichiers contenant des actifs sensibles.
