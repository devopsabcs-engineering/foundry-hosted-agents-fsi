---
lang: fr
layout: default
title: Fonctions natives Foundry
description: Démonstrations natives de la séance 2, preuves reproductibles, limites de gouvernance et environnements conservés.
nav_order: 20
---

[English](../native-showcase.md) | [Accueil](index.md) | [README français](../../README.fr.md)

[Preuves actuelles de livraison et de reprise des générations, avec captures authentiques](showcase-evidence.md).

Le pipeline sélectionne explicitement l'authentification native azd avant chaque
connexion OIDC GitHub. Le provisionnement peut utiliser Azure CLI en mode délégué,
mais les versions récentes refusent `azd auth login` lorsque ce mode est actif.
Staging et production rétablissent le mode natif avant de renouveler le jeton.

## Conserver la démo restaurée

L'agent actuellement vérifié utilise la version 4 en staging et la version 5
en production. La [livraison 39411002808](https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/actions/runs/39411002808)
a déployé le code approuvé `b0778c7`, avec des digests de chat et de reviewer
identiques entre les environnements, vérifiés indépendamment.
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
| Mémoire | Création, durée de vie, contenu, recherche et test négatif inter-scopes | Modèles de conversation et d'embedding compatibles requis ; staging n'a actuellement que son modèle de conversation |
| Compétence d'exécution | Compétence native versionnée et créée par le projet | Version 1 découverte, téléchargée et consommée par un moteur Responses opérateur isolé ; pas par l'agent hébergé |
| RAG géré | Vector store File Search natif et outil Responses | Six fichiers versionnés indexés ; trois questions EN/FR avec citations natives et deux refus hors corpus |
| Connaissances | Source, base et récupération extractive Azure AI Search GA | Déploiement Search facultatif et isolé ; un index seul n'est pas Foundry IQ |
| Service documentaire | Content Understanding GA, champs et ancrage | Analyseur accessible ; valeurs par défaut absentes et modèles requis non provisionnés |
| Service documentaire préentraîné | Document Intelligence natif `prebuilt-invoice`, GA `2024-11-30` | Extraction réelle réussie : 1 page, 1 document, 8 champs structurés ancrés, sans nouveau modèle |
| Évaluateur intégré | `builtin.retrieval`, version 15 | Staging réel : contexte pertinent 5/5, non pertinent 1/5 |
| Contrôles d'ancrage | `builtin.groundedness` v18 et `builtin.groundedness_pro` v8 | Les deux ont manqué une réponse française erronée connue ; contrôle négatif échoué, sans gain affirmé |
| Red team | Taxonomie native puis évaluation ciblant un agent | Taxonomie créée pour staging v2 ; révision exacte avant toute attaque |
| Traces | Instrumentation déterministe, requête Log Analytics et jeu de rejeu | Ingestion racine vérifiée ; champs d'étapes et rejeu non vérifiés ; identifiants demandés non vérifiés |
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

Staging n'a actuellement aucun embedding; la mémoire native reste non vérifiée.
`infra/memory-showcase.bicep` prépare uniquement le déploiement distinct
`showcase-memory-embedding` sur un compte existant :
`text-embedding-3-small`, version `1`, SKU régional `Standard`, capacité `1`,
sans mise à niveau automatique. Le catalogue du compte accepte ce SKU et le
quota régional East US 2 comporte actuellement 350 unités libres. Vérifiez à
nouveau disponibilité et quota immédiatement avant tout déploiement approuvé.

Ce modèle facultatif est extérieur à `main.bicep` et `azure.yaml`, comme le
modèle showcase isolé existant. Il ne réécrit ni compte, modèle de conversation,
agent, RBAC, réseau, stockage ou production. Ne reprovisionnez pas l'environnement
principal pour ajouter les embeddings. Obtenez l'approbation de l'artefact exact
et de la cible staging, examinez l'aperçu incrémentiel et exigez une seule
création de ressource embedding avant application. Compiler n'est pas déployer.

Après approbation, testez le magasin isolé `showcase-synthetic-memory` avec
`gpt-4o-mini`, cet embedding et une durée par défaut de 3600 secondes selon
l'[Atelier 17](labs/lab-17-native-skills-memory.md). La disponibilité du modèle
ne prouve pas sa compatibilité avec le service mémoire. Conservez tout rejet
explicite, sans remplacer le modèle fonctionnel ni attacher la mémoire à
l'agent de soumission. Une récupération positive et un contrôle inter-scopes
réussis ne prouvent toujours pas le refus d'un agent non autorisé.

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

Après approbation et provisionnement de modèles compatibles, fournissez leurs
noms exacts. Le magasin de démonstration a une durée de vie explicite.

