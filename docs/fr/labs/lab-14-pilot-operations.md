---
permalink: /fr/labs/lab-14-pilot-operations
lang: fr
title: "Atelier 14 - Exploitation du pilote"
description: "Exécuter localement le pipeline de validation, lire la porte d'évaluation et parcourir le flux de démantèlement qui protège l'infrastructure partagée."
---

> 🇬🇧 **[English version](../../labs/lab-14-pilot-operations)**

> [!IMPORTANT]
> Chaque donnée, règle et résultat de calcul de ce laboratoire est synthétique et non contraignant. Rien ici ne représente un produit, un tarif ou une police Desjardins réel, et aucun organisme de réglementation ni assureur n'a révisé ou approuvé ce contenu.

> [!WARNING]
> Pour poursuivre les ateliers 15 à 18, ne démantelez pas la démo restaurée
> partagée. Gardez staging v5 et production v6 déployés; étudiez les protections
> sans supprimer ces environnements.

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
* Identifier les commandes de démantèlement réservées à un bac à sable jetable explicitement approuvé

## Exercices

### Exercice 14.1 : Inventorier le pipeline

```powershell
Get-ChildItem .github/workflows -Filter *.yml | Select-Object -ExpandProperty Name
```

Résultat attendu : dix flux de travail.

| Flux de travail | Déclencheur | Objet |
| --- | --- | --- |
| `continuous-validation.yml` | poussée, demande de tirage, manuel | Tests de régression hors ligne et compilation Bicep |
| `reviewer-app-build.yml` | poussée/PR filtrées, manuel | Tests; publication ACR sur poussée `main` |
| `web-chat-build.yml` | poussée/PR filtrées, manuel | Tests; publication ACR sur poussée `main` |
| `publish-test-trends.yml` | après validation, manuel | Publie les preuves conservées dans le wiki |
| `require-linked-issue.yml` | cycle de vie des PR | Exige une référence fermant une issue dans la PR |
| `deploy-and-evaluate.yml` | appel et manuel seulement | Provisionnement et déploiement, préproduction puis production |
| `hosted-agent-cd.yml` | appel et manuel seulement | Déploiement de l'agent hébergé |
| `reviewer-app-teardown.yml` | manuel seulement | Supprime les ressources propres à la révision |
| `network-rebuild-teardown.yml` | manuel seulement | Supprime les ressources dont la configuration réseau est immuable |
| `full-teardown.yml` | manuel seulement | Supprime des groupes de ressources entiers à la fin de l'atelier |

Validation, liaison d'issue et publication wiki sont automatiques selon leurs
événements. Les deux flux applicatifs utilisent Azure OIDC et publient des images
ACR sur les poussées admissibles à `main`. Publication n'est pas déploiement :
livraison de l'agent et démantèlement restent explicites, par appel/manuellement,
avec approbation d'environnement pour la production.

### Exercice 14.2 (pratique) : Exécuter la suite hors ligne localement

À la racine, réactivez l'environnement de l'atelier 00 et installez les
dépendances des ateliers précédents. Ces commandes couvrent les mêmes suites
Python que `continuous-validation.yml`. Inspectez les raisons des omissions
conditionnelles lorsque des SDK facultatifs sont absents.

