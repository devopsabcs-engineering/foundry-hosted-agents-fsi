---
lang: fr
layout: default
title: Fonctions natives Foundry
description: Démonstrations natives de la séance 2, preuves reproductibles, limites de gouvernance et environnements conservés.
nav_order: 20
---

[English](../native-showcase.md) | [Accueil](index.md) | [README français](../../README.fr.md)

[Architecture déployée et schémas d'isolation native](architecture.md)

[Preuves actuelles de livraison et de reprise des générations, avec captures authentiques](showcase-evidence.md).

Le pipeline sélectionne explicitement l'authentification native azd avant chaque
connexion OIDC GitHub. Le provisionnement peut utiliser Azure CLI en mode délégué,
mais les versions récentes refusent `azd auth login` lorsque ce mode est actif.
Staging et production rétablissent le mode natif avant de renouveler le jeton.

## Conserver la démo restaurée

L'agent actuellement vérifié utilise la version 6 en staging et la version 7
en production. La [livraison 39527950931, tentative 2](https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/actions/runs/39527950931)
a déployé le code approuvé `2c3f13b`, avec des digests reviewer et MCP
identiques entre les environnements, vérifiés indépendamment. Le chat conserve
son image vérifiée précédente. Le parcours de correction en production et les
contrôles invocation200/mémoire403 des deux identités reviewer ont réussi.
La [livraison 39293980605, tentative 2](https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/actions/runs/39293980605)
avait restauré la référence v2/v3. Les deux environnements restent
déployés. Ne lancez aucun démantèlement, ne remplacez pas les identités et ne
modifiez pas `quote-tools`. Le suffixe historique `-poc` désigne la production.
Consultez les [liens de déploiement](../../README.fr.md#liens-de-déploiement).

Ce guide répond aux [suivis de la séance 2](../../assets/session2.md).
Les ajouts sont isolés du parcours de soumission existant. Du code écrit,
un enregistrement natif réussi et une consommation réelle à l'exécution sont
trois résultats distincts. Une preuve réelle est nécessaire pour le dernier.

## Ce qui est natif et ce qui reste externe

| Fonction | Implémentation | Limite de vérification |
| --- | --- | --- |
| Agents hébergés | Projet Foundry, version, identité managée et Responses | Staging et production restaurés et vérifiés |
| Fichiers | API Files native, `user_data`, texte synthétique | Téléversement vérifié ; génération à partir de texte, Markdown ou PDF, pas d'un nom JSON |
| Données synthétiques | Job natif, UUID d'opération, statut et téléchargement | Deux jobs rétablis réussis, 6 et 5 lignes téléchargées, maximum demandé de 15 par job ; aucun substitut local |
| Mémoire | Création, durée de vie, contenu, recherche et test négatif inter-scopes | Magasin staging vérifié avec embedding approuvé; refus par rôle 403, pas une ACL par agent |
| Compétence d'exécution | Compétence native versionnée et créée par le projet | Version 1 découverte, téléchargée et consommée par un moteur Responses opérateur isolé ; pas par l'agent hébergé |
| RAG géré | Vector store File Search natif et outil Responses | Six fichiers versionnés indexés ; trois questions EN/FR avec citations natives et deux refus hors corpus |
| Connaissances | Indexation et récupération Search GA, MCP et valeurs de base en préversion | Corpus East US de six documents et valeurs minimal/extractive vérifiés ; IQ staging v2 a réussi 8/8 contrôles natifs bilingues de provenance et de format le 2026-10-22 ; IQ production attend son rôle de requête Search |
| Service documentaire | Content Understanding GA avec alias de modèles par requête | Modèles dédiés `gpt-4.1` et `text-embedding-3-large` et extraction synthétique ancrée vérifiés en staging et production le 2026-10-21, sans modifier les valeurs par défaut |
| Service documentaire préentraîné | Document Intelligence natif `prebuilt-invoice`, GA `2024-11-30` | Extraction réelle réussie : 1 page, 1 document, 8 champs structurés ancrés, sans nouveau modèle |
| Évaluateur intégré | `builtin.retrieval`, version 15 | Staging réel : contexte pertinent 5/5, non pertinent 1/5 |
| Contrôles d'ancrage | `builtin.groundedness` v18 et `builtin.groundedness_pro` v8 | Les deux ont manqué une réponse française erronée connue ; contrôle négatif échoué, sans gain affirmé |
| Red team | Taxonomie native puis évaluation ciblant un agent | Clone staging v2 au hachage original invoqué avec succès ; taxonomie synthétique approuvée puis scannée, mais exécution native échouée sans résultat noté, pas une validation de sécurité |
| Traces | Instrumentation déterministe, requête Log Analytics et jeu de rejeu | Neuf spans réels, trois étapes personnalisées, rejeu natif 1/1; pas de récupération du prompt privé |
| État métier | Cosmos DB et approbation réservée à l'employé | Distinct de la mémoire ; l'agent n'approuve jamais |

Les applications Web et les MCP en lecture seule s'exécutent dans Azure
Container Apps, à l'extérieur du projet Foundry. Search est un service Azure
distinct. Application Insights et Log Analytics constituent le backend
d'observabilité Azure existant.

## Contrat du juge des messages au demandeur

L'ancien jeu de dix cas reste un échec : ses requêtes génériques demandaient
une soumission et des étapes internes, mais la réponse capturée ne contenait
que l'accusé de réception anglais. Ne présentez pas ce résultat comme une
réussite ni comme une amélioration mesurée sur le même jeu.

Le jeu distinct `eval/applicant-message-dataset.jsonl` contient cinq cas
synthétiques et des faits rédigés indépendamment. Il évalue seulement le
message dans la langue sélectionnée, pas les calculs, la persistance ou
l'autorisation internes. Sur la version 4 staging conservée, les cinq cas
anglais et les cinq cas français ont réussi les critères coherence,
groundedness et task adherence, sans erreur d'évaluateur :

* Anglais : `evalrun_7556a65eb27544b7be68fd918979df8d`
* Français : `evalrun_2a731e4ec7d14e8aa03bb300dba6b6fd`

Le contrôle distinct `evalrun_9c0960204b0945e8aa1d713b09f95211` a rejeté
les deux réponses volontairement fausses sur chaque critère : approbation avec
prix inventé et soumission réussie malgré une référence invalide. Aucun seuil
n'a été abaissé. Cela n'efface pas les faux positifs d'ancrage RAG conservés
plus bas. Le pipeline évalue désormais les deux langues et conserve résultats
natifs complets et provenance. Les scores restent consultatifs, mais une preuve
absente, erronée ou incomplète bloque la promotion.

L'URL appelle le déploiement courant; `--version` consigne la version observée
par l'opérateur, sans fixer le routage. Vérifiez le déploiement avant
l'[Atelier 18](labs/lab-18-native-evaluation-traces.md#exercice-185--évaluer-les-messages-observables-au-demandeur).

## Préparer les vérifications en lecture seule

Utilisez le même environnement Python pour toutes les commandes. Le manifeste
racine fixe `azure-ai-projects==2.6.0` ; la version 2.3.0 emploie une autre
méthode de soumission des jobs de génération.

```powershell
& .venv\Scripts\python.exe -m pip install -r requirements.txt
az login
$endpoint = 'https://aif-desjardins-quote-preparation-staging.services.ai.azure.com/api/projects/proj-desjardins-quote-preparation-staging'
$evidence = Join-Path $env:TEMP ('foundry-showcase-' + [guid]::NewGuid())
New-Item -ItemType Directory -Path $evidence
$revision = git rev-parse HEAD
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\preflight.json"
& .venv\Scripts\python.exe scripts\native_knowledge_showcase.py validate-corpus
& .venv\Scripts\python.exe eval\native_showcase_evaluation.py catalog --endpoint $endpoint --output-dir "$evidence\catalog"
```

Les chemins de preuve doivent être nouveaux. Un échec natif retourne un code
non nul et ne doit pas être présenté comme une réussite. L'authentification
utilise Entra, sans secret dans Git. Ces CLI sont réservées aux opérateurs,
jamais exposées directement comme API à un utilisateur.

### Prérequis d'embedding isolé pour la mémoire

Le déploiement staging approuvé `issue20-isolated-memory` a réussi.
`infra/memory-showcase.bicep` provisionne uniquement le déploiement distinct
`showcase-memory-embedding` sur un compte existant :
`text-embedding-3-small`, version `1`, SKU régional `Standard`, capacité `1`,
sans mise à niveau automatique. Réutilisez ce déploiement pour la démo.
Vérifiez disponibilité et quota avant de provisionner une autre cible.

Ce modèle facultatif est extérieur à `main.bicep` et `azure.yaml`, comme le
modèle showcase isolé existant. Il ne réécrit ni compte, modèle de conversation,
agent, RBAC, réseau, stockage ou production. Ne reprovisionnez pas l'environnement
principal pour ajouter les embeddings. Obtenez l'approbation de l'artefact exact
et de la cible staging, examinez l'aperçu incrémentiel et exigez une seule
création de ressource embedding avant application. Compiler n'est pas déployer.

Le magasin isolé `showcase-synthetic-memory` a été testé avec
`gpt-4o-mini`, cet embedding et une durée par défaut de 3600 secondes selon
l'[Atelier 17](labs/lab-17-native-skills-memory.md). Alimentation, liste,
recherche et contrôles inter-scopes ont réussi. Conservez tout rejet
explicite, sans remplacer le modèle fonctionnel ni attacher la mémoire à
l'agent de soumission. La liste mémoire du reviewer existant a reçu HTTP 403,
avec contrôle opérateur positif. Ce refus par rôle ne prouve ni isolation
par agent ni autorisation par scope.

## Fichiers et génération native

Le JSON exporté sert de permis de contenu exact. Le fichier envoyé au service
est un `.txt` combinant le manuel synthétique et le corpus bilingue dont les
hachages sont vérifiés. La finalité `user_data` est requise. Le job produit
des questions techniques, pas des profils de demandeurs ni des tarifs.

```powershell
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint fixture-export --file "$evidence\fixture.json"
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\file.json" file-upload --file "$evidence\fixture.json"
$fileId = (Get-Content "$evidence\file.json" -Raw | ConvertFrom-Json).result.file.id
$operationId = [guid]::NewGuid().ToString()
# Conserver cet UUID et les mêmes entrées pour toute nouvelle tentative.
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\submit.json" generation-submit --name showcase-synthetic-demo-qna --file-id $fileId --model gpt-4o-mini --samples 15 --operation-id $operationId
$jobId = (Get-Content "$evidence\submit.json" -Raw | ConvertFrom-Json).result.job_id
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\status.json" generation-status --job-id $jobId --wait-seconds 120 --poll-seconds 5
$job = (Get-Content "$evidence\status.json" -Raw | ConvertFrom-Json).result.job
$outputFileId = ($job.result.outputs | Where-Object type -EQ file | Select-Object -First 1).id
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\download.json" generation-download --job-id $jobId --file-id $outputFileId --download-file "$evidence\generated.jsonl"
```

Le scénario SDK `supervised_finetuning` permet des sorties natives
téléchargeables. Il ne crée ni entraînement, ni déploiement de modèle, ni
autorisation d'entraîner. Révisez le contenu généré avant utilisation.
Seuls le job réussi et ses sorties réelles prouvent la génération native.

Le job staging vérifié est `datagen-6424fd4d37904cebac2a1bbe9459df86`.
Il a produit 8 exemples pour un maximum demandé de 15. La sortie native
téléchargée a le SHA-256
`dc10f004c929303f1485b33eaf97e83688fc59d47f9d3ca047fe1f4bbe204e48`.
Le service exige une référence autonome suffisamment complète ; les premiers
essais trop petits ont échoué explicitement et ne sont pas comptés comme réussites.

## Contenu réel de la mémoire et segmentation

Réutilisez le magasin staging approuvé sans refaire `memory-create`
(HTTP 409). Pour un nouveau magasin approuvé séparément, utilisez
`gpt-4o-mini`, `showcase-memory-embedding` et une durée de 3600 secondes.
Les entrées expirent après une heure; réalimentez avant la démo avec de
nouveaux chemins de preuve.

```powershell
$store = 'showcase-synthetic-memory'
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\alice-seed.json" memory-seed --store $store --scope fixture-alice
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\bob-seed.json" memory-seed --store $store --scope fixture-bob
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\memory-contents.json" memory-list --store $store --scope fixture-alice
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\memory-isolation.json" memory-search --store $store --scope fixture-alice
```

La recherche doit trouver le marqueur d'Alice dans son scope et ne pas le
trouver dans celui de Bob. Un résultat positif vide échoue. Ce test démontre
une partition de récupération, pas une autorisation : un appelant privilégié
du projet peut sélectionner un autre scope. Liez le scope à l'identité
authentifiée dans l'application et limitez les rôles. Pour une isolation plus
forte, examinez des frontières distinctes de projet ou de magasin.

La mémoire ne remplace ni l'état de soumission, ni l'audit, ni la politique de
rétention Cosmos DB. Le partage d'un scope entre agents n'est pas une liste
de contrôle d'accès par agent. L'intégration à l'agent hébergé nécessite une
vérification de compatibilité distincte.

## Compétence d'exécution sans affirmation trompeuse

La [compétence](../../data/showcase/runtime-skill/SKILL.md) fournit une synthèse
bilingue de l'atelier. Elle est créée par le projet, pas intégrée par Microsoft.
La compétence historique Azure Kusto pour développeurs/Copilot ne prouve pas
l'existence d'une compétence native Foundry prête à exécuter.

```powershell
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\skill.json" skill-register --name showcase-synthetic-bilingual-brief --file data\showcase\runtime-skill\SKILL.md
$skillVersion = (Get-Content "$evidence\skill.json" -Raw | ConvertFrom-Json).result.skill.version
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\skill-toolbox.json" skill-attach --name showcase-synthetic-bilingual-brief --version $skillVersion --toolbox showcase-synthetic-runtime-skills
```

Cette toolbox séparée ne contient aucun outil de production et ne modifie pas
`quote-tools` ni l'agent courant. La preuve conserve `consumed: false`.

Vous pouvez démontrer une consommation réelle sans déployer un autre agent :

```powershell
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\skill-consumed.json" skill-consume --name showcase-synthetic-bilingual-brief --version $skillVersion --model gpt-4o-mini --scope fixture-alice
```

Ce moteur opérateur isolé découvre la compétence dans le catalogue natif et
télécharge sa version immuable. Il accepte uniquement le fichier révisé,
compare ses instructions au dépôt puis transmet ces instructions téléchargées
au modèle existant par Responses, sans outil. La réponse native terminée doit
conserver l'identifiant et la version de compétence dans ses métadonnées.
Le résultat bilingue doit commencer par la langue préférée configurée,
indiquer un exemple synthétique, conserver `approved: false` et ne citer aucun montant.

La réponse staging réelle
`resp_0fe8c263eaea766a006ad690cce8a08190ba6eb665618a7d3e`
a satisfait ces contrôles avec la version 1 et les instructions de SHA-256
`65c5c61f21d1c75f5f82a15b280392d8d20e69cdf57bbac679fec2c2106073df`.
Cette preuve concerne le moteur Responses opérateur, pas l'agent hébergé,
un client MCP de toolbox ni le fournisseur de compétences Agent Framework.
Aucun agent n'est redéployé et aucun état d'approbation ne change.
L'inférence utilise le déploiement existant avec ses frais habituels.

## Connaissances bilingues

### Commencer par File Search natif géré

Le parcours géré vérifié ne demande ni service Search distinct, ni déploiement
d'embedding, ni agent supplémentaire. Il utilise le modèle existant et les six
fichiers du [corpus synthétique](../../data/showcase/knowledge/provenance.json).
Les sources de confidentialité passent à la version 2 : les scopes partitionnent
les données, sans authentifier ni autoriser. Les autres sources restent en version 1.

```powershell
& .venv\Scripts\python.exe scripts\native_knowledge_showcase.py file-search-create --project-endpoint $endpoint --output "$evidence\native-store.json" --poll-timeout 120
foreach ($language in @('en', 'fr')) {
    foreach ($scenario in @('approval', 'scope', 'privacy', 'out-of-corpus')) {
        & .venv\Scripts\python.exe scripts\native_knowledge_showcase.py file-search-query --project-endpoint $endpoint --store-evidence "$evidence\native-store.json" --model gpt-4o-mini --language $language --scenario $scenario --output "$evidence\rag-$language-$scenario.json"
        if ($LASTEXITCODE -ne 0) { throw "Native RAG validation failed" }
    }
}
```

Le store réel versionné est `vs_035lJB6UtY795UZ6oOXOuDi9`. Six réponses
contiennent des citations natives et les deux questions non soutenues renvoient
`OUT_OF_CORPUS`. La réponse française
`resp_0e7dd0761517e6d8006ad6b1bd347081968f41a01de565afcc` cite
`FSI-PRIVACY-FR` et nie explicitement l'authentification et l'autorisation par scope.
Ce moteur opérateur n'est pas l'agent hébergé et ne constitue pas Foundry IQ.

Les fichiers utilisent le purpose natif `assistants`, distinct du `user_data`
de génération. L'appartenance réelle au store, les hachages, extraits, sujets
et langues des citations sont vérifiés. La langue est un contrôle de résultat,
pas un filtre natif ni une frontière d'autorisation. Un identifiant de store
facultatif absent du résultat est vérifié par la liste native d'appartenance.
`source_citations_verified` n'affirme pas un score d'ancrage sémantique.

Le store expire sept jours après sa dernière activité; la conservation des
fichiers téléversés est distincte. Indexation, stockage et inférence ont un coût.
Aucun environnement, agent déployé ou état d'approbation métier ne change.
Les preuves ne sont pas écrasées; les identifiants partiels sont consignés
avant la prochaine opération. Pour reprendre l'indexation après la consignation
des six téléversements :

```powershell
& .venv\Scripts\python.exe scripts\native_knowledge_showcase.py file-search-index --project-endpoint $endpoint --store-evidence "$evidence\partial-store.json" --output "$evidence\resumed-store.json" --poll-timeout 120
```

Utilisez ensuite la preuve reprise pour les requêtes, sans retéléverser
inutilement les fichiers. Une nouvelle version du corpus demande une nouvelle
indexation; l'ancienne référence de génération reste acceptée par son hachage exact.

### Base de connaissances Search facultative

Le [Bicep facultatif](../../infra/showcase.bicep) crée un nouveau service
Search Basic avec Entra seulement, classement sémantique, identité managée et
rôles explicites. Il n'est pas inclus dans le template de référence. Les coûts
récurrents, quotas, région et autorisations doivent être approuvés.

```powershell
$search = 'https://<nouveau-service>.search.windows.net'
$searchId = '/subscriptions/<abonnement>/resourceGroups/<groupe>/providers/Microsoft.Search/searchServices/<nouveau-service>'
$principal = '<ID-objet-opérateur>'
& .venv\Scripts\python.exe scripts\native_knowledge_showcase.py preflight --search-endpoint $search --search-resource-id $searchId --principal-id $principal --for-operation upsert
& .venv\Scripts\python.exe scripts\native_knowledge_showcase.py upsert --search-endpoint $search --search-resource-id $searchId --principal-id $principal
& .venv\Scripts\python.exe scripts\native_knowledge_showcase.py ingest --search-endpoint $search --search-resource-id $searchId --principal-id $principal
& .venv\Scripts\python.exe scripts\native_knowledge_showcase.py query --search-endpoint $search --question 'Who can approve the synthetic quote?' --language en
& .venv\Scripts\python.exe scripts\native_knowledge_showcase.py query --search-endpoint $search --question 'Qui peut approuver la soumission synthétique ?' --language fr
```

Examinez source, base, activité et citations réelles. Une source inconnue,
un hachage modifié, une mauvaise langue ou un extrait non soutenu provoque
un échec. L'indexation, les sources et la récupération extractive directe GA
`2026-04-01` ne demandent pas de nouveau LLM. Les valeurs de la base emploient
`2026-08-01-preview` pour fixer `retrievalReasoningEffort={"kind":"minimal"}`
et `outputMode=extractiveData`. Une définition GA seule laisse une valeur MCP
de préversion pouvant demander un modèle non configuré. Appliquez la correction
`upsert` révisée avant la validation IQ, sans ajouter de modèle de récupération.
La CLI ne crée pas automatiquement une connexion Foundry ni un rattachement
à l'agent existant.

### Enregistrer et vérifier le compagnon IQ natif

Le plan des extensions est approuvé dans
[l'issue 45](https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/issues/45).
Le code, les tests hors ligne, l'approbation de l'artefact exact et la validation
native restent des étapes distinctes. CU a réussi réellement dans les deux
environnements. Search est déployé et le clone isolé a réussi une invocation
native. Les corrections approuvées de la base ont été appliquées après la fusion
de la [PR 47](https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/pull/47),
dont l'arbre correspond exactement au code révisé. La validation IQ et un rapport
red team natif réellement noté restent en attente. Ces limites ne bloquent pas
la démo client v6/v7 inchangée.

```mermaid
flowchart LR
  subgraph Baseline["Demo client inchangee"]
    Quote["Agent de preparation v6 / v7"] --> Cases["Etat metier Cosmos"]
    Employee["Employe authentifie"] --> Cases
  end
  subgraph Extensions["Extensions synthetiques separees"]
    IQ["Compagnon prompt fsi-showcase-iq"] --> Connection["Connexion MCP ProjectManagedIdentity"]
    Connection --> Search["Base Search synthetique"]
    Invoice["Facture PDF synthetique"] --> CU["Content Understanding natif"]
    CU --> Models["Deploiements completion et embedding dedies"]
    Shadow["Clone red team staging"] --> Private["SQLite prive en memoire"]
  end
```

Aucune flèche ne relie les extensions à Cosmos. Le compagnon IQ n'a qu'un
outil MCP de lecture. CU ne calcule ni tarif ni approbation. Le clone red team
doit prouver son stockage isolé avant les attaques. Search Basic en East US
coûte actuellement 0,101 USD/heure, soit environ 73,73 USD pour 730 heures,
plus les usages de modèles, documents, hébergement et évaluations.
Une alerte budgétaire n'est pas un plafond de dépenses.
East US 2 a refusé le nouveau Search avec `InsufficientResourcesAvailable`.
Le service exclusivement synthétique a été déployé en East US au même prix
Basic ; Foundry, CU et la démo existante restent en East US 2.

[La CLI IQ](../../scripts/native_foundry_iq.py) crée un agent prompt séparé,
pas un rattachement au graphe de préparation. Déployez d'abord le template
Search approuvé avec les identités réelles des projets en lecture seulement :
`queryPrincipalType=ServicePrincipal`. Séparez les rôles opérateur/ingestion.
Staging et production peuvent partager ce corpus exclusivement synthétique.

Après l'ingestion des six sources, utilisez le checkout propre de l'artefact
approuvé. L'ID ARM et le point de terminaison doivent désigner le même projet :

```powershell
$projectId = '/subscriptions/<subscription>/resourceGroups/<group>/providers/Microsoft.CognitiveServices/accounts/<account>/projects/<project>'
$env:AZURE_TOKEN_CREDENTIALS = 'AzureCliCredential'
$iqArgs = @('--project-endpoint', $endpoint, '--project-resource-id', $projectId,
            '--search-endpoint', $search, '--search-resource-id', $searchId)
$iqRun = Join-Path $evidence ('iq-' + (Get-Date -Format yyyyMMddTHHmmss))
New-Item -ItemType Directory -Path $iqRun | Out-Null
& .venv\Scripts\python.exe scripts\native_foundry_iq.py preflight @iqArgs --output "$iqRun\preflight.json"
& .venv\Scripts\python.exe scripts\native_foundry_iq.py create @iqArgs --model gpt-4o-mini --source-revision $revision --output "$iqRun\binding.json"
foreach ($language in 'en', 'fr') {
    foreach ($scenario in 'approval', 'scope', 'privacy', 'out-of-corpus') {
        & .venv\Scripts\python.exe scripts\native_foundry_iq.py query @iqArgs --binding "$iqRun\binding.json" --language $language --scenario $scenario --output "$iqRun\$language-$scenario.json"
        if ($LASTEXITCODE -ne 0) { throw "Native IQ acceptance failed: $language/$scenario" }
    }
}
```

La connexion utilise l'API `2025-10-01-preview`, `ProjectManagedIdentity` et
l'audience `https://search.azure.com/`. Le MCP de la base utilise
`2026-08-01-preview` avec le seul outil `knowledge_base_retrieve`.
Une connexion existante dont l'authentification ou la cible diffère n'est
jamais écrasée. Le précontrôle vérifie l'identité du projet et son rôle limité.
La vérification du corpus compare les six documents indexés complets.
La sélection locale utilise Azure CLI authentifiée via `azure-identity` actuel,
sans modifier l'authentification des workloads ni leurs rôles Azure.

Chaque requête épingle la version enregistrée et revérifie définition,
connexion et corpus. Une réponse acceptée contient un véritable appel MCP
terminé. Les citations par ID doivent être pertinentes, dans la même langue,
et retrouver leur marqueur de version dans le résultat natif de l'outil.
Ce contrôle d'ID n'invente pas d'annotations natives et n'est pas un juge
sémantique. Les deux refus hors corpus doivent être exactement
`OUT_OF_CORPUS`. Les réponses brutes restent conservées en cas d'échec.

Le premier lot natif de huit cas du v1 déployé a réussi seulement 1/8.
Les contrôles de requête pris en charge ont ensuite réussi 6/8 : la réponse
anglaise de scope omettait son ID source et le refus anglais ajoutait un point.
Aucun contrôle n'a été assoupli. Un essai de surcharge `instructions` par requête
a reçu HTTP400 pour les huit cas et a été retiré ; ne l'associez pas à
`agent_reference`. La CLI force maintenant l'outil MCP autorisé, conserve la
phase d'échec, accepte une récupération réellement vide seulement pour un refus
hors corpus exact et produit du JSON compatible ASCII sous Windows.

La livraison partielle autorisée
[PR 48](https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/pull/48)
a fusionné en `7c5b1611fcc04da75c77fadd986816e0485f610b` avec l'arbre testé.
Le 2026-10-22, les instructions persistées renforcées de
`c5e1f93f2bfd463bdd1bbc3946c48a29b3c87d26` ont été déployées dans le nouveau
`fsi-showcase-iq:2` staging avec un nouveau binding. Un lot natif complet
a réussi 8/8 : approbation, scope, confidentialité et refus hors corpus exact
en anglais et en français, chacun avec un véritable appel MCP terminé.
Les échecs historiques v1 restent conservés, sans servir de preuve au v2.
Le précontrôle production en lecture seule n'a trouvé aucun rôle direct
`Search Index Data Reader` pour l'identité managée de son projet sur Search.
Aucun compagnon production ni changement de permission n'a été effectué.
Le rôle minimal, la promotion production et la validation native du clone de
protocole sont reportés au
[ticket 49](https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/issues/49).
Le parcours client v6/v7 reste inchangé. Les marqueurs source du scénario en font un
contrôle de provenance et de format, pas une évaluation sémantique indépendante
ni une preuve de fiabilité générale du modèle.

## Utiliser un service documentaire natif

La facture synthétique est rendue en PDF localement, puis analysée par le
service natif, sans faux OCR local. Des champs structurés et un ancrage
inspectable sont obligatoires.

```powershell
$cu = '<point-de-terminaison-Content-Understanding>'
$mapping = '{"prebuilt-analyzer-completion":"fsi-showcase-cu-completion","prebuilt-analyzer-embedding":"fsi-showcase-cu-embedding"}'
& .venv\Scripts\python.exe scripts\native_knowledge_showcase.py cu-preflight --cu-endpoint $cu --model-deployments $mapping
& .venv\Scripts\python.exe scripts\native_knowledge_showcase.py analyze --cu-endpoint $cu --model-deployments $mapping --poll-timeout 120 --output "$evidence\cu-native-invoice.json"
```

Les valeurs par défaut staging inchangées retournent `DefaultsNotSet`. Ne remplacez pas les valeurs
par défaut et n'utilisez pas un modèle incompatible. Le provisionnement des
modèles requis est un changement approuvé distinct. Les déploiements dédiés
sont maintenant vérifiés dans les deux comptes ; utilisez le mappage complet
par requête, pas les valeurs par défaut absentes.

Pour l'extension approuvée, [le template de modèles dédiés](../../infra/content-understanding.bicep)
ajoute seulement `fsi-showcase-cu-completion` (`gpt-4.1`, Standard capacité 10)
et `fsi-showcase-cu-embedding` (`text-embedding-3-large`, Standard capacité 1)
au compte existant. Revérifiez `supportedModels`, les SKU régionaux et le quota
avant chaque déploiement. Ni `gpt-4o-mini` ni les valeurs par défaut du compte
ne sont remplacés.

```powershell
$mapping = '{"prebuilt-analyzer-completion":"fsi-showcase-cu-completion","prebuilt-analyzer-embedding":"fsi-showcase-cu-embedding"}'
& .venv\Scripts\python.exe scripts\native_knowledge_showcase.py cu-preflight --cu-endpoint $cu --model-deployments $mapping
& .venv\Scripts\python.exe scripts\native_knowledge_showcase.py analyze --cu-endpoint $cu --model-deployments $mapping --poll-timeout 120 --output "$evidence\cu-native-invoice.json"
```

Le mappage complet par requête évite entièrement la ressource de valeurs par
défaut non configurée. `DefaultsNotSet` ne devient ni une valeur fictive ni un
repli OCR. L'analyse réelle valide encore la compatibilité modèle/déploiement.
Le fichier de sortie doit être nouveau. Il conserve l'URL d'opération avant
l'attente, les échecs authentiques et vérifie `SYN-REPAIR-001`, la confiance
finie, les spans et les polygones de page. Après expiration du délai,
l'URL reste disponible et l'opération CU distante peut encore s'exécuter.

Le 2026-10-21, l'opération staging `3fba3bf0-7066-4982-902b-f4d61b5d481a`
et l'opération production `a87c001e-9b27-4070-aa1b-4fe86457ee09` ont réussi
le validateur d'extraction inchangé. Après un délai dépassé du processus local
Azure CLI, l'opération staging originale a été reprise et validée, sans
nouvelle soumission payante. Une session azd déjà authentifiée permet aussi
`AZURE_TOKEN_CREDENTIALS=AzureDeveloperCliCredential` lorsque le processus CLI
dépasse son délai local. N'affichez aucun jeton et n'utilisez pas de repli par clé.

Pour montrer un service natif fonctionnel sans ces modèles génératifs
supplémentaires, utilisez l'analyseur de facture Document Intelligence
du compte existant :

```powershell
$invoiceEndpoint = 'https://aif-desjardins-quote-preparation-staging.cognitiveservices.azure.com'
& .venv\Scripts\python.exe scripts\native_knowledge_showcase.py invoice-analyze --cu-endpoint $invoiceEndpoint --poll-timeout 120
```

Il s'agit d'un service Azure AI distinct, pas d'une affirmation que Content
Understanding est configuré. L'extraction réelle comporte identifiant/date,
noms du fournisseur/client, articles, sous-total, taxe et total, avec confiance
et ancrage documentaire. Ces observations de facture synthétique ne sont pas
transmises à la réponse du demandeur, au calcul de tarif ou à l'approbation.

## Évaluer, investiguer et rejouer

```powershell
& .venv\Scripts\python.exe eval\native_showcase_evaluation.py retrieval-compare --endpoint $endpoint --deployment gpt-4o-mini --source-revision $revision --output-dir "$evidence\retrieval"
```

Le jeu de données, les résultats, l'identité native et la comparaison sont
conservés. L'acceptation exige au moins 3/5 pour le contexte pertinent et moins
de 3/5 pour le contrôle non pertinent. Le test réel a obtenu 5 et 1.
Il démontre l'évaluateur, pas une amélioration du RAG de production.

Répétez la commande dans un nouveau répertoire, puis comparez les deux
exécutions natives terminées :

```powershell
& .venv\Scripts\python.exe eval\native_showcase_evaluation.py retrieval-compare --endpoint $endpoint --deployment gpt-4o-mini --source-revision $revision --output-dir "$evidence\retrieval-repeat"
& .venv\Scripts\python.exe eval\native_showcase_evaluation.py compare-runs --baseline-results "$evidence\retrieval\results.json" --candidate-results "$evidence\retrieval-repeat\results.json" --output-dir "$evidence\comparison"
```

La comparaison refuse les jeux de données, versions d'évaluateur ou modèles
juges différents, les exécutions échouées, les identités/hachages manquants
et une exécution comparée à elle-même. Deux exécutions réelles ont obtenu
5/1 chacune, sans variation de score : c'est une preuve de répétabilité,
pas un gain d'optimisation.

### Conserver les contrôles natifs d'ancrage échoués

Une ancienne réponse française affirmait à tort que les scopes autorisent
des actions et citait la source de scope. La confidentialité version 2 et les
contrôles explicites de sujet/source ont corrigé la réponse réelle. Les réponses
EN/FR actuelles ont été relues contre cette source. L'agent hébergé n'a pas changé.

Les deux juges natifs ont pourtant accepté la mauvaise réponse connue :

| Évaluateur natif | Mauvaise référence | Réponse corrigée | Contrôle négatif |
|-----------------|--------------------|------------------|------------------|
| `builtin.groundedness` v18, `gpt-4o-mini` existant | 5/5 | 5/5 | Échec |
| `builtin.groundedness_pro` v8, service géré | `true` | `true` | Échec |

Les exécutions natives sont `evalrun_90768c55e09946809a97eac233d7c4bb` et
`evalrun_8683ff9a323a40de87cbeed5d752def2`. Leurs `input_items` natifs confirment
la même question utilisateur, contrairement aux reformulations de recherche.
Le contexte vient des extraits réellement cités, pas d'une réponse inventée.
Aucun gain d'ancrage ni succès de qualité n'est affirmé.

Pour reproduire avec les réponses natives erronée et corrigée conservées :

```powershell
$badRag = '<retained-known-bad-native-RAG-response.json>'
$fixedRag = '<retained-corrected-native-RAG-response.json>'
& .venv\Scripts\python.exe eval\native_showcase_evaluation.py grounding-compare --endpoint $endpoint --deployment gpt-4o-mini --source-revision $revision --baseline-results $badRag --candidate-results $fixedRag --output-dir "$evidence\grounding"
& .venv\Scripts\python.exe eval\native_showcase_evaluation.py grounding-compare --endpoint $endpoint --grounding-evaluator groundedness_pro --source-revision $revision --baseline-results $badRag --candidate-results $fixedRag --output-dir "$evidence\grounding-pro"
```

Les comparaisons renvoient volontairement un code non nul si la mauvaise réponse
passe. Conservez les échecs. Ne modifiez pas les contrôles pour obtenir du vert,
n'affaiblissez pas les validations pour régénérer une mauvaise réponse et ne
promouvez pas une variante sur le seul score d'un juge.

### Vérifier l'ingestion réelle des traces

Le graphe de soumission est déterministe. `AGENT_TASK_INSTRUCTIONS` est une
métadonnée d'évaluation, pas un prompt système exécuté. Les spans réels
conservent étape, référence synthétique validée, type d'exécution et hachage
de politique. Aucun contenu de demandeur, montant, jeton ou appel LLM inventé
n'est enregistré. L'export utilise le fournisseur de télémétrie existant
après déploiement.

Un export local isolé vers Application Insights staging existant a reçu HTTP 403
pour l'identité opérateur. `force_flush()` ne prouve pas l'ingestion :
la preuve conserve explicitement `trace_verified: false`. L'autorisation de
publication doit suivre le processus d'accès approuvé. Ne retirez pas les
identifiants Entra et n'affaiblissez pas l'authentification pour contourner ce refus.

Le runtime staging v5 approuvé a exporté neuf spans réels pour l'opération
`f63bbcfefd1b3b252a4c343bdc99fd2b`, dont `quote.INTAKE`,
`quote.REFERENCE_LOOKUP` et `quote.COMPOSITION`, avec parents/statuts/politique.
Calcul et persistance sont internes à `COMPOSITION`.
Cherchez les dépendances SDK séparément des racines de requêtes plateforme :
leurs identifiants peuvent différer. Une requête racine seule ne prouve pas
l'absence des étapes. Le rejeu natif a réussi 1/1 sur les trois critères.
Consultez les [preuves actuelles](showcase-evidence.md#traces-personnalisées-et-rejeu-natif-vérifiés).
Ne fournissez pas une racine seule à `trace-dataset`.

```powershell
$workspace = '<ID-client-Log-Analytics-existant>'
$traceId = '<ID-opération-réel-de-32-caractères>'
& .venv\Scripts\python.exe eval\native_showcase_evaluation.py trace-export --workspace-id $workspace --operation-id $traceId --output-dir "$evidence\trace"
& .venv\Scripts\python.exe eval\native_showcase_evaluation.py trace-dataset --trace-file "$evidence\trace\trace.json" --operation-id $traceId --source-revision $revision --output-dir "$evidence\replay"
& .venv\Scripts\python.exe eval\run_judge_evaluation.py --endpoint $endpoint --agent quote-preparation-agent --version 5 --deployment gpt-4o-mini --dataset "$evidence\replay\replay-dataset.json" --output-dir "$evidence\replayed-evaluation"
```

L'absence de spans provoque un échec. Un `traceparent` demandé reste non vérifié
jusqu'à confirmation native. Le rejeu reconstruit le dossier synthétique,
pas le prompt privé d'origine. Il conserve ID d'opération, hachage de politique,
révision Git et hachage du fichier de trace.

## Red team natif et borné

N'attaquez ni l'agent métier actif ni sa file de dossiers. La taxonomie v2 est
historique, pas une autorisation actuelle. Préparez une cible séparée
`fsi-showcase-redteam-*` en staging, avec les mêmes sources approuvées et un
stockage privé en mémoire.

Obtenez la version source avec `AIProjectClient.agents.get_version`. Calculez
son empreinte via `taxonomy_digest(source.definition.as_dict())` dans le runner,
pas en hachant un export JSON indenté. Révisez la définition et son
`code_configuration.content_hash` observé. Les valeurs de routage restent dans
une configuration locale : aucune définition complète ni aucun identifiant
secret dans les preuves. Le commit source d'origine est distinct du nouveau
commit du runner.

```powershell
$shadow = 'fsi-showcase-redteam-quote-001'
$sourcePins = @(
    '--source-agent', 'quote-preparation-agent',
    '--source-agent-version', $sourceVersion,
    '--source-definition-sha256', $reviewedDefinitionSha,
    '--source-content-sha256', $observedNativeContentSha,
    '--source-revision', $originalRuntimeCommit,
    '--source-deployment-provenance', $approvedOriginalRelease
)
$runtime = foreach ($setting in $reviewedSourceRouting.GetEnumerator()) {
    '--runtime-setting'
    '{0}={1}' -f $setting.Key, $setting.Value
}
& .venv\Scripts\python.exe scripts\prepare_redteam_shadow.py --allow-new-code-deployment --staging-endpoint $endpoint @sourcePins --agent $shadow @runtime --timeout 600 --output-dir .local\redteam\prepared-001
if ($LASTEXITCODE -ne 0) { throw 'Local shadow preparation failed' }
```

`$reviewedSourceRouting` ne contient que les valeurs MCP/projet/modèle/Toolbox
présentes dans la source et admises par la liste. La préparation vérifie staging,
supprime Cosmos, l'état externe et les secrets, fixe
`CASE_STORE_DB_PATH=:memory:` et omet la configuration de télémétrie source.
Elle n'affirme pas que les défauts de télémétrie de la plateforme sont désactivés.
Le code hébergé actuel appelle les fixtures MCP en HTTP streamable; conserver
la configuration Toolbox ne prouve pas un autre parcours natif Toolbox.

La préparation matérialise seulement les octets Git approuvés et un manifeste
azd isolé dans `.local`, ignoré par Git. Elle n'exécute jamais azd.
Son chemin `project` est relatif (`source`), comme l'exige azd.

Préférez `shadow-create` pour une source existante basée sur du code. Le SDK
public `download_code` retourne le ZIP original ; `create_version_from_code`
téléverse ce même ZIP avec son SHA-256 vérifié. Le runner compare d'abord le
ZIP à l'empreinte source révisée, retire seulement le champ `content_hash`
en lecture seule de la définition envoyée et vérifie les définitions et
hachages natifs réellement retournés. Il ne remplace jamais l'empreinte attendue
pour faire passer un contrôle.

Après approbation de l'artefact exact :

```powershell
$clone = @('--endpoint', $endpoint, '--staging-endpoint', $endpoint,
           '--agent', $shadow, '--turns', '1', '--timeout', '120') + $sourcePins
& .venv\Scripts\python.exe eval\native_showcase_evaluation.py shadow-create @clone --output-dir "$evidence\shadow-original-package"
if ($LASTEXITCODE -ne 0) { throw 'Keep registration evidence; inspect actual version before retrying' }
```

Une nouvelle version de code peut modifier le défaut du clone isolé seulement,
jamais la démo métier. Si la version s'active encore, observez sa version exacte
puis reprenez `shadow-preflight`, sans recréer. Le ZIP est borné à 250 MB.
Des octets identiques ne prouvent ni les dépendances résolues ni un processus actif.

Le parcours azd ci-dessous est optionnel. Un nouveau ZIP peut différer à cause
des fins de ligne ou des métadonnées de paquet. Un ZIP natif brut n'est pas un
descripteur de paquet azd : `azd deploy --from-package` ne fournissait pas
l'artefact `code-zip` exigé. Préférez le SDK public ; ne relâchez pas l'égalité
des hachages pour accepter un nouveau build.

Après approbation de l'artefact exact, créez un environnement azd local neuf
pour ce workspace, lié au groupe staging existant, puis chargez les paramètres
locaux générés. Déployez seulement le service clone nommé. N'utilisez jamais
le manifeste racine, `azd up`, `provision`, `--all`, production ou le nom métier :

```powershell
$env:AZURE_DEV_USER_AGENT = 'microsoft_foundry_skill'
$prepared = (Resolve-Path .local\redteam\prepared-001).Path
$shadowEnvironment = 'redteam-shadow-staging'
azd env new $shadowEnvironment --cwd $prepared --subscription $stagingSubscription --location eastus2 --no-prompt
if ($LASTEXITCODE -ne 0) { throw 'Fresh staging environment setup failed' }
azd env set AZURE_RESOURCE_GROUP $stagingResourceGroup --cwd $prepared --environment $shadowEnvironment
if ($LASTEXITCODE -ne 0) { throw 'Staging resource-group binding failed' }
azd env set FOUNDRY_PROJECT_ENDPOINT $endpoint --cwd $prepared --environment $shadowEnvironment
if ($LASTEXITCODE -ne 0) { throw 'Staging project binding failed' }
$settings = Get-Content "$prepared\runtime-settings.local.json" -Raw | ConvertFrom-Json
foreach ($setting in $settings.PSObject.Properties) {
    azd env set $setting.Name $setting.Value --cwd $prepared --environment $shadowEnvironment
    if ($LASTEXITCODE -ne 0) { throw 'Staging shadow configuration failed' }
}
azd deploy $shadow --cwd $prepared --environment $shadowEnvironment --timeout 600 --no-prompt
if ($LASTEXITCODE -ne 0) { throw 'Shadow deployment failed; remote build may still run' }
```

Observez la version réelle avec le SDK Projects, pas un défaut azd local
historique. Une version provisionnée `active` n'est pas un processus prouvé
en exécution. Avant invocation, comparez les définitions épinglées :

```powershell
$common = @('--endpoint', $endpoint, '--staging-endpoint', $endpoint,
            '--agent', $shadow, '--agent-version', $shadowVersion,
            '--turns', '1', '--timeout', '120') + $sourcePins
& .venv\Scripts\python.exe eval\native_showcase_evaluation.py shadow-preflight @common --output-dir "$evidence\shadow-preflight"
if ($LASTEXITCODE -ne 0) { throw 'Shadow source/runtime/isolation verification failed' }
azd ai agent invoke $shadow 'CASE-SYN-001' --version $shadowVersion --protocol responses --timeout 120 --cwd $prepared --environment $shadowEnvironment --output raw
if ($LASTEXITCODE -ne 0) { throw 'Shadow activation or actual invocation failed' }
& .venv\Scripts\python.exe eval\native_showcase_evaluation.py taxonomy-create @common --taxonomy synthetic-prohibited-actions --output-dir "$evidence\taxonomy"
```

Les hachages natifs et la définition assainie doivent correspondre : routage,
CPU/mémoire, les deux représentations des protocoles et stockage privé. Les octets Git identiques ou un
téléversement réussi ne remplacent pas ce contrôle. Aucune métadonnée métier
n'est modifiée pour fabriquer une provenance. Chaque nouvelle tentative
demande un chemin de sortie neuf.

Révisez chaque catégorie et sous-catégorie générée. Le service peut produire
des scénarios universels hors de la politique synthétique visée. La taxonomie
du clone v2 générée le 2026-10-21 contient 28 actions universelles, toutes
désactivées. Elle sert à la révision, pas à un scan de la politique synthétique.
Configurez seulement les actions synthétiques interdites visées, exportez de
nouveau la taxonomie native et révisez son nouveau hachage exact. Le runner
refuse un ensemble vide ou entièrement désactivé avant de créer une évaluation.
La génération n'est pas une autorisation. Après approbation humaine du hachage exact :

```powershell
$approvedHash = '<SHA-256-de-la-taxonomie-native-exactement-révisée>'
& .venv\Scripts\python.exe eval\native_showcase_evaluation.py red-team @common --taxonomy synthetic-prohibited-actions --approved-taxonomy-sha256 $approvedHash --output-dir "$evidence\redteam"
```

Seul `ProhibitedActions` est accepté. Aucune catégorie de contenu nocif n'est
demandée. Une interaction et un délai fini ne plafonnent ni les coûts ni tous
les objectifs générés par le service. Les résultats et échecs restent conservés.
Un délai dépassé demande l'annulation et distingue la demande de sa confirmation
réelle pour le bon run. Un délai azd arrête l'attente locale, pas forcément le
build/déploiement Azure. Rapports incomplets, erreurs d'évaluateur et violations
échouent explicitement. `scan_completed`, `report_complete` et `no_violations`
sont distincts, jamais une approbation générale de sécurité.

### Scan approuvé réel et blocage d'exécution

La taxonomie initiale entièrement désactivée reste une preuve historique.
La politique distincte `synthetic-quote-policy-shadow-v2`, version `2.0`,
active trois contrôles synthétiques : divulgation prématurée du montant,
contournement de l'approbation employé et accès aux dossiers hors atelier.
Son SHA-256 natif exact est
`c880c7c706775794f0cf998cf1637b55c27d6f809accb182dfb10582e790fc56`.
L'approbation humaine a précédé son exécution bornée en staging seulement.

L'évaluation `eval_071d7281d7e1468aa39c62616b5adcee`, run
`evalrun_889cdf2fe1d84f11be5d089100164998`, a échoué avec
`red_team_no_results`. Le journal natif détaillé indique trois objectifs
incomplets et une erreur du callback `objective_target` :
`AttributeError: 'NoneType' object has no attribute 'input_tokens'`.
L'invocation Responses hébergée réussie conservée n'a pas d'objet `usage`.
Aucun résultat d'attaque valide n'a été récupéré. Cet échec d'intégration
ne démontre pas que la cible a résisté à toutes les attaques.

Conservez le run échoué, les journaux natifs et la cible immuable originale.
N'inventez pas de nombres de jetons, n'affaiblissez pas les empreintes source
et ne répétez pas un scan facturé sans correction concrète. Une prise en charge
côté service ou une correction de protocole révisée séparément est nécessaire
avant de déclarer la validation red team native. Ne remplacez jamais la cible
par l'agent de soumission en production.

### Clone de protocole épinglé séparément

Un adaptateur testé hors ligne est disponible dans
[redteam_protocol_entrypoint.py](../../scripts/redteam_protocol_entrypoint.py).
Il ne modifie ni le parcours métier ni le clone original. Il sérialise le même
accusé de réception bilingue borné en chaîne JSON, indique la fin et ajoute un
objet `usage` standard aux réponses non diffusées et à l'événement final diffusé.
Le graphe original, la tarification, les contrôles d'approbation et les fichiers
originaux restent inchangés.

Zéro jeton du modèle propre est exact uniquement parce que cet adaptateur choisit
explicitement le `default_model` original sans appel réseau et vérifie le hachage
normalisé du graphe
`bd25b1e5c627802521ff178fa5bfea20e42d3a3d1063b1fe9357ed48c76a83ee`.
Toute modification de ce graphe bloque le démarrage et la préparation. Zéro ne
décrit pas les modèles évaluateurs du service red team, l'utilisation de la
plateforme ni les coûts. Ce clone déterministe ne constitue pas une preuve de
sécurité pour un autre agent reposant sur un LLM.

Préparez l'artefact dérivé localement avec
[redteam_protocol_package.py](../../scripts/redteam_protocol_package.py).
Fournissez le ZIP original obtenu par le SDK, son empreinte source révisée
indépendamment, ainsi que la révision et le hachage de fichier de l'adaptateur
révisés séparément. Exécutez depuis cette révision Git exacte :

```powershell
$protocolRevision = '<reviewed-full-Git-SHA>'
$protocolEntrypointSha = '<reviewed-entrypoint-SHA-256>'
$protocolPreparation = '.local\redteam\protocol-preparation-001'
& .venv\Scripts\python.exe scripts\redteam_protocol_package.py --source-zip $reviewedOriginalZip --source-content-sha256 $observedNativeContentSha --protocol-revision $protocolRevision --protocol-entrypoint-sha256 $protocolEntrypointSha --output-dir $protocolPreparation
if ($LASTEXITCODE -ne 0) { throw 'Protocol preparation failed; preserve original evidence' }
$protocolProof = Get-Content "$protocolPreparation\protocol-preparation.json" -Raw | ConvertFrom-Json
```

La préparation ajoute un seul point d'entrée révisé, préserve chaque membre du
ZIP original, refuse les archives dangereuses et consigne un hachage dérivé
déterministe distinct. `immutable_artifact_equality` vaut explicitement false.
Révisez le nouveau hachage et sa provenance avant toute approbation d'écriture
cloud. Ne réemballez pas avec azd en supposant conserver le même hachage.

Uniquement après approbation du déploiement de l'artefact exact :

```powershell
$protocolPins = @('--protocol-revision', $protocolRevision,
                  '--protocol-entrypoint-sha256', $protocolEntrypointSha,
                  '--protocol-content-sha256', $protocolProof.target_content_sha256)
$protocolCommon = @('--endpoint', $endpoint, '--staging-endpoint', $endpoint,
                     '--agent', 'fsi-showcase-redteam-protocol-quote-001',
                     '--turns', '1', '--timeout', '120') + $sourcePins + $protocolPins
& .venv\Scripts\python.exe eval\native_showcase_evaluation.py shadow-create @protocolCommon --output-dir "$evidence\protocol-registration-001"
if ($LASTEXITCODE -ne 0) { throw 'Inspect recorded registration before any retry' }
```

Observez cette nouvelle version exacte ; reprenez `shadow-preflight` avec les
mêmes trois empreintes de protocole et `--agent-version`, puis vérifiez une
invocation Responses hébergée réelle. Un test local ou un enregistrement réussi
ne constitue pas une validation native. Créez une taxonomie distincte visant ce
nouveau clone, exportez et révisez son hachage natif persisté et obtenez
l'approbation humaine du scan. L'approbation `c880c7c7` vise le clone original,
pas cette nouvelle cible. Conservez le run échoué et les deux provenances.

## Suivi d'expériences et recommandation

Commencez par les comparaisons Foundry et les traces Azure réelles. Conservez
révision Git, hachage du runner, version d'évaluateur, modèle, hachage du jeu
de données, paramètres, ID natifs et traces vérifiées. Comparez les variantes
avec le même jeu de données et la même configuration d'évaluation.

Les évaluations Foundry ne sont pas simplement MLflow renommé. Azure ML offre
un backend compatible MLflow ; cela ne confirme pas un écran Experiments
équivalent dans Foundry. Ajoutez Langfuse, Phoenix ou MLflow seulement pour
un besoin mesuré non satisfait, avec coûts, accès, rétention et frontière
de données approuvés. Aucune plateforme externe n'est installée ici.

## Validation et publication

```powershell
& .venv\Scripts\python.exe -m pytest eval src\quote-preparation-agent\tests -q
az bicep build --file infra\showcase.bicep --stdout
npm run build-workshop-deck
npm run build-evaluation-deck
```

Les présentations [française](../assets/decks/foundry-hosted-agents-workshop-fsi-fr.pptx)
et [anglaise](../assets/decks/foundry-hosted-agents-workshop-fsi-en.pptx) partagent
la même structure et distinguent les exercices locaux de la démo Azure.
Poursuivez avec le [guide d'évaluation](evaluation-guide.md) et
l'[Atelier 19](labs/lab-19-evaluation-engineering.md) pour les captures conservées,
les JSONL synthétiques rédigés et les présentations d'évaluation distinctes.
La publication wiki conserve son contrôle de provenance de la branche main ;
ne le contournez pas depuis une branche de fonctionnalité. La livraison des
ajouts requiert les approbations Produit, Sécurité et Responsable technique.
Les deux applications Web épinglent maintenant PyJWT 2.15.1 au lieu de la
version vulnérable 2.12.1. Les tests d'authentification et la nouvelle vérification
des avis valident ce changement source, pas les images déployées inchangées.
Revérifiez les alertes après publication et reconstruction.

CodeQL GitHub et les contrôles hors ligne sont configurés. Une ancienne
exécution main réussie ne valide pas le nouveau source des extensions.
Exigez les contrôles sur la version exacte révisée avant livraison, puis
les preuves natives réelles, pas seulement les simulations SDK hors ligne.

## Références primaires

* [Compétences natives](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/skills)
* [Mémoire native](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/memory-usage)
* [Bases de connaissances Search](https://learn.microsoft.com/en-us/azure/search/agentic-retrieval-how-to-create-knowledge-base)
* [Content Understanding](https://learn.microsoft.com/en-us/azure/ai-services/content-understanding/overview)
* [Génération synthétique](https://learn.microsoft.com/en-us/azure/foundry/observability/how-to/evaluation-dataset-synthetic)
* [Red team cloud](https://learn.microsoft.com/en-us/azure/foundry/how-to/develop/run-ai-red-teaming-cloud)
* [Azure ML et MLflow](https://learn.microsoft.com/en-us/azure/machine-learning/concept-mlflow?view=azureml-api-2)
