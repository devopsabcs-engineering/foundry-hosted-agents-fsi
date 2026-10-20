---
permalink: /fr/labs/lab-17-native-skills-memory
lang: fr
title: "Atelier 17 - Compétences d'exécution et frontières mémoire"
description: "Enregistrer et consommer la compétence du projet dans un moteur isolé, puis distinguer segmentation mémoire et autorisation."
---

[English](../../labs/lab-17-native-skills-memory.md) | [Ateliers](index.md)

## Portée et prérequis

Prévoyez 40 minutes. Terminez l'[Atelier 16](lab-16-native-search-invoice.md)
ou obtenez le même environnement Python et l'accès opérateur approuvé à staging.
La compétence utilise `gpt-4o-mini` existant avec ses frais d'inférence.
L'exercice mémoire réutilise les modèles staging approuvés séparément et le
magasin isolé existant `showcase-synthetic-memory`.

Tout est synthétique et non contraignant, sans produit, tarif ou police
Desjardins réel. Ne modifiez ni agent hébergé, ni `quote-tools`, ni état métier
Cosmos DB, ni approbation réservée à l'employé. Ne déployez pas de modèle
pour débloquer l'exercice. Depuis PowerShell à la racine du dépôt :

```powershell
$endpoint = 'https://aif-desjardins-quote-preparation-staging.services.ai.azure.com/api/projects/proj-desjardins-quote-preparation-staging'
$evidence = Join-Path '.local' ('lab17-' + [guid]::NewGuid())
New-Item -ItemType Directory -Path $evidence
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\preflight.json"
Get-Content data\showcase\runtime-skill\SKILL.md
```

La compétence est créée par ce projet, pas fournie par Microsoft comme
compétence native d'exécution. L'ancienne compétence Azure Kusto pour
développeurs/Copilot est un autre artefact. Lisez les contraintes de sortie
avant tout appel d'inférence.

## Exercice 17.1 : Enregistrer et rattacher sans prétendre consommer

```powershell
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\skill.json" skill-register --name showcase-synthetic-bilingual-brief --file data\showcase\runtime-skill\SKILL.md
$skillVersion = (Get-Content "$evidence\skill.json" -Raw | ConvertFrom-Json).result.skill.version
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\skill-toolbox.json" skill-attach --name showcase-synthetic-bilingual-brief --version $skillVersion --toolbox showcase-synthetic-runtime-skills
Get-Content "$evidence\skill-toolbox.json"
```

Notez identifiant/version natifs et nom de la toolbox distincte. La preuve
doit conserver `consumed: false` : une entrée de catalogue ou un rattachement
n'est pas une invocation. La toolbox séparée ne contient pas d'outil de
production et ne modifie ni `quote-tools` ni l'agent courant. Tous les chemins
de sortie doivent être nouveaux.

## Exercice 17.2 : Prouver la consommation par le moteur opérateur isolé

```powershell
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\skill-consumed.json" skill-consume --name showcase-synthetic-bilingual-brief --version $skillVersion --model gpt-4o-mini --scope fixture-alice
if ($LASTEXITCODE -ne 0) { throw 'Skill consumption failed; retain the native error.' }
Get-Content "$evidence\skill-consumed.json"
```

Suivez la preuve depuis la découverte native jusqu'au téléchargement immuable,
puis l'appel Responses terminé. La CLI compare les instructions téléchargées
au fichier révisé du dépôt et les envoie au modèle existant sans outil.
Vérifiez SHA-256, identifiant de réponse et métadonnées exactes
d'identifiant/version, au lieu de déduire la consommation de l'enregistrement.

Examinez la sortie bilingue réelle : langue préférée en premier, désignation
synthétique, `approved: false` et aucun montant. La preuve d'exécution réussie
rapporte `consumed: true`; le rattachement antérieur reste faux. Une validation
de sortie échouée reste un échec.

Identifiez le moteur exécutant : Responses opérateur isolé, pas agent hébergé,
client MCP de toolbox ou fournisseur de compétences Agent Framework.
Aucun déploiement ni approbation métier ne change.

## Exercice 17.3 : Vérifier les prérequis mémoire approuvés

Lisez `preflight.json` et relevez les déploiements disponibles. Comparez-les
aux entrées de conversation et d'embedding exigées :

