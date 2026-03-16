# Audit Technique & Sécurité — NetworkTools_WebUi V3

**Date** : 2026-03-16
**Auditeur** : Staff Software Engineer Python / Senior AppSec Auditor
**Périmètre** : Totalité du dépôt (`server/`, `web/`, `tests/`, configs)
**Lignes analysées** : ~4 150 (2 358 Python + 1 367 JS + 428 CSS)

---

## 1. Tableau de Santé Global

| Domaine | Score /10 | Analyse Synthétique |
| :--- | :---: | :--- |
| **Architecture** | 4/10 | Pattern Manager correct mais couplage fort, état global mutable, pas d'injection de dépendances, code dupliqué entre managers, pas de couche service. |
| **Qualité Code** | 3/10 | Aucun type hint sur ~60% des fonctions, `except: pass` multiples, imports anti-pattern (`__import__`), fonctions >40 lignes, zéro docstring PEP 257. |
| **Sécurité** | 2/10 | **CRITIQUE** — Aucune authentification API, lecture de fichiers arbitraires (Path Traversal), credentials en clair, AutoAddPolicy SSH, XSS via innerHTML, pas de CORS/CSP/rate-limiting. |
| **Tests** | 2/10 | 12 tests pour ~30 endpoints et ~20 classes/fonctions. Aucun test d'intégration, aucun test de manager, aucun test de base de données. Couverture estimée <5%. |
| **Documentation** | 4/10 | README correct mais incomplet (pas de section sécurité, pas de contribution guide, pas de changelog). Zéro docstring dans le code. Pas de `CONTRIBUTING.md`, pas de `SECURITY.md`. |

---

## 2. Matrice de Vulnérabilités & Bugs

### Sévérité : CRITIQUE

| Sévérité | Fichier / Fonction | Problème | Impact | Correction |
| :---: | :--- | :--- | :--- | :--- |
| **CRITIQUE** | `server/main.py` (global) | **Aucune authentification/autorisation sur l'ensemble de l'API** | N'importe qui sur le réseau peut exécuter des commandes SSH, scanner des réseaux, lire des configurations. Compromission totale de l'infrastructure réseau. | Implémenter un middleware d'authentification (JWT/OAuth2 via `fastapi.security`), ajouter du RBAC. |
| **CRITIQUE** | `server/api/diff.py:22-29` | **Path Traversal — Lecture de fichiers arbitraires** : `f1_path` et `f2_path` sont utilisés directement dans `os.path.exists()` et `open()` sans aucune validation. | Un attaquant peut lire n'importe quel fichier du système : `/etc/shadow`, clés SSH, configs DB, etc. | Valider et résoudre les chemins comme `_safe_download_path()`, restreindre à un répertoire autorisé. |
| **CRITIQUE** | `server/api/scan.py:28` | **Aucune validation de `body: dict`** pour `start_scan`. Le paramètre `network` est passé directement à `nmap.scan()`. | Injection potentielle d'arguments nmap via le champ `network`. Reconnaissance réseau non autorisée. | Utiliser un modèle Pydantic avec validation `ipaddress.ip_network()`. |
| **CRITIQUE** | `server/api/backup.py:15` | **Aucune validation de `body: dict`** pour `start_backup`. IPs, username, password non validés. | Exécution SSH vers des hôtes arbitraires avec des credentials fournis par l'attaquant. | Modèle Pydantic avec validation des IPs et contraintes sur les credentials. |
| **CRITIQUE** | `server/managers/ssh_manager.py:25` | **`paramiko.AutoAddPolicy()`** — Accepte n'importe quelle clé hôte SSH sans vérification. | Attaque Man-in-the-Middle : un attaquant peut intercepter toutes les connexions SSH et capturer les credentials. | Utiliser `RejectPolicy` ou `WarningPolicy` avec un fichier `known_hosts` géré. |
| **CRITIQUE** | `config.json:3-5` | **SNMP community strings en clair** (`"public"`, `"TICE"`) dans un fichier versionné. | Exposition des credentials SNMP dans le dépôt Git. Accès lecture/écriture aux équipements réseau. | Variables d'environnement ou vault (HashiCorp Vault, AWS Secrets Manager). Ne jamais versionner de secrets. |

