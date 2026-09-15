---
permalink: /fr/labs/lab-14-pilot-operations
lang: fr
title: "Atelier 14 - Exploitation du pilote"
description: "Exécuter localement le pipeline de validation, lire la porte d'évaluation et parcourir le flux de démantèlement qui protège l'infrastructure partagée."
---

> 🇬🇧 **[English version](../../labs/lab-14-pilot-operations)**

> [!IMPORTANT]
> Chaque donnée, règle et résultat de calcul de ce laboratoire est synthétique et non contraignant. Rien ici ne représente un produit, un tarif ou une police Desjardins réel, et aucun organisme de réglementation ni assureur n'a révisé ou approuvé ce contenu.

## Aperçu

| Élément | Valeur |
| --- | --- |
| **Durée** | 40 minutes |
| **Niveau** | Avancé |
| **Prérequis** | [Atelier 13](lab-13-reviewer-ui.md) |

Vous avez maintenant vu chaque composant : le calculateur, la machine à états, les serveurs MCP, l'agent, le clavardage du demandeur et l'interface de révision. Cet atelier couvre ce qui les maintient honnêtes d'un changement à l'autre.

## Objectifs d'apprentissage

À la fin de ce laboratoire, vous serez capable de :

* Exécuter localement et hors ligne les mêmes vérifications que l'intégration continue
* Lire la porte d'évaluation déterministe et expliquer ce qu'elle refuse de laisser passer
* Expliquer pourquoi le pipeline s'authentifie par OIDC et ne porte presque aucun secret
* Décrire la conception de sécurité du flux de démantèlement
* Identifier quels flux de travail sont verrouillés et pourquoi

## Exercices

### Exercice 14.1 : Inventorier le pipeline

```powershell
Get-ChildItem .github/workflows -Filter *.yml | Select-Object -ExpandProperty Name
```

Résultat attendu : sept flux de travail.

| Flux de travail | Déclencheur | Objet |
| --- | --- | --- |
| `continuous-validation.yml` | poussée, demande de tirage, manuel | Tests de régression hors ligne et compilation Bicep |
| `reviewer-app-build.yml` | poussée et demande de tirage filtrées par chemin | Tests et image de l'application de révision |
| `web-chat-build.yml` | poussée et demande de tirage filtrées par chemin | Tests et image du clavardage |
| `publish-test-trends.yml` | après la validation | Publie les preuves de tests dans le wiki |
| `deploy-and-evaluate.yml` | appel et manuel seulement | Provisionnement et déploiement, verrouillé |
| `hosted-agent-cd.yml` | appel et manuel seulement | Déploiement de l'agent hébergé, verrouillé |
| `reviewer-app-teardown.yml` | manuel seulement | Supprime les ressources propres à la révision |

Seuls les trois premiers s'exécutent automatiquement. Rien qui touche Azure ne s'exécute sur une poussée.

### Exercice 14.2 (pratique) : Exécuter la suite hors ligne localement

Ce sont les commandes qu'exécute `continuous-validation.yml`.

```powershell
pytest src/quote-preparation-agent/tests -v
pytest eval -v
pytest apps/workshop/tests mcp/application-server/tests mcp/rulebook-server/tests -v
```

Résultat attendu : les trois suites réussissent. Les surfaces applicatives sont testées par leurs propres flux de travail :

```powershell
python -m pytest apps/reviewer-app/tests -v
$env:PYTHONPATH = 'apps/web-chat'
python -m pytest apps/web-chat/tests -v
```

Les tests de révision insèrent eux-mêmes leur chemin d'importation, alors que ceux du clavardage s'appuient sur `PYTHONPATH`. Les flux de travail diffèrent exactement de la même manière, ce qu'il vaut la peine de remarquer avant de copier une commande de l'un à l'autre.

### Exercice 14.3 (pratique) : Lire la porte d'évaluation

```powershell
python eval/evaluation_gate.py
```

Résultat attendu : une ligne indiquant combien d'enregistrements de référence ont réussi, un résultat de parité bilingue et un verdict final.

```text
13/13 records passed; bilingual_parity=PASS
Gate: PASS
```

La porte est déterministe. Elle n'appelle aucun modèle et n'effectue aucune requête réseau, un échec signifie donc toujours un changement de comportement plutôt qu'un fournisseur instable.

La parité bilingue mérite qu'on s'y arrête. Un changement qui améliorerait le message anglais en laissant le message français périmé réussirait chaque test unitaire de ce dépôt tout en constituant un défaut, car les deux langues sont le produit. La porte traite une rupture de parité comme un échec.

### Exercice 14.4 : Comprendre la posture d'authentification

```powershell
Select-String -Path .github/workflows/*.yml -Pattern "secrets\." | Select-Object -ExpandProperty Line
```

Résultat attendu : le seul secret référencé dans tout le pipeline est le jeton de poussée du wiki. Tout le reste provient de variables de dépôt.

L'accès à Azure passe par la fédération d'identité de charge de travail :

```powershell
Select-String -Path .github/workflows/deploy-and-evaluate.yml -Pattern "azure/login|client-id|tenant-id|subscription-id" | Select-Object -ExpandProperty Line
```