```powershell
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint memory-create --help
```

Staging dispose maintenant de `gpt-4o-mini` et de `showcase-memory-embedding`
(`text-embedding-3-small`, version `1`). Le magasin isolé utilise une durée
de vie par défaut de 3600 secondes, sans extraction de profil utilisateur
ni résumé de conversation; l'extraction procédurale reste activée par défaut
côté service. Ce sont les paramètres du magasin existant
`showcase-synthetic-memory`, pas des garanties de la commande générique
`memory-create`, qui définit modèles et TTL. L'alimentation synthétique directe
est distincte de l'extraction automatique.
Alimentation, liste et recherche natives ont réussi, contrairement à l'ancien
blocage de prérequis. Une liste de modèles ne prouve pas le fonctionnement.
Ne substituez pas un modèle de conversation à l'embedding et ne redéployez
pas l'infrastructure principale.

## Exercice 17.4 : Tester les namespaces après approbation des prérequis

Réutilisez le magasin staging approuvé existant sans le recréer (HTTP 409).
Pour une autre cible approuvée seulement, créez un nouveau magasin isolé
avec les modèles ci-dessus et `--ttl-seconds 3600`. Ces commandes réalimentent
les entrées expirées après une heure et conservent de nouvelles preuves,
sans modifier la configuration du magasin :

```powershell
$store = 'showcase-synthetic-memory'
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\alice-seed.json" memory-seed --store $store --scope fixture-alice
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\bob-seed.json" memory-seed --store $store --scope fixture-bob
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\memory-contents.json" memory-list --store $store --scope fixture-alice
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\memory-isolation.json" memory-search --store $store --scope fixture-alice
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\bob-isolation.json" memory-search --store $store --scope fixture-bob
Get-Content "$evidence\memory-isolation.json"
```

Arrêtez à la première erreur. Examinez `positive`, `negative`, `scope`,
`negative_scope` et `scope_negative_check`. Le marqueur d'Alice doit être trouvé
dans son scope et absent de celui de Bob. Un résultat positif vide échoue;
attendez l'indexation et reprenez vers un nouveau fichier plutôt que déclarer
un magasin vide isolé. Les alimentations séquentielles réutilisent le contenu
identique, mais les appels concurrents ne sont pas atomiques.

Même réussi, ce test prouve une partition de récupération, pas l'autorisation.
Un appelant privilégié du projet peut choisir un autre namespace. Liez le
scope à l'identité authentifiée, limitez les rôles et envisagez des frontières
de projet/magasin distinctes pour renforcer l'isolation. N'acceptez jamais
de scope arbitraire d'un chatbot. Un scope partagé n'est pas une liste
d'accès par agent.

Le contrôle d'autorisation conservé utilise l'identité existante du reviewer
staging : acquisition de jeton réussie, puis liste mémoire refusée HTTP 403.
L'opérateur autorisé a lu l'entrée comme contrôle positif.
Ce refus par rôle d'appelant/projet ne prouve pas une ACL par agent.
Ne modifiez pas RBAC et n'exposez aucun jeton pour le reproduire. Consultez
les [preuves](../showcase-evidence.md#mémoire-isolée-vérifiée).

La durée de vie mémoire n'est pas la rétention Cosmos DB. La mémoire ne fait
autorité ni pour la soumission ni pour l'audit. Elle n'est pas rattachée à
l'agent de soumissions. Tout rattachement futur exige une vérification de
compatibilité d'exécution et une approbation distinctes.

## Preuves de réalisation

* Conservez enregistrement et rattachement séparément de la consommation.
* Notez réponse native, version immuable, hachage des instructions et contrôles
  bilingues, ou l'erreur exacte.
* Conservez les recherches positives et négatives inter-scopes dans les deux sens.
* Distinguez refus par rôle 403 et partitionnement; notez l'expiration après
  une heure et réalimentez avant une démonstration.
* Expliquez pourquoi un namespace ne donne ni approbation ni autorisation.

Gardez les preuves sous `.local`, ignoré par Git; aucun démantèlement requis.
Passez à l'[Atelier 18 : Évaluation et rejeu](lab-18-native-evaluation-traces.md).