### Sévérité : HAUTE

| Sévérité | Fichier / Fonction | Problème | Impact | Correction |
| :---: | :--- | :--- | :--- | :--- |
| **HAUTE** | `web/js/app.js:177-179` | **XSS via `innerHTML`** : les données de l'API (noms d'équipements, modèles, IPs) sont injectées directement dans le DOM sans échappement. | Un nom SNMP malicieux (`<img onerror=alert(1)>`) exécute du JavaScript arbitraire dans le navigateur de l'administrateur. | Utiliser `textContent` ou une fonction d'échappement HTML. |
| **HAUTE** | `server/main.py` (global) | **Aucun middleware CORS** configuré. | Toute page web peut faire des requêtes cross-origin vers l'API, permettant le CSRF. | Ajouter `CORSMiddleware` avec une whitelist d'origines stricte. |
| **HAUTE** | `server/api/scheduler_api.py:17` | **Aucune validation du `cron_expr`** ni du `task_type`** | Un attaquant peut injecter des expressions cron malformées ou des types de tâches non prévus. | Valider le format cron avec regex, whitelist des `task_type` autorisés. |
| **HAUTE** | `server/api/audit.py:28` | **`body: dict` non validé** — mêmes IPs/credentials non contraints que backup. | Connexions SSH vers des cibles arbitraires. | Modèle Pydantic. |
| **HAUTE** | `server/api/diff.py:58-59` | **Écriture de fichier dans le CWD** (`diff_report.html`) sans chemin sécurisé. | Écrasement de fichiers arbitraires si le CWD est manipulé. Race condition possible. | Écrire dans `get_app_data_dir()` avec un nom unique (UUID). |
| **HAUTE** | `server/managers/backup_manager.py:155` | **Fichiers de config écrits dans le CWD** avec un hostname extrait de la réponse SSH. | Même si le hostname est sanitisé (ligne 151), écriture hors du répertoire de données prévu. | Écrire dans `get_app_data_dir()` exclusivement. |
| **HAUTE** | `server/main.py` (global) | **Pas de HTTPS** — le serveur écoute en HTTP sur `127.0.0.1:8080`. | Credentials SSH/SNMP transmis en clair sur le réseau local. | Configurer TLS dans uvicorn ou utiliser un reverse proxy (nginx/caddy). |
| **HAUTE** | Tous les endpoints SSE | **Fuite mémoire** — Les dictionnaires `_active_scans`, `_active_backups`, `_active_ssh`, `_active_audits`, `_active_playbooks` ne sont jamais nettoyés si le client se déconnecte avant la fin. | Consommation mémoire croissante, déni de service à terme. | Implémenter un TTL avec nettoyage périodique, ou utiliser `weakref`. |

### Sévérité : MOYENNE

