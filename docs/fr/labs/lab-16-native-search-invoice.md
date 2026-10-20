---
permalink: /fr/labs/lab-16-native-search-invoice
lang: fr
title: "Atelier 16 - File Search et extraction de factures"
description: "Interroger le corpus bilingue natif, examiner sources et refus, puis extraire une facture synthétique avec Document Intelligence."
---

[English](../../labs/lab-16-native-search-invoice.md) | [Ateliers](index.md)

## Portée et prérequis

Prévoyez 45 minutes. Terminez l'[Atelier 15](lab-15-native-files-generation.md)
ou obtenez le même environnement Python et l'accès opérateur approuvé à staging.
Utilisez le déploiement `gpt-4o-mini` existant. File Search géré n'exige ni
service Search distinct ni déploiement d'embedding. Faites approuver les frais
d'indexation, de stockage et d'inférence avant les exercices réels.

Tout est synthétique et non contraignant, sans produit, tarif ou police
Desjardins réel. Ne transmettez aucun montant de facture à la réponse du
demandeur, au calcul de tarif ou au dossier d'approbation. Ces appels opérateur
ne modifient ni l'agent hébergé, ni `quote-tools`, ni les environnements déployés.

Depuis la racine du dépôt, créez un nouveau répertoire ignoré par Git :

```powershell
$endpoint = 'https://aif-desjardins-quote-preparation-staging.services.ai.azure.com/api/projects/proj-desjardins-quote-preparation-staging'
$evidence = Join-Path '.local' ('lab16-' + [guid]::NewGuid())
New-Item -ItemType Directory -Path $evidence
& .venv\Scripts\python.exe scripts\native_knowledge_showcase.py validate-corpus
Get-Content data\showcase\knowledge\provenance.json
```

Identifiez les six sources versionnées et leurs hachages. Les sources de
confidentialité sont en version 2, celles de scope et d'approbation en version 1.
Si la validation échoue, n'affaiblissez pas les contrôles et n'indexez pas des
sources modifiées pour continuer.

## Exercice 16.1 : Indexer et interroger les deux langues

```powershell
& .venv\Scripts\python.exe scripts\native_knowledge_showcase.py file-search-create --project-endpoint $endpoint --output "$evidence\native-store.json" --poll-timeout 120
if ($LASTEXITCODE -ne 0) { throw 'Inspect the partial indexing evidence before querying.' }
foreach ($language in @('en', 'fr')) {
    foreach ($scenario in @('approval', 'scope', 'privacy', 'out-of-corpus')) {
        & .venv\Scripts\python.exe scripts\native_knowledge_showcase.py file-search-query --project-endpoint $endpoint --store-evidence "$evidence\native-store.json" --model gpt-4o-mini --language $language --scenario $scenario --output "$evidence\rag-$language-$scenario.json"
        if ($LASTEXITCODE -ne 0) { throw 'Native RAG validation failed; retain the response.' }
    }
}
Get-Content "$evidence\rag-fr-privacy.json"
Get-Content "$evidence\rag-en-out-of-corpus.json"
```

Examinez l'identifiant de chaque réponse native, l'extrait, la citation,
l'appartenance et le hachage source. Les réponses d'approbation, de scope et de
confidentialité doivent citer le bon sujet dans la bonne langue. La
confidentialité ne doit pas prétendre qu'un scope authentifie ou autorise.
Les deux questions non soutenues doivent retourner `OUT_OF_CORPUS`;
une réponse inventée, même plausible, échoue.

Expliquez `source_citations_verified`, `store_membership_verified` et
`validation_state`. Ils vérifient l'attribution, pas l'ancrage sémantique ni
un filtre natif de langue ou d'accès. Un identifiant facultatif de store absent
du résultat est vérifié par la liste native d'appartenance indépendante, jamais
inventé. Conservez la réponse en attente si la validation échoue.

File Search emploie le purpose `assistants`, contrairement au `user_data` de
génération. Le store expire sept jours après sa dernière activité, mais la
conservation des fichiers téléversés est distincte. Ce moteur Responses
opérateur isolé ne constitue ni Foundry IQ ni une preuve de consommation
par l'agent hébergé.

## Exercice 16.2 : Reprendre un index partiel sans retéléversement

Faites cet exercice seulement si la création a échoué après consignation des
six téléversements. Examinez le journal réel et affectez son chemin exact
à `$partialStore`. Ne fabriquez ni journal complet ni panne. Sinon, indiquez
que cette étape est inutile et conservez la preuve du store réussi.

```powershell
$partialStore = '<actual-partial-store-evidence.json>'
& .venv\Scripts\python.exe scripts\native_knowledge_showcase.py file-search-index --project-endpoint $endpoint --store-evidence $partialStore --output "$evidence\resumed-store.json" --poll-timeout 120
```

Après une reprise réussie, utilisez `resumed-store.json` comme `--store-evidence`
pour les requêtes suivantes, avec de nouveaux fichiers de sortie. Un changement
de version source exige un nouveau corpus indexé, pas des preuves incompatibles.

## Exercice 16.3 : Distinguer prérequis documentaire et extraction

Lisez les paramètres Content Understanding avant toute analyse :

```powershell
$invoiceEndpoint = 'https://aif-desjardins-quote-preparation-staging.cognitiveservices.azure.com'
& .venv\Scripts\python.exe scripts\native_knowledge_showcase.py cu-preflight --cu-endpoint $invoiceEndpoint 1> "$evidence\cu-preflight.json" 2> "$evidence\cu-preflight.stderr.txt"
$cuExit = $LASTEXITCODE
Get-Content "$evidence\cu-preflight.json"
Get-Content "$evidence\cu-preflight.stderr.txt"
$cuExit
```

Staging rapporte actuellement `DefaultsNotSet`; les modèles compatibles requis
ne sont pas provisionnés. C'est une limite de prérequis, pas une preuve
d'extraction. Ne modifiez pas les paramètres du compte et ne substituez pas un
modèle de conversation incompatible. Le provisionnement est un changement
approuvé distinct. Si ce changement a déjà été réalisé, la commande `analyze`
du guide est le parcours CU.

Utilisez maintenant le service préentraîné distinct Document Intelligence,
sans modèles génératifs supplémentaires :

```powershell
& .venv\Scripts\python.exe scripts\native_knowledge_showcase.py invoice-analyze --cu-endpoint $invoiceEndpoint --poll-timeout 120 1> "$evidence\invoice.json" 2> "$evidence\invoice.stderr.txt"
if ($LASTEXITCODE -ne 0) { throw 'Invoice extraction failed; inspect the retained service error.' }
Get-Content "$evidence\invoice.json"
```

Le PDF fictif est construit localement; son extraction est native avec
`prebuilt-invoice`, API `2024-11-30`, pas un OCR local. Examinez pages/documents,
identifiant/date, fournisseur/client, articles, sous-total, taxe et total.
Contrôlez confiance et ancrage avec la source synthétique, pas seulement le
statut HTTP. L'extraction historique vérifiée avait 1 page, 1 document et
8 champs structurés; notez vos résultats réels plutôt que recopier ces nombres.

## Preuves de réalisation

* Conservez provenance, store/appartenance et huit réponses EN/FR ou erreurs
  précises, y compris les deux contrôles hors corpus.
* Expliquez pourquoi les citations vérifiées ne prouvent ni sens ni accès autorisé.
* Conservez séparément prérequis CU et facture native; ne présentez pas le
  succès Document Intelligence comme une configuration CU réussie.

Gardez les preuves hors de Git et les ressources partagées disponibles.
Passez à l'[Atelier 17 : Compétences et mémoire](lab-17-native-skills-memory.md).