Résultat attendu : `azure/login` configuré à partir de `vars.AZURE_CLIENT_ID`, `vars.AZURE_TENANT_ID` et `vars.AZURE_SUBSCRIPTION_ID`. Aucun secret client n'apparaît nulle part, car OIDC échange un jeton GitHub de courte durée contre un jeton Azure au moment de l'exécution. Une variable de dépôt divulguée est un ensemble d'identifiants, pas une donnée d'authentification.

C'est également pourquoi l'atelier 12 devait être exécuté par une personne administratrice. L'identité fédérée détient des permissions de ressources Azure et aucune permission Microsoft Graph.

### Exercice 14.5 (pratique) : Analyser les flux de travail

```powershell
actionlint
```

Résultat attendu : code de sortie 1 avec exactement trois constats, tous signalant `unexpected key "queue"` :

| Fichier | Ligne |
| --- | --- |
| `deploy-and-evaluate.yml` | 58 |
| `publish-test-trends.yml` | 48 |
| `reviewer-app-teardown.yml` | 80 |

Ces constats sont attendus. `concurrency.queue` est valide pour le modèle de déploiement de ce dépôt et non reconnu par le schéma de l'analyseur. Traitez tout quatrième constat comme réel, et laissez ces trois-là tels quels.

### Exercice 14.6 : Lire la conception de sécurité du démantèlement

Le démantèlement est le flux de travail le plus dangereux de tout pilote, lisez donc son en-tête avant ses étapes.

```powershell
Get-Content .github/workflows/reviewer-app-teardown.yml -TotalCount 44
```

Résultat attendu : une bannière expliquant que le flux ne supprime jamais le groupe de ressources.

La raison est précise. `vars.AZURE_RESOURCE_GROUP` nomme un groupe de ressources unique partagé par les environnements de préproduction et de production, une commande `az group delete` lancée lors du démantèlement de la préproduction emporterait donc la production avec elle. Le flux supprime en conséquence uniquement des ressources nommées individuellement et propres à la révision, et un garde-fou de noms protégés fait échouer l'exécution si une cible de suppression calculée entre en collision avec l'infrastructure partagée.

Quatre protections indépendantes précèdent le premier appel Azure :

* Le flux est manuel seulement, jamais sur poussée, planification ou demande de tirage
* L'opérateur doit saisir le nom de l'environnement cible dans une entrée `confirm`, et une discordance échoue avant tout appel Azure
* `execute` vaut false par défaut, une exécution sans modification d'entrée est donc un essai à blanc qui rapporte sans supprimer
* La tâche se lie à l'environnement GitHub correspondant, la protection par réviseurs obligatoires s'applique donc

Chaque suppression vérifie d'abord l'existence de la cible, une réexécution après un échec partiel réussit donc, et une exécution contre des ressources déjà absentes se termine avec le code 0.

### Exercice 14.7 : Localiser le verrou restant

L'atelier 10 a présenté le verrou G2, G3 et G6 sur le modèle d'infrastructure. Le même verrou couvre le déploiement.

```powershell
Get-Content .github/workflows/deploy-and-evaluate.yml -TotalCount 20
```

Résultat attendu : une bannière réservée à l'auteur indiquant de ne pas déclencher le flux tant que les verrous ne sont pas levés.

Deux conséquences en découlent, et les deux sont correctes plutôt que défectueuses :

* Les URI de redirection HTTPS enregistrés à l'atelier 12 ne se résolvent pas, car aucune application conteneurisée de révision n'existe encore
* L'agent hébergé n'a aucune identité Entra d'agent, `agentPrincipalId` de l'atelier 10 demeure donc vide et les tableaux de liens de déploiement publiés dans le wiki omettent les lignes de révision

Le pilote est complet en tant que système et délibérément incomplet en tant que déploiement. Reconnaître cette différence est l'objet de cet atelier.

## Liste de vérification

* [ ] Vous avez listé les sept flux de travail et identifié ceux qui s'exécutent automatiquement
* [ ] Chaque suite de tests locale réussit
* [ ] `python eval/evaluation_gate.py` rapporte `Gate: PASS`
* [ ] Le seul secret du pipeline est le jeton de poussée du wiki
* [ ] `actionlint` rapporte exactement trois constats `queue` connus
* [ ] Vous pouvez nommer les quatre protections précédant le flux de démantèlement
* [ ] Vous avez localisé la bannière réservée à l'auteur sur le flux de déploiement

## Vérification des connaissances

* Pourquoi un échec de parité bilingue serait-il invisible aux suites de tests unitaires ?
* Pourquoi une variable de dépôt convient-elle à `AZURE_CLIENT_ID` alors qu'un secret client ne conviendrait pas ?
* Le flux de démantèlement supprime une attribution de rôle AcrPull mais jamais le registre de conteneurs. Pourquoi ?
* Si `execute` vaut false par défaut, que produit réellement une première exécution du flux de démantèlement ?
* Pourquoi la porte d'évaluation déterministe évite-t-elle d'appeler un modèle ?

## Étapes suivantes

Vous avez complété l'atelier bilingue de préparation de soumissions, d'une donnée synthétique sur votre poste de travail jusqu'à une décision révisée accompagnée d'une piste de vérification.

Retournez à l'[index des ateliers](index.md) ou à la [page d'accueil de l'atelier](../index.md).
