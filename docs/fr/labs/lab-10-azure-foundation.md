---
permalink: /fr/labs/lab-10-azure-foundation
lang: fr
title: "Atelier 10 - Provisionner la fondation Azure"
description: "Lire les modèles Bicep qui soutiennent le pilote, les compiler hors ligne et comprendre pourquoi la fondation réseau est déployée séparément du reste."
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

Vous allez lire et compiler les modèles. Le déploiement s'exécute depuis l'intégration continue, pas depuis cet atelier.

## Objectifs d'apprentissage

À la fin de ce laboratoire, vous serez capable de :

* Expliquer ce que `infra/main.bicep` provisionne et comment les noms de préproduction et de production sont dérivés
* Expliquer pourquoi le réseau virtuel réside dans `infra/network.bicep` plutôt que dans `infra/main.bicep`
* Compiler les modèles hors ligne et régénérer les artéfacts JSON versionnés
* Décrire pourquoi deux paramètres, `reviewerClientId` et `agentPrincipalId`, ont une chaîne vide comme valeur par défaut

## Exercices

### Exercice 10.1 : Lire la fondation réseau

Deux modèles se déploient dans un même groupe de ressources. Ouvrez `infra/network.bicep` et lisez la bannière avant toute autre chose.

```powershell
Get-Content infra/network.bicep -TotalCount 12
```

Résultat attendu : un commentaire expliquant que ce modèle est déployé une seule fois pour l'ensemble du groupe de ressources, séparément de `infra/main.bicep`.

La raison mérite d'être comprise, car c'est un piège dans lequel il est facile de tomber. `infra/main.bicep` est déployé deux fois dans le même groupe de ressources, une fois pour la préproduction et une fois pour la production. Un réseau virtuel est une ressource unique dont les sous-réseaux sont des propriétés : une écriture ARM qui omet `subnets` supprime ceux qu'elle ne nomme pas. Si le réseau avait été déclaré dans `infra/main.bicep`, provisionner la préproduction supprimerait les sous-réseaux de la production, et provisionner la production supprimerait ceux de la préproduction.

```powershell
Select-String -Path infra/network.bicep -Pattern "name: 'snet-" | Select-Object -ExpandProperty Line
```

Résultat attendu : cinq sous-réseaux. Deux portent les environnements d'applications conteneurisées, deux portent les exécutions de l'agent et un porte les points de terminaison privés.

Les sous-réseaux d'agent sont distincts de ceux des applications conteneurisées parce qu'un compte Foundry revendique son sous-réseau d'injection de façon exclusive. Deux comptes ne peuvent pas en partager un, d'où un sous-réseau propre à la préproduction et un autre à la production.

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

> [!NOTE]
> Le nom de l'environnement `azd` de production dans l'intégration continue
> (et tout nom de ressource qui en découle, par exemple
> `cosmos-desjardins-quote-preparation-poc`) porte un suffixe historique
> `-poc`. Ce suffixe ne signifie **pas** « preuve de concept » -- il s'agit
> bien de l'environnement de production. Ne confondez pas une ressource
> portant le suffixe `-poc` que vous voyez dans le portail Azure ou les
> journaux d'intégration continue avec un déploiement distinct hors
> production.

### Exercice 10.4 (pratique) : Compiler les modèles hors ligne

La compilation n'exige aucune authentification Azure et ne touche aucun abonnement.

```powershell
az bicep install
az bicep build --file infra/network.bicep --outfile infra/network.json
az bicep build --file infra/main.bicep --outfile infra/main.json
```

Résultat attendu : les deux commandes se terminent avec le code 0. Les fichiers JSON sont des artéfacts versionnés, donc si une compilation en modifie un, versionnez le fichier régénéré avec votre modification Bicep.

```powershell
git status --short infra/main.json infra/network.json
```

Résultat attendu : aucune sortie lorsque votre copie de travail correspond aux artéfacts versionnés.

### Exercice 10.5 : Comprendre les deux paramètres vides

Deux paramètres ont une chaîne vide comme valeur par défaut, et dans les deux cas cette valeur vide évite du travail plutôt que de déployer quelque chose de défectueux.

```powershell
Select-String -Path infra/main.bicep -Pattern "param reviewerClientId|param agentPrincipalId|var deployReviewerApp" | Select-Object -ExpandProperty Line
```

