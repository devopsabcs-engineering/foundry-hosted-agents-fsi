---
permalink: /fr/labs/lab-10-azure-foundation
lang: fr
title: "Atelier 10 - Provisionner la fondation Azure"
description: "Lire le modèle Bicep qui soutient le pilote, le compiler hors ligne et comprendre pourquoi le déploiement lui-même demeure verrouillé."
---

> 🇬🇧 **[English version](../../labs/lab-10-azure-foundation)**

> [!IMPORTANT]
> Chaque donnée, règle et résultat de calcul de ce laboratoire est synthétique et non contraignant. Rien ici ne représente un produit, un tarif ou une police Desjardins réel, et aucun organisme de réglementation ni assureur n'a révisé ou approuvé ce contenu.

## Aperçu

| Élément | Valeur |
| --- | --- |
| **Durée** | 35 minutes |
| **Niveau** | Intermédiaire |
| **Prérequis** | [Atelier 09](lab-09-teardown.md), interface de ligne de commande Azure installée |

Les ateliers 00 à 09 n'ont jamais quitté votre poste de travail. C'était délibéré : le calculateur, la machine à états et le graphe de l'agent sont plus faciles à raisonner quand rien ne peut échouer pour une raison réseau. Cet atelier introduit l'infrastructure qui porte ces mêmes composants vers Azure pour un pilote.

Vous allez lire et compiler le modèle. Vous ne le déploierez pas.

## Objectifs d'apprentissage

À la fin de ce laboratoire, vous serez capable de :

* Expliquer ce que `infra/main.bicep` provisionne et comment les noms de préproduction et de production sont dérivés
* Compiler le modèle hors ligne et régénérer l'artéfact `infra/main.json` versionné
* Décrire pourquoi deux paramètres, `reviewerClientId` et `agentPrincipalId`, ont une chaîne vide comme valeur par défaut
* Expliquer le verrou qui empêche le flux de travail de déploiement de s'exécuter

## Exercices

### Exercice 10.1 : Lire le verrou de déploiement

Ouvrez `infra/main.bicep` et lisez le commentaire en tête de fichier avant toute autre chose.

```powershell
Get-Content infra/main.bicep -TotalCount 12
```

Résultat attendu : un commentaire marquant le modèle `AUTHOR-ONLY / NOT DEPLOYED`, verrouillé derrière G2 (plateforme et sécurité), G3 (compatibilité reproductible) et G6 (réglementation et confidentialité). Le même verrou s'applique à `.github/workflows/deploy-and-evaluate.yml`, ce qui explique l'absence de déclencheur `push` sur ce flux de travail.

Traitez ceci comme la contrainte directrice pour le reste de l'atelier. Un modèle qui compile n'est pas un modèle dont l'exécution a été approuvée.

### Exercice 10.2 : Inventorier ce que le modèle provisionne

```powershell
Select-String -Path infra/main.bicep -Pattern "^module " | Select-Object -ExpandProperty Line
```

Résultat attendu : une liste de modules couvrant la surveillance (Log Analytics et Application Insights), le compte et le projet Foundry, le déploiement du modèle, le magasin de dossiers Cosmos DB, les applications conteneurisées MCP et l'application de révision.

Chaque module réside dans `infra/modules/`. Les composants locaux de l'atelier s'y rattachent directement : le dépôt d'approbation construit à l'atelier 03 devient le magasin de dossiers Cosmos, et les deux serveurs MCP des ateliers 04 et 05 deviennent deux applications conteneurisées.

### Exercice 10.3 (pratique) : Retracer la dérivation des noms

Ce modèle ne contient aucun appel à `uniqueString()` ni aucun étiquetage azd. Les noms proviennent d'un unique paramètre `environmentName`.

```powershell
Select-String -Path infra/main.bicep -Pattern "endsWith\(environmentName" | Select-Object -ExpandProperty Line
```