| Sévérité | Fichier / Fonction | Problème | Impact | Correction |
| :---: | :--- | :--- | :--- | :--- |
| **MOY** | `server/managers/snmp_manager.py:64,126,153,174,193` | **Bare `except:` / `except: pass`** — 5 occurrences de `except` nu ou `except: pass`. | Masque les erreurs, rend le debug impossible. Peut cacher des failles de sécurité. | Capturer les exceptions spécifiques, logger systématiquement. |
| **MOY** | `server/managers/snmp_manager.py:208-210` | **Double appel SNMP** — `fetch_oid()` est appelé 2 fois pour contact, name, et location (une fois pour le test `if`, une fois pour la valeur). | 6 requêtes SNMP supplémentaires par hôte, soit 30% de trafic réseau en plus. | Stocker le résultat dans une variable intermédiaire. |
| **MOY** | `server/api/scan.py:55`, `server/api/backup.py:36` | **Anti-pattern `__import__("queue")`** au lieu d'un import standard en tête de fichier. | Code obscur, non-idiomatique, difficile à maintenir. | `import queue` en haut du fichier. |
| **MOY** | `server/managers/audit_manager.py:30-52` | **Code dupliqué** — `consume_output()` est copié-collé de `ssh_manager.py:72-94`. | Maintenance double, bugs divergents. | Extraire dans un module utilitaire partagé. |
| **MOY** | `server/db/database.py` | **SQLite sans mode WAL** — accès concurrent depuis les threads de scan/backup/audit. | Erreurs `database is locked` sous charge. | Activer `PRAGMA journal_mode=WAL` et utiliser un pool de connexions. |
| **MOY** | `server/db/database.py:8-11` | **Connexions DB non gérées via context manager** — `get_db()` retourne une connexion brute sans `with`. | Fuites de connexions si une exception survient avant `conn.close()`. | Retourner un context manager (`contextlib.contextmanager`). |
| **MOY** | `server/main.py:98` | **Vérification `parents` incorrecte** — `app_data_dir not in path.parents` ne fonctionne pas si le fichier est directement dans `app_data_dir` (car `.parents` n'inclut pas le chemin lui-même pour un fichier à la racine). | Bypass potentiel de la restriction de téléchargement. | Utiliser `path.is_relative_to(app_data_dir)` (Python 3.9+). |
| **MOY** | `server/main.py:116-121` | **SPA catch-all AVANT `/health`** — La route `/{full_path:path}` capture `/health`. | L'endpoint de santé est inaccessible car intercepté par le catch-all. | Déplacer `/health` avant le catch-all ou utiliser un préfixe API. |
| **MOY** | `requirements.txt` | **`requests` manquant** — `alert_manager.py` importe `requests` mais il n'est pas dans les dépendances. | `ImportError` en production si requests n'est pas installé par hasard. | Ajouter `requests` au `requirements.txt`. |

### Sévérité : BASSE

| Sévérité | Fichier / Fonction | Problème | Impact | Correction |
| :---: | :--- | :--- | :--- | :--- |
| **BASSE** | `requirements.txt` | **Aucune version pinned** (sauf `pysnmp`, `pyasn1`). | Builds non reproductibles, risque de casse silencieuse. | Pinner toutes les versions, utiliser `pip-compile`. |
| **BASSE** | `requirements.txt:11` | **`ttkbootstrap`** — bibliothèque GUI Tkinter inutile dans une application web. | Dépendance inutile (~20MB), surface d'attaque élargie. | Supprimer. |
| **BASSE** | `requirements.txt:6` | **`pysnmp==4.4.12`** — projet déprécié et non maintenu depuis 2020. | Pas de correctifs de sécurité. | Migrer vers `pysnmplib` (fork maintenu). |
| **BASSE** | `server/managers/snmp_manager.py:73` | **`max_workers=50`** — 50 threads SNMP simultanés. | Surcharge réseau, risque de blacklist par les IPS/IDS. | Réduire à 10-20, rendre configurable. |
| **BASSE** | `server/managers/ssh_manager.py:49` | **`time.sleep(1)`** — délai fixe après chaque commande SSH. | Lenteur artificielle multipliée par le nombre de commandes × nombre d'hôtes. | Utiliser un polling basé sur `recv_ready()` avec timeout adaptatif. |
| **BASSE** | Global | **Aucun type hint** sur `load_config()`, `_build_rules()`, `_run_backup()`, `_run_audit()`, `_run_scan()`, toutes les méthodes de `SNMPManager`, `AuditManager`, `BackupManager`, `TopologyManager`, `DiffManager`. | Non-conformité PEP 484, pas de vérification statique possible. | Ajouter les annotations de type, configurer `mypy`. |
| **BASSE** | Global | **Zéro docstring PEP 257** — Aucune classe ni fonction publique n'a de docstring formatée. | Documentation auto-générée impossible, maintenance difficile. | Ajouter des docstrings Google-style ou NumPy-style. |

---

## 3. Refactoring "Gold Standard"

### Cible : `server/api/diff.py` — Le pire fichier du dépôt

**Problèmes** : Path Traversal critique, écriture dans le CWD, aucune validation d'entrée, aucun type hint, exception avalée, HTML construit par concaténation.

#### Code Original (72 lignes, 4 vulnérabilités)
```python
# AVANT — server/api/diff.py (VULNÉRABLE)
@router.post("/compare")
async def compare_files(body: dict):  # ← Aucune validation
    f1_path = body.get("file1", "")
    f2_path = body.get("file2", "")
    # ...
    if os.path.exists(f1_path) and os.path.isfile(f1_path):  # ← PATH TRAVERSAL
        with open(f1_path, "r", encoding="utf-8") as a:
            lines1 = a.readlines()
    # ...
    report_file = "diff_report.html"  # ← Écriture CWD
    with open(report_file, "w", encoding="utf-8") as out:
        out.write(clean_html)  # ← HTML par concaténation
```

#### Code Refactorisé (Gold Standard)

```python
"""Endpoint de comparaison de configurations réseau."""

from __future__ import annotations

import difflib
import uuid
from html import escape
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from server.utils.paths import get_app_data_dir

router = APIRouter()

# Répertoire sécurisé pour les rapports de diff
_REPORTS_DIR = Path(get_app_data_dir()).resolve()


class CompareRequest(BaseModel):
    """Modèle de validation pour les requêtes de comparaison."""

    text1: str = Field(default="", max_length=500_000, description="Contenu texte source 1")
    text2: str = Field(default="", max_length=500_000, description="Contenu texte source 2")
    label1: str = Field(default="Référence", max_length=128)
    label2: str = Field(default="Actuel", max_length=128)

    @field_validator("label1", "label2")
    @classmethod
    def sanitize_labels(cls, value: str) -> str:
        """Échappe les labels pour éviter l'injection HTML."""
        return escape(value.strip()) if value else "N/A"


def _generate_diff_html(
    lines1: list[str],
    lines2: list[str],
    label1: str,
    label2: str,
) -> str:
    """Génère un rapport HTML diff sécurisé avec labels échappés."""
    html_diff = difflib.HtmlDiff(wrapcolumn=90)
    raw_table = html_diff.make_table(
        lines1, lines2, label1, label2, context=True, numlines=5
    )
    return f"""<!DOCTYPE html>
<html lang="fr">
<head><meta charset="utf-8"><title>Diff — {label1} vs {label2}</title>
<style>
  body {{ font-family:'Segoe UI',sans-serif; font-size:13px; background:#0f1117; color:#e0e0e0; margin:20px; }}
  table.diff {{ border-collapse:collapse; width:100%; background:#1a1e2a; }}
  .diff th {{ background:#1e2436; padding:8px; color:#8899bb; }}
  .diff td {{ padding:4px 8px; font-family:'Consolas',monospace; white-space:pre-wrap; }}
  .diff_add {{ background:#1a3a1a; color:#4dff4d; }}
  .diff_chg {{ background:#3a3a1a; color:#ffdd44; }}
  .diff_sub {{ background:#3a1a1a; color:#ff4d4d; }}
</style></head>
<body><h2>Rapport de Comparaison</h2>
<p><b>Source 1:</b> {label1} | <b>Source 2:</b> {label2}</p>
{raw_table}</body></html>"""


@router.post("/compare")
async def compare_configs(body: CompareRequest) -> dict[str, Any]:
    """Compare deux configurations textuelles et retourne un diff unifié.

    Seules les comparaisons de texte sont autorisées (pas de chemins de fichiers)
    afin d'éliminer tout risque de Path Traversal.
    """
    if not body.text1.strip() and not body.text2.strip():
        raise HTTPException(status_code=400, detail="Au moins une source de données requise.")

    lines1 = [line + "\n" for line in body.text1.splitlines()]
    lines2 = [line + "\n" for line in body.text2.splitlines()]

    # Génération du rapport HTML dans un répertoire sécurisé
    report_name = f"diff_report_{uuid.uuid4().hex[:8]}.html"
    report_path = _REPORTS_DIR / report_name
    report_html = _generate_diff_html(lines1, lines2, body.label1, body.label2)
    report_path.write_text(report_html, encoding="utf-8")

    # Diff unifié pour l'affichage frontend
    text_diff = list(difflib.unified_diff(
        lines1, lines2, fromfile=body.label1, tofile=body.label2, lineterm=""
    ))

    return {
        "status": "success",
        "diff_lines": text_diff,
        "html_file": report_name,
        "added": sum(1 for l in text_diff if l.startswith("+") and not l.startswith("+++")),
        "removed": sum(1 for l in text_diff if l.startswith("-") and not l.startswith("---")),
    }
```

**Pourquoi cette version est supérieure :**
1. **Path Traversal éliminé** — Plus aucun chemin de fichier accepté en entrée, uniquement du texte.
2. **Validation Pydantic complète** — Taille max, sanitisation des labels, types stricts.
3. **Écriture sécurisée** — Rapport écrit dans `get_app_data_dir()` avec nom unique (UUID).
4. **Échappement HTML** — Labels échappés pour prévenir l'injection XSS.
5. **Type hints complets** — Conformité PEP 484, vérifiable par mypy.
6. **Docstrings** — Conformité PEP 257.
7. **Erreur explicite** — `HTTPException(400)` au lieu d'un retour silencieux.

---

## 4. Améliorations Structurelles

### 4.1 — Authentification & Autorisation
Ajouter une couche d'authentification **obligatoire** :
- `fastapi.security.OAuth2PasswordBearer` avec JWT tokens
- Middleware global qui protège tous les endpoints `/api/*`
- RBAC : rôles `admin` (SSH/backup), `auditor` (lecture seule), `viewer` (dashboard)
- Rate limiting via `slowapi` ou middleware custom

### 4.2 — Refactoring en Package avec Couche Service
```
server/
├── auth/              # JWT, RBAC, middleware
│   ├── middleware.py
│   └── models.py
├── services/          # Logique métier (entre API et Managers)
│   ├── scan_service.py
│   ├── backup_service.py
│   └── audit_service.py
├── managers/          # Opérations bas niveau (SSH, SNMP)
├── api/               # Routes HTTP (validation + sérialisation uniquement)
├── schemas/           # Modèles Pydantic (entrée/sortie)
├── db/
│   ├── models.py      # SQLAlchemy ORM models
│   ├── repository.py  # Data access layer
│   └── session.py     # Session factory avec context manager
└── core/
    ├── config.py      # Pydantic Settings (env vars)
    ├── security.py    # Hashing, encryption
    └── exceptions.py  # Exceptions métier custom
```

### 4.3 — Gestion des Secrets
- Remplacer `config.json` par `pydantic-settings` avec variables d'environnement
- Fichier `.env` (gitignored) pour le développement local
- Support de vaults pour la production
- Chiffrement at-rest des credentials SNMP/SSH stockés

### 4.4 — Base de Données
- Migrer vers SQLAlchemy ORM avec modèles déclaratifs
- Context manager pour les sessions (`async with get_session() as session:`)
- Mode WAL activé par défaut pour SQLite
- Migrations avec Alembic

### 4.5 — Extraction du Code Dupliqué
- `consume_output()` : extraire dans `server/utils/ssh_utils.py`
- `load_config()` : extraire dans `server/core/config.py` (singleton)
- Pattern SSE (streaming queue) : créer un helper générique `SSETaskRunner`

### 4.6 — Gestion Propre de la Concurrence
- Remplacer les `threading.Thread` manuels par `asyncio.to_thread()` (Python 3.9+)
- Remplacer les dictionnaires globaux `_active_*` par un `TaskRegistry` avec TTL et nettoyage automatique
- Utiliser `asyncio.TaskGroup` pour la gestion du cycle de vie des tâches

---

## 5. Roadmap "Production Ready"

### Phase 1 — Sécurité Critique (Semaine 1-2)
1. **Authentification JWT** sur tous les endpoints API
2. **Éliminer le Path Traversal** dans `diff.py` (refactoring Gold Standard ci-dessus)
3. **Modèles Pydantic** sur TOUS les endpoints (`scan`, `backup`, `audit`, `scheduler`, `topology`)
4. **Remplacer `AutoAddPolicy`** par un système de `known_hosts`
5. **CORS middleware** avec whitelist stricte
6. **Externaliser les secrets** (SNMP communities, SMTP credentials) dans des variables d'environnement

### Phase 2 — Robustesse & Qualité (Semaine 3-4)
1. **Ajouter des tests** : objectif 60% de couverture minimum
   - Tests unitaires pour chaque manager
   - Tests d'intégration API avec `httpx.AsyncClient`
   - Tests de sécurité (path traversal, injection, auth bypass)
2. **Context managers** pour toutes les connexions DB
3. **SQLite WAL mode** + pool de connexions
4. **Nettoyage mémoire** : TTL sur les registres de tâches actives
5. **Logging structuré** (JSON) avec niveaux appropriés, sans PII

### Phase 3 — Architecture & Maintenabilité (Semaine 5-6)
1. **Refactoring en couche service** (séparation API/logique/data)
2. **Pydantic Settings** pour la configuration (remplacement de `config.json`)
3. **Extraction du code dupliqué** (`consume_output`, SSE pattern, config loader)
4. **Type hints** sur 100% des fonctions publiques + configuration `mypy --strict`
5. **Linters** : configuration Ruff + pre-commit hooks

### Phase 4 — CI/CD & Déploiement (Semaine 7-8)
1. **Pipeline CI** : GitHub Actions avec lint, type-check, tests, security scan (bandit, safety)
2. **Dockerfile** multi-stage optimisé
3. **docker-compose** avec reverse proxy TLS (Caddy/Traefik)
4. **Dépendances pinnées** avec `pip-compile` ou migration vers Poetry
5. **Supprimer `ttkbootstrap`** et `pyasyncore` des dépendances

### Phase 5 — Monitoring & Opérations (Semaine 9+)
1. **Health check** fonctionnel (actuellement masqué par le SPA catch-all)
2. **Métriques Prometheus** (durée des scans, nombre de connexions SSH, erreurs)
3. **Content Security Policy** headers pour le frontend
4. **Rate limiting** par IP sur les endpoints critiques
5. **Documentation OpenAPI** enrichie avec exemples et schémas de réponse

---

## Annexe — Résumé des Bare `except` à Éliminer

| Fichier | Ligne(s) | Contexte |
| :--- | :--- | :--- |
| `server/managers/snmp_manager.py` | 64 | `except: pass` dans le filtre d'IP |
| `server/managers/snmp_manager.py` | 119 | `except ValueError: pass` pour la table Excel |
| `server/managers/snmp_manager.py` | 126 | `except: pass` pour l'auto-width |
| `server/managers/snmp_manager.py` | 153 | `except Exception: continue` sans logging |
| `server/managers/snmp_manager.py` | 174 | `except: return None` dans `fetch_oid` |
| `server/managers/snmp_manager.py` | 193 | `except:` dans le parsing MAC |
| `server/api/scan.py` | 24 | `except Exception:` silencieux dans `load_config` |
| `server/api/audit.py` | 24 | `except Exception:` silencieux dans `load_config` |

---

*Fin de l'audit. Ce document doit être traité comme un rapport de sécurité confidentiel.*
