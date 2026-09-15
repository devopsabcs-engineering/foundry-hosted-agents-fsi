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
* Expliquer pourquoi certaines ressources doivent être supprimées plutôt que reconfigurées

## Exercices

### Exercice 14.1 : Inventorier le pipeline

```powershell
Get-ChildItem .github/workflows -Filter *.yml | Select-Object -ExpandProperty Name
```

Résultat attendu : huit flux de travail.

| Flux de travail | Déclencheur | Objet |
| --- | --- | --- |
| `continuous-validation.yml` | poussée, demande de tirage, manuel | Tests de régression hors ligne et compilation Bicep |
| `reviewer-app-build.yml` | poussée et demande de tirage filtrées par chemin | Tests et image de l'application de révision |
| `web-chat-build.yml` | poussée et demande de tirage filtrées par chemin | Tests et image du clavardage |
| `publish-test-trends.yml` | après la validation | Publie les preuves de tests dans le wiki |
| `deploy-and-evaluate.yml` | appel et manuel seulement | Provisionnement et déploiement, préproduction puis production |
| `hosted-agent-cd.yml` | appel et manuel seulement | Déploiement de l'agent hébergé |
| `reviewer-app-teardown.yml` | manuel seulement | Supprime les ressources propres à la révision |
| `network-rebuild-teardown.yml` | manuel seulement | Supprime les ressources dont la configuration réseau est immuable |

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

Résultat attendu : code de sortie 1 avec exactement quatre constats, tous signalant `unexpected key "queue"` :

| Fichier | Ligne |
| --- | --- |
| `deploy-and-evaluate.yml` | 53 |
| `network-rebuild-teardown.yml` | 78 |
| `publish-test-trends.yml` | 48 |
| `reviewer-app-teardown.yml` | 80 |

Ces constats sont attendus. `concurrency.queue` est valide pour le modèle de déploiement de ce dépôt et non reconnu par le schéma de l'analyseur. Traitez tout cinquième constat comme réel, et laissez ces quatre-là tels quels.

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

### Exercice 14.7 : Lire le démantèlement pour reconstruction réseau

Certaines configurations ne peuvent pas être modifiées sur place. `vnetConfiguration` sur un environnement géré d'applications conteneurisées et `networkInjections` sur un compte Foundry se définissent uniquement à la création : déplacer un environnement déjà déployé vers un réseau virtuel impose donc de le supprimer d'abord.

```powershell
Get-Content .github/workflows/network-rebuild-teardown.yml -TotalCount 46
```

Résultat attendu : une bannière nommant les trois types de ressources supprimés et, plus longuement, ce qui est préservé.

La liste des éléments préservés est la moitié la plus intéressante. Les comptes Cosmos restent, car un point de terminaison privé se rattache à un compte existant et les supprimer écarterait chaque dossier du magasin. Le réseau virtuel reste, car les deux environnements le partagent. Les enregistrements Entra restent, car un seul enregistrement de révision sert à la fois la préproduction et la production.

```powershell
Select-String -Path .github/workflows/network-rebuild-teardown.yml -Pattern "seq 1 30|purgeable" | Select-Object -ExpandProperty Line
```

Résultat attendu : une boucle d'interrogation autour de la purge du compte Foundry.

Cette boucle existe à cause d'un détail de synchronisation facile à manquer. `az cognitiveservices account delete` signale une réussite alors que le compte est encore à l'état `Deleting`, et une purge lancée pendant cette fenêtre est rejetée. Un compte injecté conserve en outre un lien d'association de service sur son sous-réseau jusqu'à la fin de la purge : une tentative de purge unique laisse donc le sous-réseau immobilisé et la reconstruction bloquée.

> [!WARNING]
> Supprimer un environnement géré change le nom de domaine de chaque application qu'il contient. Les URI de redirection enregistrés à l'atelier 12 et l'enregistrement du clavardage de l'atelier 11 doivent tous deux être rafraîchis ensuite, avec les mêmes scripts. Les deux scripts fusionnent les URI de redirection au lieu de les remplacer, les réexécuter est donc sûr.

## Liste de vérification

* [ ] Vous avez listé les huit flux de travail et identifié ceux qui s'exécutent automatiquement
* [ ] Chaque suite de tests locale réussit
* [ ] `python eval/evaluation_gate.py` rapporte `Gate: PASS`
* [ ] Le seul secret du pipeline est le jeton de poussée du wiki
* [ ] `actionlint` rapporte exactement quatre constats `queue` connus
* [ ] Vous pouvez nommer les quatre protections précédant les flux de démantèlement
* [ ] Vous pouvez expliquer pourquoi le démantèlement pour reconstruction réseau préserve les comptes Cosmos

## Vérification des connaissances

* Pourquoi un échec de parité bilingue serait-il invisible aux suites de tests unitaires ?
* Pourquoi une variable de dépôt convient-elle à `AZURE_CLIENT_ID` alors qu'un secret client ne conviendrait pas ?
* Le flux de démantèlement supprime une attribution de rôle AcrPull mais jamais le registre de conteneurs. Pourquoi ?
* Si `execute` vaut false par défaut, que produit réellement une première exécution du flux de démantèlement ?
* Pourquoi la porte d'évaluation déterministe évite-t-elle d'appeler un modèle ?
* Pourquoi le compte Foundry doit-il être purgé et pas seulement supprimé avant que la reconstruction puisse se poursuivre ?

## Étapes suivantes

Vous avez complété l'atelier bilingue de préparation de soumissions, d'une donnée synthétique sur votre poste de travail jusqu'à une décision révisée accompagnée d'une piste de vérification.

Retournez à l'[index des ateliers](index.md) ou à la [page d'accueil de l'atelier](../index.md).