```powershell
python -m pytest src/quote-preparation-agent/tests -v
python -m pytest eval -v
python -m pytest apps/workshop/tests mcp/application-server/tests mcp/rulebook-server/tests -v
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

La parité est couverte par les tests unitaires et par la porte des données de
référence. Une amélioration seulement anglaise peut rompre le contrat bilingue.
Les juges natifs sont distincts : scores consultatifs, mais preuves complètes
et sans erreur EN/FR obligatoires pour promouvoir. Conservez le 0/10 historique
avec son contrat d'origine.

### Exercice 14.4 : Comprendre la posture d'authentification

```powershell
Select-String -Path .github/workflows/*.yml -Pattern "secrets\." | Select-Object -ExpandProperty Line
```

Résultat attendu : `WIKI_PUSH_TOKEN` est la seule référence `secrets.*`
personnalisée. Les flux utilisent aussi `github.token` intégré pour GitHub
et OIDC pour Azure; les variables contiennent les identifiants de déploiement.

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

Le résultat dépend de la version et du schéma actionlint. Les anciennes versions
signalent `unexpected key "queue"` aux cinq déclarations `concurrency.queue`
des flux de livraison, wiki et démantèlement. Comparez chaque diagnostic à la
déclaration réelle et à la syntaxe Actions prise en charge; les numéros de ligne
ne sont pas une liste d'exemptions. Examinez tout autre constat. Cinq erreurs
arbitraires ne doivent jamais être ignorées parce qu'elles sont cinq.

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

### Exercice 14.8 (pratique) : Tout démanteler

Pour la démonstration conservée, l'exercice reste en lecture seule. Ne supprimez
que votre bac à sable jetable, après approbation explicite du propriétaire et
inventaire. Aucune option ne doit viser le groupe partagé staging/production.
Listez d'abord les environnements et leurs groupes :

```powershell
azd env list
azd env get-value AZURE_RESOURCE_GROUP -e <environment>
```

L'inventaire historique contenait ces deux groupes; ce n'est ni une vérification
d'existence actuelle ni une autorisation de suppression :

| Groupe de ressources | Contenu |
| --- | --- |
| `rg-desjardins-quote-preparation` | Préproduction et production : Foundry, applications conteneurisées, Cosmos DB, le registre de conteneurs et le réseau virtuel |
| `rg-desjardins-quote-preparation-poc` | Un déploiement de validation de principe antérieur |

> [!CAUTION]
> `rg-desjardins-quote-preparation` regroupe la préproduction et la production, c'est précisément pourquoi le flux de l'exercice 14.6 refuse de le supprimer. Le supprimer met fin au pilote pour tout le monde. Les attributions de rôle de l'identité OIDC de GitHub sont limitées à ce groupe et disparaissent avec lui : une reconstruction ultérieure exige qu'une personne administratrice de l'abonnement recrée le groupe et réattribue ces rôles.

**Option A : localement avec azd.** Cette option utilise votre propre connexion Azure : vous devez donc être Contributeur sur le groupe.

```powershell
azd down --force --purge -e <environment>
```

`--force` évite l'invite de confirmation et `--purge` supprime définitivement le compte Foundry et les espaces de travail Log Analytics en suppression réversible, afin que leurs noms soient libres pour un déploiement futur. Si `azd down` n'indique rien à supprimer (par exemple parce que l'environnement a été provisionné par le pipeline plutôt que depuis votre poste), supprimez directement le groupe et purgez vous-même le compte Foundry :

```powershell
az group delete --name <resource-group> --yes
az cognitiveservices account list-deleted --output table
az cognitiveservices account purge --name <account> --resource-group <resource-group> --location <location>
```

**Option B : par le pipeline.** `full-teardown.yml` est le troisième flux de démantèlement. Commencez par un essai à blanc, qui se contente d'inventorier chaque groupe dans le résumé de l'exécution :

```powershell
gh workflow run full-teardown.yml -f target=poc -f confirm=poc
gh workflow run full-teardown.yml -f target=poc -f confirm=poc -f execute=true
```

Résultat attendu : approbation de l'environnement protégé `production`.
La première commande inventorie; la seconde supprime la cible `poc` approuvée.
Les cibles `shared`/`both` existent, mais ne doivent pas viser la démonstration
conservée. L'approbation d'un essai à blanc n'autorise pas une suppression.

Le flux conserve les quatre protections des autres flux de démantèlement et en ajoute une cinquième : les noms de groupes de ressources doivent correspondre à un motif de liste d'autorisation, une variable de dépôt mal saisie ne peut donc pas le diriger vers un groupe sans rapport. Il purge aussi chaque compte Foundry avant de supprimer le groupe, car les rôles de l'identité sont limités au groupe et auraient disparu au moment d'une purge ultérieure.

> [!NOTE]
> Par défaut, l'identité du flux n'a accès qu'à `vars.AZURE_RESOURCE_GROUP`. Une exécution `poc` signale le groupe de validation de principe comme inaccessible et l'ignore avec un avertissement ; accordez d'abord à l'identité le rôle Contributeur sur ce groupe, ou utilisez l'option A. Le flux peut être relancé sans risque : si les groupes sont déjà supprimés, il réussit avec un avertissement et ne supprime rien. Aucune des deux options ne supprime les inscriptions d'application Entra ; retirez celle de la révision avec `scripts/remove-reviewer-identity.ps1`.

## Liste de vérification

* [ ] Vous avez listé les dix flux, dont publication ACR automatique et liaison d'issue
* [ ] Chaque suite de tests locale réussit
* [ ] `python eval/evaluation_gate.py` rapporte `Gate: PASS`
* [ ] Vous distinguez secret wiki personnalisé, jeton GitHub intégré et Azure OIDC
* [ ] Vous avez comparé les diagnostics actionlint au schéma et aux déclarations réelles
* [ ] Vous pouvez nommer les quatre protections précédant les flux de démantèlement
* [ ] Vous pouvez expliquer pourquoi le démantèlement pour reconstruction réseau préserve les comptes Cosmos
* [ ] Vous avez conservé les environnements partagés et identifié l'approbation requise pour supprimer un bac à sable

## Vérification des connaissances

* Comment tests unitaires de parité et porte sur le jeu complet se complètent-ils ?
* Pourquoi une variable de dépôt convient-elle à `AZURE_CLIENT_ID` alors qu'un secret client ne conviendrait pas ?
* Le flux de démantèlement supprime une attribution de rôle AcrPull mais jamais le registre de conteneurs. Pourquoi ?
* Si `execute` vaut false par défaut, que produit réellement une première exécution du flux de démantèlement ?
* Pourquoi la porte d'évaluation déterministe évite-t-elle d'appeler un modèle ?
* Pourquoi le compte Foundry doit-il être purgé et pas seulement supprimé avant que la reconstruction puisse se poursuivre ?
* Pourquoi `full-teardown.yml` purge-t-il le compte Foundry avant de supprimer le groupe de ressources plutôt qu'après ?

## Étapes suivantes

Vous avez terminé la séquence d'exploitation du pilote. Passez à
l'[Atelier 15 : Fichiers et génération native](lab-15-native-files-generation.md)
pour les exercices natifs isolés, en conservant les environnements partagés.

Retournez à l'[index des ateliers](index.md) ou à la [page d'accueil de l'atelier](../index.md).
