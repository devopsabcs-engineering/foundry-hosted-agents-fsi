---
permalink: /fr/labs/lab-18-native-evaluation-traces
lang: fr
title: "Atelier 18 - Évaluation native et rejeu des traces"
description: "Comparer les contrôles natifs, conserver les échecs d'ancrage et rejouer seulement des traces déterministes réellement ingérées."
---

[English](../../labs/lab-18-native-evaluation-traces.md) | [Ateliers](index.md)

## Portée et prérequis

Prévoyez 50 minutes. Terminez l'[Atelier 17](lab-17-native-skills-memory.md)
et conservez les preuves File Search de l'[Atelier 16](lab-16-native-search-invoice.md).
Utilisez l'environnement Python existant, l'accès opérateur Entra et un budget
d'évaluation/inférence approuvé. Depuis la racine du dépôt :

```powershell
$endpoint = 'https://aif-desjardins-quote-preparation-staging.services.ai.azure.com/api/projects/proj-desjardins-quote-preparation-staging'
$evidence = Join-Path '.local' ('lab18-' + [guid]::NewGuid())
New-Item -ItemType Directory -Path $evidence
$revision = git rev-parse HEAD
& .venv\Scripts\python.exe eval\native_showcase_evaluation.py catalog --endpoint $endpoint --output-dir "$evidence\catalog"
```

Tout est synthétique et non contraignant, sans produit, tarif ou police
Desjardins réel. La découverte du catalogue n'est pas un succès d'évaluation.
Ces exercices ne déploient pas d'agent, ne changent pas les approbations et
n'autorisent aucune livraison. Gardez les preuves hors de Git avec des
chemins nouveaux pour chaque exécution.

## Exercice 18.1 : Mesurer les contrôles de récupération

```powershell
& .venv\Scripts\python.exe eval\native_showcase_evaluation.py retrieval-compare --endpoint $endpoint --deployment gpt-4o-mini --source-revision $revision --output-dir "$evidence\retrieval"
if ($LASTEXITCODE -ne 0) { throw 'Inspect failed retrieval controls before continuing.' }
& .venv\Scripts\python.exe eval\native_showcase_evaluation.py retrieval-compare --endpoint $endpoint --deployment gpt-4o-mini --source-revision $revision --output-dir "$evidence\retrieval-repeat"
if ($LASTEXITCODE -ne 0) { throw 'Inspect the repeated run before comparison.' }
& .venv\Scripts\python.exe eval\native_showcase_evaluation.py compare-runs --baseline-results "$evidence\retrieval\results.json" --candidate-results "$evidence\retrieval-repeat\results.json" --output-dir "$evidence\comparison"
Get-Content "$evidence\comparison\run-comparison.json"
```

Ouvrez chaque exécution native réelle dans Foundry. Notez hachage du jeu,
révision Git, identifiants d'exécution/évaluation, version d'évaluateur et
déploiement du juge. `builtin.retrieval` version 15 accepte le contexte pertinent
à partir de 3/5 et exige moins de 3/5 pour le contexte non pertinent.
Examinez jeu et sorties individuelles, pas seulement une capture.
Historiquement les deux exécutions ont obtenu 5/1, delta nul : répétabilité,
pas amélioration. Consignez vos scores sans présumer ce même résultat.

La comparaison refuse une exécution comparée à elle-même, les exécutions
échouées, les jeux/versions/juges différents et les identités ou hachages
manquants. Comme contrôle négatif hors ligne, essayez l'auto-comparaison :

```powershell
& .venv\Scripts\python.exe eval\native_showcase_evaluation.py compare-runs --baseline-results "$evidence\retrieval\results.json" --candidate-results "$evidence\retrieval\results.json" --output-dir "$evidence\self-comparison" 2> "$evidence\self-comparison.stderr.txt"
$selfExit = $LASTEXITCODE
Get-Content "$evidence\self-comparison.stderr.txt"
$selfExit
```

Exigez un code non nul et le diagnostic précis de même exécution. Un fichier
manquant n'est pas le contrôle voulu. Cette démonstration de juge ne prouve
ni un RAG dans l'agent hébergé ni un gain de récupération en production.

## Exercice 18.2 : Conserver les faux positifs des juges d'ancrage

