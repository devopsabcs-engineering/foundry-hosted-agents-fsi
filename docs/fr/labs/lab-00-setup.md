---
permalink: /fr/labs/lab-00-setup
lang: fr
title: "Atelier 00 - Configuration"
description: "Créer un environnement virtuel Python, installer les dépendances de chaque composant et confirmer que les suites de tests existantes réussissent."
---

> 🇬🇧 **[English version](../../labs/lab-00-setup)**

> [!IMPORTANT]
> Chaque donnée, règle et résultat de calcul de ce laboratoire est synthétique et non contraignant. Rien ici ne représente un produit, un tarif ou une police Desjardins réel, et aucun organisme de réglementation ni assureur n'a révisé ou approuvé ce contenu.

## Aperçu

| Élément | Valeur |
| --- | --- |
| **Durée** | 20 minutes |
| **Niveau** | Débutant |
| **Prérequis** | Aucun |

## Objectifs d'apprentissage

À la fin de ce laboratoire, vous serez capable de :

* Créer un environnement virtuel Python pour cet atelier
* Installer les dépendances du calculateur, du dépôt d'approbation, des deux serveurs MCP et de l'agent LangGraph
* Exécuter les suites pytest existantes comme vérification de bon fonctionnement avant de toucher au code
* Repérer la mention synthétique et non contraignante que vous reverrez dans chaque laboratoire

## Exercices

### Exercice 0.1 : Confirmer Python et cloner le dépôt

Cet atelier cible Python 3.11 ou plus récent.

```powershell
python --version
git clone https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi.git
cd foundry-hosted-agents-fsi
```

Si le dépôt est déjà ouvert, passez l'étape de clonage et confirmez que vous êtes à la racine du dépôt avant de continuer.

### Exercice 0.2 : Créer un environnement virtuel et installer les dépendances

Chaque composant conserve son propre `requirements.txt`. Installez les quatre fichiers pour que le calculateur, les deux serveurs MCP et l'agent soient disponibles dans le même environnement.

```powershell
python -m venv .venv
./.venv/Scripts/Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -r mcp/application-server/requirements.txt
python -m pip install -r mcp/rulebook-server/requirements.txt
python -m pip install -r src/quote-preparation-agent/requirements.txt
```

Le `requirements.txt` racine couvre `pytest` et `jsonschema`, utilisés par les tests du calculateur et du dépôt d'approbation dans `apps/workshop/`.

### Exercice 0.3 : Exécuter les suites de tests existantes

Avant de modifier quoi que ce soit, confirmez que les tests du dépôt réussissent dans votre environnement.

```powershell
python -m pytest apps/workshop mcp src/quote-preparation-agent -q
```

Résultat attendu : tous les tests réussissent, sans aucun échec. Le nombre exact de tests augmente au fil des laboratoires et des phases suivantes ; ne le comparez pas à un chiffre fixe.

> [!TIP]
> Aucun de ces tests n'appelle Azure, un modèle de langage ou le réseau. Ils s'exécutent entièrement à partir des données de `data/synthetic/` et d'une machine à états LangGraph compilée, ce qui en fait un moyen rapide de confirmer que votre environnement Python est correct avant l'atelier 01.

### Exercice 0.4 : Repérer la mention de non-responsabilité

Ouvrez [README.md](../../README.md) et [docs/index.md](../index.md). Repérez le paragraphe qui indique que chaque donnée, règle et résultat de calcul est synthétique et non contraignant, sans révision ni approbation réglementaire. Vous reverrez la même affirmation, ou une variante proche, en haut de chaque laboratoire restant.

## Liste de vérification

* [ ] `python -m venv .venv` s'est terminé et l'environnement s'active sans erreur
* [ ] Les quatre fichiers `requirements.txt` se sont installés sans erreur
* [ ] `pytest apps/workshop mcp src/quote-preparation-agent -q` ne rapporte aucun échec
* [ ] Vous avez repéré la mention synthétique et non contraignante dans README.md ou docs/index.md

## Vérification des connaissances

* Pourquoi cet atelier conserve-t-il un `requirements.txt` distinct pour chaque serveur MCP et pour l'agent, plutôt qu'un seul fichier partagé ?
* Quels trois répertoires de premier niveau la commande de l'exercice 0.3 couvre-t-elle ?

## Étapes suivantes

Poursuivez avec l'[Atelier 01 : Données et schéma](lab-01-fixtures-schema.md).
