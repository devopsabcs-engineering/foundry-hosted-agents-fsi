---
permalink: /fr/labs/lab-15-native-files-generation
lang: fr
title: "Atelier 15 - Fichiers et génération native"
description: "Téléverser la référence synthétique révisée, examiner les sorties natives et diagnostiquer les anciens jobs échoués sans substitut local."
---

[English](../../labs/lab-15-native-files-generation.md) | [Ateliers](index.md)

## Portée et prérequis

Prévoyez 40 minutes. Terminez l'[Atelier 00](lab-00-setup.md) et obtenez
l'accès opérateur approuvé au projet staging existant. Utilisez son environnement
Python avec `azure-ai-projects==2.6.0`, vos identifiants Entra et un modèle
de base compatible avec la génération. Exécutez PowerShell depuis la racine du
dépôt. La CLI opérateur n'est pas une API destinée aux utilisateurs.

Les données et résultats sont synthétiques et non contraignants, sans représenter
des produits, tarifs ou polices Desjardins réels. La génération consomme de la
capacité et peut entraîner des frais. Ne déployez rien, ne modifiez pas
`quote-tools`, ne remplacez pas les agents restaurés et ne lancez aucun
démantèlement. Staging v5 et production v6 approuvés restent disponibles.

Créez un nouveau répertoire de preuves dans `.local`, ignoré par Git. Utilisez
un répertoire neuf à chaque tentative; n'écrasez aucune preuve.

```powershell
$endpoint = 'https://aif-desjardins-quote-preparation-staging.services.ai.azure.com/api/projects/proj-desjardins-quote-preparation-staging'
$evidence = Join-Path '.local' ('lab15-' + [guid]::NewGuid())
New-Item -ItemType Directory -Path $evidence
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\preflight.json"
```

Examinez les déploiements et avertissements retournés. Cette vérification est
en lecture seule, sans prouver la compatibilité de génération. Si l'accès échoue,
conservez l'erreur et arrêtez les exercices réels, sans sortie locale de remplacement.

## Exercice 15.1 : Distinguer le permis de la référence téléversée

```powershell
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint fixture-export --file "$evidence\fixture.json"
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\file.json" file-upload --file "$evidence\fixture.json"
Get-Content "$evidence\file.json"
$fileId = (Get-Content "$evidence\file.json" -Raw | ConvertFrom-Json).result.file.id
```

Lisez la preuve de téléversement. Le JSON est un permis de contenu exact,
pas la référence envoyée au service. La CLI construit une référence `.txt`
compatible comprenant le manuel figé, le corpus bilingue aux hachages vérifiés
et 26 leçons autonomes indépendantes dans `data\showcase\generation-reference.txt`,
avec le purpose `user_data`. Notez l'identifiant natif et les hachages sources.
Un export local réussi ne suffit pas à valider cette étape.

## Exercice 15.2 : Soumettre, suivre et examiner la sortie native

Générez des questions techniques d'atelier, jamais des profils de demandeurs
ni des tarifs. Conservez l'UUID et les entrées exactes avant la soumission.
Réutilisez-les pour reprendre une soumission, mais choisissez un nouveau nom
de preuve au lieu d'écraser `submit.json`.

```powershell
$operationId = [guid]::NewGuid().ToString()
$operationId | Set-Content "$evidence\operation-id.txt"
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\submit.json" generation-submit --name showcase-synthetic-demo-qna --file-id $fileId --model gpt-4o-mini --samples 15 --operation-id $operationId
$jobId = (Get-Content "$evidence\submit.json" -Raw | ConvertFrom-Json).result.job_id
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\status.json" generation-status --job-id $jobId --wait-seconds 120 --poll-seconds 5
if ($LASTEXITCODE -ne 0) { throw 'Inspect the native job error before continuing.' }
$job = (Get-Content "$evidence\status.json" -Raw | ConvertFrom-Json).result.job
if ($job.status -ne 'succeeded') { throw 'Download requires a succeeded native job.' }
$outputFileId = ($job.result.outputs | Where-Object type -EQ file | Select-Object -First 1).id
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint --output "$evidence\download.json" generation-download --job-id $jobId --file-id $outputFileId --download-file "$evidence\generated.jsonl"
Get-FileHash "$evidence\generated.jsonl" -Algorithm SHA256
Get-Content "$evidence\generated.jsonl" | Measure-Object -Line
```