Obtenez les réponses RAG natives erronée et corrigée auprès du responsable des
preuves. La mauvaise réponse française affirmait à tort que les scopes
autorisent des actions. N'affaiblissez pas les contrôles source/sujet, ne
modifiez pas les réponses natives et n'inventez pas une référence pour la
régénérer. Sans ces artefacts, consignez le blocage et analysez les
[preuves conservées](../native-showcase.md#conserver-les-contrôles-natifs-dancrage-échoués).

Examinez les deux réponses et leurs `input_items` natifs : la question
utilisateur d'origine doit correspondre, pas seulement les reformulations.
Comparez chaque réponse aux extraits réellement cités et à la confidentialité
version 2. Avec ces chemins conservés exacts, exécutez les deux juges :

```powershell
$badRag = '<retained-known-bad-native-RAG-response.json>'
$fixedRag = '<retained-corrected-native-RAG-response.json>'
& .venv\Scripts\python.exe eval\native_showcase_evaluation.py grounding-compare --endpoint $endpoint --deployment gpt-4o-mini --source-revision $revision --baseline-results $badRag --candidate-results $fixedRag --output-dir "$evidence\grounding"
$groundingExit = $LASTEXITCODE
& .venv\Scripts\python.exe eval\native_showcase_evaluation.py grounding-compare --endpoint $endpoint --grounding-evaluator groundedness_pro --source-revision $revision --baseline-results $badRag --candidate-results $fixedRag --output-dir "$evidence\grounding-pro"
$groundingProExit = $LASTEXITCODE
$groundingExit
$groundingProExit
Get-ChildItem "$evidence\grounding", "$evidence\grounding-pro"
```

Les deux juges natifs ont manqué la mauvaise référence dans les exécutions conservées :

| Juge                        | Mauvaise référence | Réponse corrigée | Contrôle négatif |
| --------------------------- | ------------------ | ---------------- | ---------------- |
| `builtin.groundedness` v18   | 5/5                | 5/5              | Échec            |
| `builtin.groundedness_pro` v8 | `true`            | `true`           | Échec            |

N'affirmez ni succès des comparaisons d'ancrage ni amélioration d'ancrage.
L'acceptation de la mauvaise réponse fait volontairement retourner un code
non nul. Distinguez ce contrôle échoué des erreurs d'authentification, de délai
ou de validation d'entrée dans les résultats natifs conservés. Gardez sorties
échouées et identifiants natifs; ne modifiez pas les contrôles pour obtenir
du vert et ne promouvez rien sur le seul score du juge. La correction du
corpus et des instructions ne modifie pas l'agent hébergé.

## Exercice 18.3 : Vérifier l'ingestion avant export et rejeu

Le graphe est déterministe. `AGENT_TASK_INSTRUCTIONS` est une métadonnée
d'évaluation, pas un prompt système exécuté. Les spans réels conservent étape,
identifiant synthétique validé, type d'exécution et hachage de politique,
sans données de demandeur, montants, appels LLM ou jetons inventés.

> [!IMPORTANT]
> Le rejeu exige des spans déjà réellement ingérés par le fournisseur de
> télémétrie autorisé dans Application Insights/Log Analytics existant.
> La livraison conservée a des spans racines vérifiés, mais les champs d'étapes
> et le rejeu déterministe restent non vérifiés. Ne déployez rien et ne modifiez
> pas les accès dans cet atelier.

L'export local isolé a reçu HTTP 403 pour l'identité opérateur et conservé
`trace_verified: false`. Ni `force_flush()` ni un W3C `traceparent` demandé
ne prouve l'ingestion. Si l'autorisation de publication ou le déploiement
instrumenté manque, consignez le blocage. Suivez la gestion d'accès approuvée;
ne retirez jamais les identifiants Entra pour contourner l'authentification.

Seulement après confirmation d'ingestion et accès de requête au workspace,
remplacez les paramètres par l'ID client du workspace existant et l'ID
d'opération réel de 32 caractères. Exportez d'abord et arrêtez sans spans réels :

```powershell
$workspace = '<existing-Log-Analytics-workspace-customer-ID>'
$traceId = '<actual-32-character-operation-ID>'
& .venv\Scripts\python.exe eval\native_showcase_evaluation.py trace-export --workspace-id $workspace --operation-id $traceId --output-dir "$evidence\trace"
if ($LASTEXITCODE -ne 0) { throw 'No verified trace export; do not create a replay.' }
Get-Content "$evidence\trace\trace.json"
& .venv\Scripts\python.exe eval\native_showcase_evaluation.py trace-dataset --trace-file "$evidence\trace\trace.json" --operation-id $traceId --source-revision $revision --output-dir "$evidence\replay"
if ($LASTEXITCODE -ne 0) { throw 'Trace reconstruction failed; do not evaluate a substitute.' }
Get-Content "$evidence\replay\replay-dataset.json"
```

Vérifiez opération, hachage de politique, révision source, hachage du fichier
de trace et correspondance au dossier synthétique. L'absence de spans échoue;
un ID demandé reste non vérifié avant confirmation native. Le rejeu reconstruit
une donnée de test, pas le prompt privé d'origine. Après cette inspection
seulement, soumettez le jeu conservé à staging v2 :

```powershell
& .venv\Scripts\python.exe eval\run_judge_evaluation.py --endpoint $endpoint --agent quote-preparation-agent --version 2 --deployment gpt-4o-mini --dataset "$evidence\replay\replay-dataset.json" --output-dir "$evidence\replayed-evaluation"
```

Notez identifiants d'évaluation réels et erreurs. Sans ingestion réelle,
ne créez pas une trace manuelle présentée comme preuve d'exécution.

## Exercice 18.4 : Vérifier séparément le playground réel

1. Ouvrez l'agent staging dans Foundry et sélectionnez sa version déployée.
   Connectez-vous normalement, sans injecter de jeton dans le navigateur.
2. Dans Playground, Chat, envoyez `CASE-SYN-001`. Attendez la réponse terminée,
   pas seulement une trace terminée.
3. Exigez les deux champs non vides `en-CA` et `fr-CA`, la révision employé et
   l'avis de formation, sans prix ni champs réservés au reviewer.
4. Dans Traces, distinguez exécution racine réussie, réponse utile et ingestion
   des étapes personnalisées. Une réponse vide est un échec de l'interface.
5. Dans Evaluations, examinez les critères individuels et le nombre global de
   cas réussis. Le juge consultatif n'est pas le contrôle déterministe.

Les [captures réelles](../showcase-evidence.md#agent-staging-foundry-authentifié)
documentent l'ancien message vide v3 et la réponse corrigée v4.
La [capture d'évaluation](../showcase-evidence.md#résultats-dévaluation-sans-embellissement)
conserve les critères échoués sans assimiler succès du workflow et succès du juge.
Ces observations ne remplacent pas vos propres vérifications réelles.

## Exercice 18.5 : Évaluer les messages observables au demandeur

Utilisez les cinq cas indépendants du nouveau jeu, pas les dix anciens cas de
workflow. Examinez les faits fiables avant la capture. Vérifiez la version
actuellement déployée dans Foundry : l'URL appelle le déploiement courant et
`--version` ne fixe pas le routage.

```powershell
$agentVersion = '<currently-deployed-staging-version>'
foreach ($locale in 'en-CA', 'fr-CA') {
    & .venv\Scripts\python.exe eval\convert_judge_dataset.py eval\applicant-message-dataset.jsonl "$evidence\applicant-$locale.json" --locale $locale
    if ($LASTEXITCODE -ne 0) { throw "Dataset conversion failed: $locale" }
    & .venv\Scripts\python.exe eval\run_judge_evaluation.py --endpoint $endpoint --agent quote-preparation-agent --version $agentVersion --deployment gpt-4o-mini --dataset "$evidence\applicant-$locale.json" --output-dir "$evidence\applicant-$locale"
    if ($LASTEXITCODE -ne 0) { throw "Inspect native judge results: $locale" }
}
```

Exigez cinq éléments terminés et trois critères notés par élément dans chaque
`results.json`. Vérifiez langue et contexte indépendant dans `captured.json`.
Les exécutions v4 conservées ont réussi 5/5 sur chaque critère dans chaque
langue. Un contrôle distinct de deux réponses a rejeté approbation et prix
inventés, ainsi qu'une soumission fictive pour une référence invalide, sur les
trois critères. Les identités natives figurent dans le
[guide](../native-showcase.md#contrat-du-juge-des-messages-au-demandeur).

C'est un nouveau contrat d'évaluation sur un jeu distinct, pas un gain mesuré
par rapport à l'ancien résultat. Le barème est une métadonnée, pas un prompt
exécuté. Il ne prouve ni calcul, ni persistance Cosmos, ni autorisation du
reviewer, ni correction des faux positifs d'ancrage RAG. Conservez ces contrôles
séparément et préservez les échecs historiques.

## Preuves de réalisation

* Conservez deux exécutions natives, leur comparaison et le rejet de
  l'auto-comparaison, avec scores mesurés et identités exactes.
* Conservez les deux résultats d'ancrage, faux positifs et contrôles échoués
  compris, ou consignez l'absence bloquante des artefacts historiques.
* Conservez export vérifié, provenance du rejeu et évaluation native seulement
  si l'ingestion est disponible; sinon, documentez le prérequis bloquant.
* Conservez les deux résultats des messages avec hachages, langue, provenance
  de capture et identités natives; distinguez-les de l'ancien jeu.

Retournez à l'[Atelier 17](lab-17-native-skills-memory.md), à l'[index](index.md)
ou au [guide natif](../native-showcase.md). Laissez staging et production
déployés; ces exercices n'autorisent ni démantèlement ni livraison.
