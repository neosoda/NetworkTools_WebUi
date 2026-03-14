<div align="center">
  <img src="network-analysis.ico" width="100" height="100" alt="NetworkTools Logo">
  <h1>🌐 NetworkTools WebUI (V3 Pro)</h1>
  <p><b>L'armure numérique pour votre infrastructure réseau.</b></p>

  [![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg?style=for-the-badge&logo=python)](https://www.python.org/)
  [![Framework](https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
  [![UI](https://img.shields.io/badge/UI-Cyber_Aesthetic-ff0055?style=for-the-badge)](https://github.com/neosoda/NetworkTools_WebUi)
  [![License](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)
</div>

---

## 🚀 Présentation

**NetworkTools WebUI** est une plateforme centralisée conçue pour les administrateurs réseau exigeants. Elle combine la puissance de l'automatisation Python avec une interface web réactive et esthétique pour simplifier la gestion quotidienne de parcs hétérogènes.

### 🌟 Points Forts (V15+)
- **Compatibilité Totale** : Support avancé pour **Cisco**, **Allied Telesis**, et **Aruba/HP**.
- **Intelligence Aruba** : Détection et réponse automatique aux bannières *"Press any key"* et gestion dynamique de la pagination (`-- MORE --`).
- **Fiabilisation SSH** : Algorithmes d'anti-EOF et sanitisation rigoureuse des bannières complexes (Mocana).
- **Architecture de Production** : Code hautement modularisé, typage strict (`mypy`-ready), gestion explicite des exceptions SSH, et couverture par tests unitaires.

---

## ✨ Fonctionnalités Majeures

### 💾 Backup Manager (Next-Gen)
- **Multi-Vendeurs** : Capturez vos configurations quel que soit le constructeur.
- **Auto-Cleaning** : Retrait automatique des séquences de contrôle ANSI (`[24;1H`, etc.) pour des fichiers `.txt` parfaitement propres.
- **Sanitisation Windows** : Nettoyage des noms d'hôtes pour éviter les erreurs de caractères interdits.
- **Auto-Archivage** : Génération instantanée de fichiers ZIP pour vos exports globaux.

### ⚖️ Comparateur Évolué
- **Interface Drag & Drop** : Glissez-déposez vos configurations directement sur les zones de comparaison.
- **Diff Visuel Premium** : Visualisation claire des ajouts, suppressions et modifications.
- **Support Texte Direct** : Collez du texte brut ou choisissez des fichiers locaux.

### 🛡️ Audit de Conformité
- **Règles Personnalisables** : Vérifiez instantanément si votre parc respecte vos standards de sécurité (NTP, Telnet disabled, etc.).
- **Rapports visuels** : Statut de conformité par équipement avec détails des manquements.

### 📅 Planificateur & SSH Mass
- **Calendrier Visuel** : Programmez vos backups et audits via une interface calendrier ergonomique.
- **Playbooks YAML** : Automatisez des séquences complexes de commandes SSH sur des centaines d'équipements en un clic.

---

## 🛠️ Installation & Démarrage

### Pré-requis
- **Python** 3.9 ou supérieur.
- **Git** pour la gestion de versions.

### Installation Rapide
```bash
# 1. Cloner le dépôt
git clone https://github.com/neosoda/NetworkTools_WebUi.git
cd NetworkTools_WebUi

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Lancer l'application
python run.py
```

L'interface est accessible sur [http://localhost:8000](http://localhost:8000).

---

## 🏗️ Architecture Technique

| Couche | Technologie |
| :--- | :--- |
| **Backend** | Python 3.10+, FastAPI, Paramiko (Core SSH) |
| **Database** | SQLite (Persistance inventaire & logs) |
| **Frontend** | Vanilla JS, CSS3 Modern (Cyber-Military style) |
| **Automation** | APScheduler (Tâches programmées) |

---

## 📝 Licence
Ce projet est distribué sous licence **MIT**. Voir le fichier `LICENSE` pour plus d'informations.

---
<div align="center">
  <p><i>Propulsé par Antigravity - Conçu pour l'excellence et la fiabilité.</i></p>
</div>