Résultat attendu : plusieurs embranchements sur le suffixe `-staging`, dont le préfixe de nom MCP, la capacité du modèle, l'étiquette d'environnement de révision et le nom de l'application conteneurisée de révision.

Ce dernier embranchement existe pour une raison stricte. Les noms d'applications conteneurisées sont plafonnés à 32 caractères, et `reviewer-` préfixé au nom d'environnement de préproduction en ferait 45. Le modèle utilise donc deux noms littéraux plutôt qu'une interpolation :

| Environnement | Nom de l'application conteneurisée de révision |
| --- | --- |
| Production | `foundry-quote-reviewer` |
| Préproduction | `foundry-quote-reviewer-staging` |

L'atelier 12 dépend de ce déterminisme. Comme le nom est fixe plutôt qu'aléatoire, vous pouvez calculer l'URI de redirection de connexion avant même que l'application ne soit déployée.

### Exercice 10.4 (pratique) : Compiler le modèle hors ligne

La compilation n'exige aucune authentification Azure et ne touche aucun abonnement.

```powershell
az bicep install
az bicep build --file infra/main.bicep --outfile infra/main.json
```

Résultat attendu : la commande se termine avec le code 0. `infra/main.json` est un artéfact versionné, donc si la compilation le modifie, versionnez le fichier régénéré avec votre modification Bicep.

```powershell
git status --short infra/main.json
```

Résultat attendu : aucune sortie lorsque votre copie de travail correspond à l'artéfact versionné.

### Exercice 10.5 : Comprendre les deux paramètres vides

Deux paramètres ont une chaîne vide comme valeur par défaut, et dans les deux cas cette valeur vide évite du travail plutôt que de déployer quelque chose de défectueux.

```powershell
Select-String -Path infra/main.bicep -Pattern "param reviewerClientId|param agentPrincipalId|var deployReviewerApp" | Select-Object -ExpandProperty Line
```

Résultat attendu : les deux paramètres valent `''` par défaut, et `deployReviewerApp` est calculé comme `!empty(reviewerClientId)`.

L'application de révision analyse son identifiant client avec `uuid.UUID()` au démarrage. Transmettre une chaîne vide ne produirait pas un mode dégradé, mais une boucle de plantage. Le modèle ignore donc entièrement le module jusqu'à ce que l'atelier 12 fournisse un enregistrement réel.

`agentPrincipalId` est plus subtil. Un agent hébergé reçoit sa propre identité Entra dédiée par agent, et Foundry crée cette identité au moment du déploiement, après l'exécution de ce modèle. Il ne s'agit explicitement pas de l'identité gérée par le système du compte ou du projet Foundry, elle ne peut donc pas être résolue ici. Tant qu'elle n'est pas fournie, l'agent ne peut pas écrire de dossiers dans Cosmos.

## Liste de vérification

* [ ] Vous avez localisé la bannière des verrous G2, G3 et G6 dans `infra/main.bicep`
* [ ] Vous avez listé les modules que le modèle provisionne
* [ ] `az bicep build` se termine avec le code 0 et laisse `infra/main.json` inchangé
* [ ] Vous pouvez expliquer pourquoi un `reviewerClientId` vide fait ignorer le module de révision
* [ ] Vous pouvez expliquer pourquoi `agentPrincipalId` ne peut pas être résolu à la rédaction du modèle

## Vérification des connaissances

* Pourquoi l'application conteneurisée de révision utilise-t-elle deux noms littéraux plutôt qu'une interpolation de `environmentName` ?
* Si `infra/main.json` est généré à partir de `infra/main.bicep`, pourquoi est-il versionné plutôt qu'ignoré ?
* Qu'est-ce qui échoue en premier si quelqu'un déploie le module de révision avec un `reviewerClientId` vide ?

## Étapes suivantes

Poursuivez avec l'[Atelier 11 : L'interface de clavardage du demandeur](lab-11-web-chat.md).
