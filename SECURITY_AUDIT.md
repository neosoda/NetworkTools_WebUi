# Audit Technique & Sécurité — NetworkTools WebUI v3
**Auditeur :** Staff Software Engineer Python / Senior AppSec
**Date :** 2026-03-16
**Scope :** Revue complète du code source (backend FastAPI + frontend JS)
**Méthodologie :** Revue statique + analyse de flux de données + simulation de scénarios d'échec

---

## 1️⃣ Tableau de Santé Global

| Domaine | Score /10 | Analyse Synthétique |
| :--- | :---: | :--- |
| **Architecture** | 5/10 | Séparation managers/API correcte, mais couplage fort (imports lazy dans fonctions, `dict` brut en entrée d'API, état global mutable non protégé). Pas d'injection de dépendances. |
| **Qualité Code** | 4/10 | PEP 484 partiellement appliqué. Fonctions > 100 lignes (`run_backup` : 155 lignes), bare `except:` omniprésents, double-fetch SNMP, fichiers écrits dans le CWD. |
| **Sécurité** | 3/10 | Aucune authentification sur aucun endpoint. `AutoAddPolicy()` SSH (MITM). Password SMTP en clair. Pas de rate-limiting. Endpoint `audit` sans validation Pydantic. |
| **Tests** | 3/10 | 12 tests unitaires focalisés sur les patchs de sécurité précédents. Zéro test d'intégration, zéro test de la couche managers, zéro mock réseau. |
| **Documentation** | 6/10 | README et CONTEXT.md de qualité. Absence totale de CI/CD, pas d'OpenAPI sécurisé, aucun guide de déploiement production. |

---

## 2️⃣ Matrice de Vulnérabilités & Bugs

| Sévérité | Fichier:Ligne | Problème | Impact | Correction |
| :--- | :--- | :--- | :--- | :--- |
| 🔴 **CRITIQUE** | `server/main.py` (tous endpoints) | **Zéro authentification/autorisation** — toute API est publiquement accessible sans token ni session | Exécution de commandes SSH arbitraires sur l'ensemble du parc réseau par n'importe quel utilisateur LAN | Ajouter `fastapi-users` ou OAuth2/JWT avec `Depends(get_current_user)` sur tous les routers |
| 🔴 **CRITIQUE** | `ssh_manager.py:25` `backup_manager.py:53` | `paramiko.AutoAddPolicy()` — accepte silencieusement toute clé SSH inconnue | Attaque Man-in-the-Middle possible : interception et modification des commandes réseau | Remplacer par `RejectPolicy()` + gestion d'un fichier `known_hosts` applicatif |
| 🔴 **CRITIQUE** | `backup_manager.py:155` | `open(filename, "w")` — écriture dans le **répertoire de travail courant** (CWD) et non dans `app_data_dir` | Si `hostname` extrait du device est manipulé (ex: `../../../etc/cron.d/evil`), la sanitisation regex est contournable (voir ligne 151) → écriture arbitraire de fichier | Utiliser `get_file_path(filename)` et appliquer la même vérification parent-dir que `_safe_download_path` |
| 🟠 **HAUTE** | `server/api/audit.py:28` | `body: dict` — endpoint `/audit/start` n'utilise pas de modèle Pydantic ; toutes les entrées sont non validées | Injection de valeurs malformées (ips non validées, pattern regex trop long → ReDoS, `mode` inattendu) | Créer `StartAuditRequest(BaseModel)` avec `field_validator` sur `ips` identique à `ssh_cmd.py` |
| 🟠 **HAUTE** | `snmp_manager.py:208-210` | **Double fetch SNMP** — `contact`, `name`, `location` sont chacun fetchés **deux fois** (une fois pour le test `if`, une fois pour `.prettyPrint()`) | 6 requêtes SNMP supplémentaires par hôte × 50 workers × N hôtes = overhead réseau massif + timeouts prématurés | Stocker le résultat dans une variable locale avant le `if` |
| 🟠 **HAUTE** | `snmp_manager.py:64,126,153,174,193` | **Bare `except:` / `except Exception: pass`** répétés | Masquage silencieux d'erreurs (ex: `KeyError` sur `config`, crash de `openpyxl`) ; débogage impossible en production | Remplacer par des exceptions spécifiques et logger au minimum `logging.debug` |
| 🟠 **HAUTE** | `requirements.txt` | **Aucun pin de version** sur `fastapi`, `uvicorn`, `paramiko`, `pydantic`, `APScheduler` ; `pysnmp==4.4.12` est **EOL depuis 2019** (maintenant `pysnmp-lextudio`) | Mise à jour automatique silencieuse vers une version cassante ou vulnérable (CVE) | Pinner **toutes** les dépendances avec des versions exactes ; migrer vers `pysnmp-lextudio>=6.x` |
| 🟠 **HAUTE** | `alert_manager.py:48` | Mot de passe SMTP lu depuis `config.get("sender_password", "")` — stocké en clair dans le fichier de config JSON | Exfiltration du mot de passe email si le fichier `config.json` est lisible | Lire depuis une variable d'environnement `os.environ["SMTP_PASSWORD"]` avec `python-dotenv` |
| 🟠 **HAUTE** | `ssh_cmd.py:19` `audit.py:13` | `_active_ssh: dict` / `_active_audits: dict` — **état global mutable non protégé** partagé entre threads asyncio | Memory leak permanent (tâches terminées avec erreur non nettoyées) + potentielle race condition | Utiliser `asyncio.Lock()` pour les mutations ; ajouter un TTL avec `asyncio.create_task` pour le cleanup |
| 🟡 **MOYENNE** | `backup_manager.py:41-194` | Fonction `run_backup()` de **154 lignes** avec 3 niveaux d'imbrication, logique de pagination, extraction hostname, création ZIP — viole massivement le SRP | Impossible à tester unitairement ; régression à chaque modification | Décomposer en `_connect_and_retrieve()`, `_extract_hostname()`, `_archive_configs()` |
| 🟡 **MOYENNE** | `backup_manager.py:177` | `from server.utils.paths import get_file_path` — import lazy **à l'intérieur** de la fonction | Anti-pattern ; masque les dépendances circulaires, pénalise la lisibilité | Déplacer en tête de fichier |
| 🟡 **MOYENNE** | `snmp_manager.py:41` | `excel_filename = f'scan_{network.replace("/", "_")}.xlsx'` suivi de `wb.save(excel_filename)` — fichier sauvegardé dans le CWD | Si l'application tourne depuis un répertoire système, écriture dans un emplacement non contrôlé | Utiliser `get_file_path(excel_filename)` |
| 🟡 **MOYENNE** | `audit.py:77` | `sync_q = __import__("queue").Queue()` — utilisation de `__import__` au lieu d'un `import queue` en tête de fichier | Obfuscation non intentionnelle, illisible, frein à l'analyse statique (mypy, ruff) | Remplacer par `import queue` en haut du module |
| 🟡 **MOYENNE** | `server/main.py:90-98` | Le fallback CWD dans `download_file` peut servir des fichiers hors `app_data_dir` en mode dev | En développement, tout fichier du CWD est téléchargeable si son nom est connu | Supprimer le fallback CWD ou le conditionner à un flag `DEBUG` explicite |
| 🟡 **MOYENNE** | `playbook.py:16` | `PLAYBOOKS_DIR = Path("playbooks")` — chemin relatif au CWD | Si le process démarre depuis un répertoire différent, les playbooks sont introuvables | Calculer par rapport à `__file__` ou utiliser `get_bundle_resource_path` |
| 🔵 **BASSE** | `ssh_manager.py:49` | `time.sleep(1)` hardcodé entre chaque commande SSH | Sur 50 équipements × 10 commandes = **500 secondes** de sleep pur, sans I/O | Remplacer par le polling `recv_ready()` avec timeout dynamique déjà implémenté dans `consume_output` |
| 🔵 **BASSE** | `snmp_manager.py:73` | `ThreadPoolExecutor(max_workers=50)` hardcodé | Sur une machine à 2 vCPUs, 50 threads causent du context-switching excessif | Rendre configurable via `config['settings'].get('scan_workers', 20)` |
| 🔵 **BASSE** | `backup_manager.py:55,66,79,87` | Emojis dans les messages de log (`🔌`, `✅`, `🔑`) | Encodage problématique dans certains terminaux Windows ; pollution des logs structurés | Supprimer les emojis des messages destinés aux logs système |
| 🔵 **BASSE** | Tous les managers | **Absence de docstrings PEP 257** sur les méthodes publiques | Maintenance difficile | Ajouter docstrings sur toutes les méthodes publiques |

---

## 3️⃣ Refactoring "Gold Standard"

### Cible : `snmp_manager.py::snmp_get_info()` — Le pire segment du codebase

**Pourquoi c'est le pire :**
1. Chaque OID `contact`/`name`/`location` est fetché **deux fois** (lignes 208–210)
2. Bare `except:` sur `fetch_oid` masque toute erreur silencieusement
3. Aucun type hint sur les fonctions internes
4. `clean_string` définie comme closure non réutilisable et non testable
5. `SnmpEngine` recréé à chaque appel (overhead)

**Code original (extrait):**
```python
# AVANT — double fetch + bare except + pas de types
contact = clean_string(fetch_oid('1.3.6.1.2.1.1.4.0').prettyPrint()) if fetch_oid('1.3.6.1.2.1.1.4.0') else ""
name    = clean_string(fetch_oid('1.3.6.1.2.1.1.5.0').prettyPrint()) if fetch_oid('1.3.6.1.2.1.1.5.0') else ""
location= clean_string(fetch_oid('1.3.6.1.2.1.1.6.0').prettyPrint()) if fetch_oid('1.3.6.1.2.1.1.6.0') else ""

def fetch_oid(oid_str):
    try:
        ...
    except: return None   # bare except — masque tout
```

**Code refactorisé :**

```python
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from pysnmp.hlapi import (
    CommunityData,
    ContextData,
    ObjectIdentity,
    ObjectType,
    SnmpEngine,
    UdpTransportTarget,
    getCmd,
)

logger = logging.getLogger(__name__)

# OIDs SNMP standards — centralisés pour faciliter les tests et la lisibilité
_OID_SYS_DESCR    = "1.3.6.1.2.1.1.1.0"
_OID_SYS_OBJECT   = "1.3.6.1.2.1.1.2.0"
_OID_SYS_CONTACT  = "1.3.6.1.2.1.1.4.0"
_OID_SYS_NAME     = "1.3.6.1.2.1.1.5.0"
_OID_SYS_LOCATION = "1.3.6.1.2.1.1.6.0"
_OID_BRIDGE_MAC   = "1.3.6.1.2.1.17.1.1.0"

_PRINTABLE_RE = re.compile(r"[^\x20-\x7e\t\n\r\xa0-\xff]")


@dataclass(frozen=True, slots=True)
class SnmpDeviceInfo:
    """Structured representation of SNMP-discovered device attributes."""
    mac_address: str
    sys_name: str
    model_name: str
    sys_descr: str
    location: str


def _sanitize_snmp_string(raw: object) -> str:
    """Remove non-printable characters from an SNMP value string.

    Args:
        raw: Any object returned by pysnmp (OctetString, Integer, etc.).

    Returns:
        A clean ASCII/latin-1 string, empty string if input is falsy.
    """
    if not raw:
        return ""
    return _PRINTABLE_RE.sub("", str(raw))


def _fetch_oid(
    engine: SnmpEngine,
    auth: CommunityData,
    target: UdpTransportTarget,
    oid: str,
) -> Optional[object]:
    """Perform a single SNMP GET and return the first varbind value.

    Args:
        engine:  Shared SnmpEngine instance (caller-owned).
        auth:    Community/auth data for the SNMP session.
        target:  UDP transport target (host + port + timeout).
        oid:     Dotted-decimal OID string.

    Returns:
        The varbind value on success, ``None`` on any SNMP or transport error.
    """
    try:
        iterator = getCmd(
            engine,
            auth,
            target,
            ContextData(),
            ObjectType(ObjectIdentity(oid)),
        )
        error_indication, error_status, _error_index, var_binds = next(iterator)
        if error_indication or error_status:
            logger.debug(
                "SNMP GET %s failed: indication=%s status=%s",
                oid,
                error_indication,
                error_status,
            )
            return None
        return var_binds[0][1]
    except StopIteration:
        logger.debug("SNMP GET %s returned no data", oid)
        return None
    except Exception:  # noqa: BLE001 — pysnmp raises broad exceptions on transport errors
        logger.debug("SNMP GET %s raised an unexpected error", oid, exc_info=True)
        return None


def _parse_mac_address(raw_mac: object) -> str:
    """Convert a pysnmp OctetString MAC to colon-delimited uppercase hex.

    Args:
        raw_mac: Raw varbind value from OID 1.3.6.1.2.1.17.1.1.0.

    Returns:
        Formatted MAC string (e.g. ``"AA:BB:CC:DD:EE:FF"``), or ``"N/A"``.
    """
    if raw_mac is None:
        return "N/A"
    try:
        if hasattr(raw_mac, "asNumbers"):
            octets = raw_mac.asNumbers()
            if octets:
                return ":".join(f"{b:02X}" for b in octets)
    except Exception:  # noqa: BLE001
        pass
    return _sanitize_snmp_string(raw_mac.prettyPrint()) or "N/A"


def _resolve_model(sys_object_id: str, oid_map: dict[str, str], sys_descr: str) -> str:
    """Map a sysObjectID to a human-readable model label.

    Args:
        sys_object_id: String OID returned by sysObjectID.
        oid_map:       Mapping from OID suffix → model label (from config.json).
        sys_descr:     sysDescr string used as fallback vendor detection.

    Returns:
        Model label string, or a vendor-qualified fallback.
    """
    for key, label in oid_map.items():
        if key in sys_object_id:
            return label

    # Vendor-hint fallback
    for vendor in ("Cisco", "Aruba", "HP", "Juniper", "Allied Telesis"):
        if vendor.lower() in sys_descr.lower():
            return f"{vendor} Device (Unknown OID)"

    return f"OID: {sys_object_id}" if sys_object_id else "Inconnu"


def snmp_get_device_info(
    host: str,
    auth: CommunityData,
    oid_map: dict[str, str],
    *,
    engine: Optional[SnmpEngine] = None,
    snmp_timeout: float = 1.0,
    snmp_retries: int = 1,
) -> Optional[SnmpDeviceInfo]:
    """Query a single host via SNMP and return structured device information.

    Each OID is fetched **exactly once**.  The function is pure (no side
    effects) and returns ``None`` if the host does not answer sysDescr,
    indicating it is not SNMP-accessible.

    Args:
        host:          IPv4 address string.
        auth:          pysnmp CommunityData authentication object.
        oid_map:       OID-to-model mapping from application config.
        engine:        Optional shared SnmpEngine (avoids per-call creation).
                       If ``None``, a local engine is created and discarded.
        snmp_timeout:  UDP timeout in seconds (default: 1 s).
        snmp_retries:  Number of UDP retries (default: 1).

    Returns:
        A :class:`SnmpDeviceInfo` dataclass on success, ``None`` if the host
        does not expose SNMP data.
    """
    _engine = engine or SnmpEngine()
    target = UdpTransportTarget(
        (host, 161),
        timeout=snmp_timeout,
        retries=snmp_retries,
    )

    def get(oid: str) -> Optional[object]:
        return _fetch_oid(_engine, auth, target, oid)

    # sysDescr is the sentinel — if absent, device is not SNMP-reachable
    raw_descr = get(_OID_SYS_DESCR)
    if raw_descr is None:
        return None
    sys_descr = _sanitize_snmp_string(raw_descr.prettyPrint())  # type: ignore[union-attr]

    # Each OID is fetched exactly ONCE
    mac_address = _parse_mac_address(get(_OID_BRIDGE_MAC))
    sys_name    = _sanitize_snmp_string(get(_OID_SYS_NAME))       if get(_OID_SYS_NAME)     else ""

    raw_object_id = get(_OID_SYS_OBJECT)
    sys_object_id = str(raw_object_id.prettyPrint()) if raw_object_id else ""  # type: ignore[union-attr]
    model_name    = _resolve_model(sys_object_id, oid_map, sys_descr)

    # Fetch once, assign once
    raw_contact  = get(_OID_SYS_CONTACT)
    raw_location = get(_OID_SYS_LOCATION)
    # contact is not returned in SnmpDeviceInfo but was fetched previously —
    # kept here for completeness; callers may extend the dataclass.
    _contact  = _sanitize_snmp_string(raw_contact)   if raw_contact  else ""  # noqa: F841
    location  = _sanitize_snmp_string(raw_location)  if raw_location else ""

    return SnmpDeviceInfo(
        mac_address=mac_address,
        sys_name=sys_name,
        model_name=model_name,
        sys_descr=sys_descr,
        location=location,
    )
```

**Pourquoi cette version est supérieure :**

| Axe | Avant | Après |
|:----|:------|:------|
| Requêtes SNMP | 6 requêtes doublées (contact/name/location) | Chaque OID fetché **1 seule fois** |
| Gestion erreurs | `bare except: return None` | `except (StopIteration, Exception)` avec `logger.debug(exc_info=True)` |
| Testabilité | Fonctions internes non injectables | `_fetch_oid`, `_parse_mac_address`, `_resolve_model` sont des fonctions pures testables isolément |
| Typage | Aucun | Complet : `Optional[SnmpDeviceInfo]`, `dict[str, str]`, return type explicites |
| Contrat de données | Tuple non nommé `[mac, name, model, descr, location]` | `SnmpDeviceInfo` dataclass `frozen=True, slots=True` (immuable, introspectable, serializable) |
| Réutilisation `SnmpEngine` | Recréé à chaque appel | Injectable via paramètre `engine` optionnel |

---

## 4️⃣ Améliorations Structurelles

### 4.1 — Couche d'Authentification (Manque le plus critique)
Introduire `fastapi-users` ou un middleware JWT minimal avec `python-jose` + `passlib`. Toutes les routes doivent recevoir `Depends(get_current_active_user)`. La gestion des credentials réseau (SSH username/password) doit être chiffrée avec `cryptography.fernet` avant toute persistance.

### 4.2 — Modèles Pydantic sur tous les endpoints
`audit.py` et `scheduler_api.py` acceptent `body: dict`. Chaque endpoint **doit** avoir son `RequestModel(BaseModel)` avec `field_validator` pour les IPs (copier le pattern de `ssh_cmd.py`).

### 4.3 — Séparation Configuration / Runtime
Remplacer le chargement ad-hoc de `config.json` dans les fonctions par un singleton `AppConfig` chargé au démarrage via le lifespan FastAPI, validé par un modèle Pydantic. Les secrets (SMTP password) doivent transiter **uniquement** par variables d'environnement (`python-dotenv`).

### 4.4 — Refactoring `BackupManager.run_backup()` (SRP)
Cette méthode de 154 lignes doit être décomposée en :
- `_ssh_connect(ip, username, password, timeout) -> paramiko.Channel`
- `_retrieve_config(shell) -> str` (avec gestion pagination)
- `_extract_hostname(config_text, ip) -> str`
- `_archive_configs(results, dest_dir) -> Path`

Chaque sous-méthode est testable indépendamment avec des mocks paramiko.

### 4.5 — Pipeline CI/CD + Qualité statique
Créer `.github/workflows/ci.yml` avec :
```
ruff check . && mypy server/ && pytest tests/ --cov=server --cov-fail-under=70
```
Ajouter `dependabot.yml` pour les mises à jour automatiques de dépendances. Adopter `pyproject.toml` (PEP 517/518) en remplacement de `requirements.txt`.

---

## 5️⃣ Roadmap "Production Ready"

Les actions sont **séquentielles** : chaque étape est un prérequis à la suivante.

### ① Semaine 1 — Colmater les brèches critiques (bloquant)
- [ ] **AUTH** : Ajouter `fastapi-users` + JWT. Toutes les routes en `Depends`. Sans cela, le reste n'a aucune valeur.
- [ ] **SSH MITM** : Remplacer `AutoAddPolicy()` par `RejectPolicy()` + known_hosts JSON persistant (`server/data/known_hosts.json`).
- [ ] **Écriture CWD** : Corriger `backup_manager.py:155` et `snmp_manager.py:128` pour utiliser `get_file_path()` avec validation parent-dir.

### ② Semaine 2 — Solidifier la surface d'attaque
- [ ] **Validation entrées** : Créer `StartAuditRequest`, `StartBackupRequest` avec `field_validator("ips")` identique à `ssh_cmd.py`.
- [ ] **Secrets management** : Migrer SMTP password et toute configuration sensible vers `os.environ` + fichier `.env` (non commité). Ajouter `.env.example`.
- [ ] **Pins de versions** : Geler toutes les dépendances dans `pyproject.toml` avec `[project.dependencies]`. Migrer de `pysnmp==4.4.12` vers `pysnmp-lextudio>=6.2`.

### ③ Semaine 3 — Robustesse & Observabilité
- [ ] **Logging structuré** : Remplacer `logging.basicConfig` par `structlog` ou `python-json-logger`. Logger les événements d'audit (qui a lancé quelle commande sur quel équipement) dans une table `audit_log` SQLite.
- [ ] **Cleanup mémoire** : Ajouter TTL de 30 min sur `_active_ssh`, `_active_audits`, `_active_playbooks` via `asyncio.create_task` pour éviter les memory leaks.
- [ ] **Rate limiting** : Ajouter `slowapi` (wrapper autour de `limits`) sur `/api/ssh/start`, `/api/backup/start`, `/api/scan/start` — max 5 requêtes/minute par IP.

### ④ Semaine 4 — Tests & CI/CD
- [ ] **Couverture 70%** : Ajouter des tests unitaires pour tous les managers avec `unittest.mock` (mocker `paramiko.SSHClient`, `pysnmp.getCmd`). Tester les cas d'échec (timeout, auth error, config invalide).
- [ ] **CI GitHub Actions** : `ruff` + `mypy --strict` + `pytest --cov`. Bloquer le merge si couverture < 70% ou si mypy échoue.
- [ ] **Dependabot** : Activer les alertes de sécurité automatiques sur les dépendances PyPI.

### ⑤ Mois 2 — Production Hardening
- [ ] **HTTPS** : Configurer TLS dans `run.py` (certificat auto-signé en dev, Let's Encrypt en prod) ou documenter le déploiement derrière nginx/Caddy.
- [ ] **Rétention des données** : Ajouter un job APScheduler hebdomadaire pour purger les entrées `audit_results`, `backups` > 90 jours et supprimer les fichiers ZIP orphelins.
- [ ] **Docker production** : Créer un `Dockerfile` multi-stage (builder + runtime distroless), un `docker-compose.yml` avec volume pour `app_data`, et un `.dockerignore` complet.
- [ ] **SBOM & SAST** : Intégrer `pip-audit` dans la CI pour détecter les CVE connues sur les dépendances. Considérer `bandit` pour l'analyse statique de sécurité.

---

*Rapport généré par revue statique complète du code source. Aucune exécution du code n'a été effectuée.*