```powershell
$chat = '<déploiement-conversation-compatible>'
$embedding = '<déploiement-embedding-compatible>'
$store = 'showcase-synthetic-memory'
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\memory-create.json" memory-create --store $store --chat-model $chat --embedding-model $embedding --ttl-seconds 3600
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
un échec. La récupération extractive GA `2026-04-01` ne demande pas de nouveau
LLM. La CLI ne crée pas automatiquement une connexion Foundry ni un rattachement
à l'agent existant.

## Utiliser un service documentaire natif

La facture synthétique est rendue en PDF localement, puis analysée par le
service natif, sans faux OCR local. Des champs structurés et un ancrage
inspectable sont obligatoires.

```powershell
$cu = '<point-de-terminaison-Content-Understanding>'
& .venv\Scripts\python.exe scripts\native_knowledge_showcase.py cu-preflight --cu-endpoint $cu
& .venv\Scripts\python.exe scripts\native_knowledge_showcase.py analyze --cu-endpoint $cu --poll-timeout 120
```

Staging retourne actuellement `DefaultsNotSet`. Ne remplacez pas les valeurs
par défaut et n'utilisez pas un modèle incompatible. Le provisionnement des
modèles requis est un changement approuvé distinct ; aucun champ fictif
ne remplace un échec.

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

Le runtime déployé a depuis démontré l'ingestion native de `invoke_agent` dans
les deux environnements. Seule l'invocation hébergée apparaît, sans les champs
personnalisés étape/cas/politique nécessaires au rejeu.
Consultez les [identifiants exacts et les preuves de livraison](showcase-evidence.md#ingestion-native-des-invocations-hébergées).
Une invocation racine ne constitue pas une preuve de provenance utilisable
par `trace-dataset`.

```powershell
$workspace = '<ID-client-Log-Analytics-existant>'
$traceId = '<ID-opération-réel-de-32-caractères>'
& .venv\Scripts\python.exe eval\native_showcase_evaluation.py trace-export --workspace-id $workspace --operation-id $traceId --output-dir "$evidence\trace"
& .venv\Scripts\python.exe eval\native_showcase_evaluation.py trace-dataset --trace-file "$evidence\trace\trace.json" --operation-id $traceId --source-revision $revision --output-dir "$evidence\replay"
& .venv\Scripts\python.exe eval\run_judge_evaluation.py --endpoint $endpoint --agent quote-preparation-agent --version 2 --deployment gpt-4o-mini --dataset "$evidence\replay\replay-dataset.json" --output-dir "$evidence\replayed-evaluation"
```

L'absence de spans provoque un échec. Un `traceparent` demandé reste non vérifié
jusqu'à confirmation native. Le rejeu reconstruit le dossier synthétique,
pas le prompt privé d'origine. Il conserve ID d'opération, hachage de politique,
révision Git et hachage du fichier de trace.

## Red team natif et borné

```powershell
& .venv\Scripts\python.exe eval\native_showcase_evaluation.py taxonomy-create --endpoint $endpoint --agent quote-preparation-agent --agent-version 2 --taxonomy showcase-synthetic-prohibited-actions --output-dir "$evidence\taxonomy"
```

Révisez la taxonomie complète : le service peut générer des catégories
universelles dépassant les seules politiques de non-divulgation de montant
et d'approbation. Une génération réussie n'autorise pas les attaques.
Après révision humaine, fournissez son hachage exact et une seule interaction :

```powershell
$approvedHash = '<SHA-256-de-la-taxonomie-native-exactement-révisée>'
& .venv\Scripts\python.exe eval\native_showcase_evaluation.py red-team --endpoint $endpoint --agent quote-preparation-agent --agent-version 2 --taxonomy showcase-synthetic-prohibited-actions --approved-taxonomy-sha256 $approvedHash --source-revision $revision --turns 1 --output-dir "$evidence\redteam"
```

Seul `ProhibitedActions` est accepté. Aucune catégorie de contenu nocif n'est
demandée. Les résultats et échecs natifs sont conservés ; un délai dépassé
demande l'annulation. Une exécution réussie n'est pas une approbation de sécurité.

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
```

Les présentations [française](../assets/decks/foundry-hosted-agents-workshop-fsi-fr.pptx)
et [anglaise](../assets/decks/foundry-hosted-agents-workshop-fsi-en.pptx) partagent
la même structure et distinguent les exercices locaux de la démo Azure.
La publication wiki conserve son contrôle de provenance de la branche main ;
ne le contournez pas depuis une branche de fonctionnalité. La livraison des
ajouts requiert les approbations Produit, Sécurité et Responsable technique.
Les deux applications Web épinglent maintenant PyJWT 2.15.1 au lieu de la
version vulnérable 2.12.1. Les tests d'authentification et la nouvelle vérification
des avis valident ce changement source, pas les images déployées inchangées.
Revérifiez les alertes après publication et reconstruction.

La configuration CodeQL GitHub existe, mais sa dernière analyse observée
porte sur le commit main `b4ceba0`, pas sur cette branche non publiée.
Aucun scanner SAST ou de secrets local n'est installé. Une ancienne analyse
ne valide pas le nouveau source; exécutez les contrôles configurés sur
la version publiée exacte avant toute livraison.

## Références primaires

* [Compétences natives](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/skills)
* [Mémoire native](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/memory-usage)
* [Bases de connaissances Search](https://learn.microsoft.com/en-us/azure/search/agentic-retrieval-how-to-create-knowledge-base)
* [Content Understanding](https://learn.microsoft.com/en-us/azure/ai-services/content-understanding/overview)
* [Génération synthétique](https://learn.microsoft.com/en-us/azure/foundry/observability/how-to/evaluation-dataset-synthetic)
* [Red team cloud](https://learn.microsoft.com/en-us/azure/foundry/how-to/develop/run-ai-red-teaming-cloud)
* [Azure ML et MLflow](https://learn.microsoft.com/en-us/azure/machine-learning/concept-mlflow?view=azureml-api-2)