Résultat attendu : les deux paramètres valent `''` par défaut, et `deployReviewerApp` est calculé comme `!empty(reviewerClientId)`.

L'application de révision analyse son identifiant client avec `uuid.UUID()` au démarrage. Transmettre une chaîne vide ne produirait pas un mode dégradé, mais une boucle de plantage. Le modèle ignore donc entièrement le module jusqu'à ce que l'atelier 12 fournisse un enregistrement réel.

`agentPrincipalId` est plus subtil. Un agent hébergé reçoit sa propre identité Entra dédiée par agent, et Foundry crée cette identité au moment du déploiement, après l'exécution de ce modèle. Il ne s'agit explicitement pas de l'identité gérée par le système du compte ou du projet Foundry, elle ne peut donc pas être résolue ici. Tant qu'elle n'est pas fournie, l'agent ne peut pas écrire de dossiers dans Cosmos.

### Exercice 10.6 : Comprendre pourquoi Cosmos est injoignable depuis Internet

```powershell
Select-String -Path infra/modules/cosmos-db.bicep -Pattern "publicNetworkAccess|privateEndpoints|groupIds" | Select-Object -ExpandProperty Line
```

Résultat attendu : `publicNetworkAccess: 'Disabled'`, une ressource `Microsoft.Network/privateEndpoints` et un tableau `groupIds` contenant `Sql`.

Le modèle déclare `Disabled` parce qu'une affectation de politique Azure à la racine du locataire applique un effet `modify` qui réécrit cette propriété à chaque écriture. Une version antérieure de ce modèle déclarait `Enabled`, ce qui a produit une défaillance précise et instructive. Le déploiement a signalé une réussite, la politique a immédiatement remis le compte à `Disabled`, puis l'application de révision a retourné une erreur HTTP 500 à chaque requête avec `Request originated from IP ... through public internet. This is blocked by your Cosmos DB account firewall settings.`

> [!IMPORTANT]
> Un modèle qui déclare une valeur que la politique remplace n'est pas une simple dérive cosmétique. Cela signifie que le déploiement ne décrit plus le système en cours d'exécution, et donc que personne lisant le modèle ne peut prédire le comportement de ce qui est déployé.

Le point de terminaison privé donne aux charges de travail situées dans le réseau virtuel un chemin que le pare-feu accepte. La zone DNS privée compte tout autant : sans elle, les appelants internes au réseau résolvent l'adresse publique du compte, et le pare-feu les rejette exactement comme avant.

```powershell
Select-String -Path infra/modules/cosmos-db.bicep -Pattern "privateDnsZoneGroups" | Select-Object -ExpandProperty Line
```

Résultat attendu : une ressource enfant `privateDnsZoneGroups`, qui est ce qui écrit les enregistrements A dans la zone.

## Liste de vérification

* [ ] Vous pouvez expliquer pourquoi le réseau virtuel n'est pas déclaré dans `infra/main.bicep`
* [ ] Vous avez listé les modules que le modèle provisionne
* [ ] `az bicep build` se termine avec le code 0 pour les deux modèles et laisse les artéfacts JSON inchangés
* [ ] Vous pouvez expliquer pourquoi un `reviewerClientId` vide fait ignorer le module de révision
* [ ] Vous pouvez expliquer pourquoi `agentPrincipalId` ne peut pas être résolu à la rédaction du modèle
* [ ] Vous pouvez expliquer ce qui se brise quand un modèle déclare une valeur que la politique remplace

## Vérification des connaissances

* Pourquoi l'application conteneurisée de révision utilise-t-elle deux noms littéraux plutôt qu'une interpolation de `environmentName` ?
* Si `infra/main.json` est généré à partir de `infra/main.bicep`, pourquoi est-il versionné plutôt qu'ignoré ?
* Qu'est-ce qui échoue en premier si quelqu'un déploie le module de révision avec un `reviewerClientId` vide ?
* Un point de terminaison privé existe mais le groupe de zones DNS privées n'a jamais été créé. Que voit un appelant situé dans le réseau virtuel ?

## Étapes suivantes

Poursuivez avec l'[Atelier 11 : L'interface de clavardage du demandeur](lab-11-web-chat.md).