Notez le statut, l'identifiant de sortie, le hachage et le nombre réel; examinez
les affirmations avant utilisation. Quinze est le maximum demandé, pas un nombre
garanti. Les jobs récupérés `datagen-a866fd3be0104ae4b6ec4808b76cbec2` et
`datagen-afe38ec64fb744a09e845119139e4064` ont réussi avec 6 et 5 exemples
respectivement, chacun pour un maximum demandé de 15. Ne présentez pas
ces résultats historiques comme votre exécution.
Examinez identifiants de sortie et SHA-256 téléchargés dans les
[preuves de récupération](../showcase-evidence.md).
Ces résultats API/téléchargement sont distincts des captures Foundry réalisées
indépendamment et de la livraison approuvée. Consultez la
[livraison actuelle](../showcase-evidence.md#livraison-approuvée-actuelle);
un résultat de génération ne prouve pas la version de l'agent. Les approbations
restent distinctes.
Le scénario SDK `supervised_finetuning` permet les sorties téléchargeables;
il ne crée ni entraînement, ni déploiement, ni autorisation d'entraîner.

## Exercice 15.3 : Diagnostiquer un ancien job échoué

Lisez le job initial échoué `datagen-4e74a27bd5f24a87a08ea35ad788c8cb`
(référence inférieure à 1 Ko). Répétez avec
`datagen-af8399a33bd7477b8279591b5a408c7a` (contexte autonome insuffisant),
en choisissant un nouveau nom de fichier stderr. N'inventez pas d'identifiant
et ne soumettez pas volontairement un mauvais job. Sans accès à la preuve
historique, consignez l'exercice comme bloqué.

```powershell
$failedJobId = 'datagen-4e74a27bd5f24a87a08ea35ad788c8cb'
& .venv\Scripts\python.exe scripts\native_foundry_showcase.py --endpoint $endpoint generation-status --job-id $failedJobId 2> "$evidence\historical-failure.stderr.txt"
$failureExit = $LASTEXITCODE
Get-Content "$evidence\historical-failure.stderr.txt"
$failureExit
```

Un job échoué ou annulé retourne un code non nul et un diagnostic avec
identifiant, statut et erreur du service, pas un résultat JSON réussi.
Une erreur 404 ou d'autorisation prouve seulement que le job est illisible.
Rapprochez l'erreur du format et de la taille de référence dans la soumission
conservée. Les petites références initiales ont échoué, y compris les premières
reprises avec l'ancienne source; ces échecs restent conservés. La référence
récupérée contient 26 leçons autonomes et 19 881 octets. Dépasser le minimum
de 1 Ko ne prouve pas que le contexte autonome suffit au service pour produire
des exemples utilisables. La génération accepte texte, Markdown ou PDF, pas les
noms de fichiers JSON. Ne comptez pas les échecs comme réussites et ne fabriquez
aucun substitut local.

Si votre nouveau job reste en attente après le délai, gardez son UUID et son
identifiant, puis reprenez `generation-status` vers un nouveau chemin de preuve.
Un délai de suivi dépassé ne justifie pas une nouvelle soumission.

## Preuves de réalisation

* Conservez prérequis, téléversement natif, UUID, soumission, statut réussi,
  sortie native et SHA-256, ou l'erreur bloquante précise.
* Conservez séparément le code de sortie et le diagnostic de l'ancien échec.
* Expliquez la différence entre téléversement, génération et droit d'entraîner.

Gardez les preuves synthétiques hors de Git. Ne supprimez pas les ressources
partagées. Passez à l'[Atelier 16 : File Search et factures](lab-16-native-search-invoice.md).
