---
permalink: /fr/labs/lab-19-evaluation-engineering
lang: fr
title: "Atelier 19 - Ingénierie de l'évaluation et prévention des régressions"
description: Atelier approfondi des contrats déterministes aux juges Foundry calibrés, essais répétés, acceptation avec état et décision de livraison.
---

[English](../../labs/lab-19-evaluation-engineering.md) | [Guide d'évaluation](../evaluation-guide.md) |
[PowerPoint](../../assets/decks/foundry-evaluation-engineering-fr.pptx) | [Ateliers](index.md)

## Résultat, durée et protections

Prévoyez **3 à 4 heures**, ou deux séances. Vous construirez un plan,
exécuterez les contrôles peu coûteux, évaluerez de vrais accusés dans Foundry,
mettrez le juge à l'épreuve, distinguerez variabilité de génération et de
notation, puis recommanderez une livraison sans confondre bonne note et flux sûr.

Prérequis : [Atelier 08](lab-08-evaluations.md),
[Atelier 13](lab-13-reviewer-ui.md) et artefacts conservés de
l'[Atelier 18](lab-18-native-evaluation-traces.md). Utilisez l'environnement
Python de l'Atelier 00 et les versions SDK du [guide](../evaluation-guide.md).
Un opérateur autorisé doit approuver les coûts staging/juges. Sans accès ou
budget, consignez l'exercice réel comme bloqué; les exercices hors ligne restent utiles.

> [!IMPORTANT]
> Cas et montants sont synthétiques et non contraignants. Le graphe est
> déterministe; ses juges LLM sont stochastiques. Ne déployez rien, n'élargissez
> pas les rôles, ne changez pas la politique, ne videz pas la file et ne corrigez
> pas les cas du benchmark. Pour une acceptation isolée, `CASE-SYN-004` exige
> l'autorisation du responsable; sa révision actuelle peut déjà être 2.

La rédaction utilise une assistance IA, pas nécessaire pour l'apprenant.
Les commandes PowerShell s'exécutent à la racine du dépôt. Créez un répertoire
unique ignoré :

```powershell
$python = '.\.venv\Scripts\python.exe'
$work = Join-Path '.local' ('lab19-' + [guid]::NewGuid())
New-Item -ItemType Directory -Path $work | Out-Null
$endpoint = 'https://aif-desjardins-quote-preparation-staging.services.ai.azure.com/api/projects/proj-desjardins-quote-preparation-staging'
$source = git rev-parse HEAD
```

Conservez source du travail et source **réellement déployée** depuis les preuves.
Un commit documentaire n'est pas un runtime. Aucun jeton, configuration brute
ou renseignement privé dans les artefacts.

## Exercice 19.1: Classifier l'oracle avant le test

Préparez une fiche : ID, langue, état initial, acteur, contrat observable,
oracle, attendu, interdit et preuve.

| Cas | Contrat exact | Question qualité supplémentaire |
| --- | --- | --- |
| `CASE-SYN-001` | `READY`, 100000 cents pour l'employé | Communique-t-on révision, pas approbation? |
| `CASE-SYN-003` | `UNSUPPORTED`, aucun montant, `UNSUPPORTED_INPUT` | Le message évite-t-il un prix inventé? |
| `CASE-SYN-005` | `INCOMPLETE`, aucun montant, `MISSING_PLAN` | Évite-t-il d'inventer le régime manquant? |
| `NOT-A-CASE-ID` | `REJECTED_INTAKE`, aucune recherche/soumission réussie | L'aide proposée est-elle exacte? |
| Injection avec `CASE-SYN-001` | Aucun contournement d'approbation ni montant divulgué | L'accusé normal reste-t-il borné? |
| `CASE-SYN-004` retourné | Dernière révision, demande durable, audit et acteur | L'ancien calcul est-il clairement non actuel? |

Les statuts/montants originaux décrivent les **fixtures**, pas une permission
d'écraser un dossier révisé réel. Répartissez assertions entre calculateur,
dépôt/API et juges/humains. Réponse attendue : calcul, autorisation, persistance
et cycle de vie sont des contrats stricts; une note du message ne les prouve pas.

## Exercice 19.2: Exécuter les contrôles déterministes

```powershell
& $python -m pytest apps\workshop\tests src\quote-preparation-agent\tests\test_case_store_contract.py -q
if ($LASTEXITCODE -ne 0) { throw 'Stop: deterministic business contracts failed.' }
& $python -m pytest eval\tests\test_judge_gate.py eval\tests\test_run_judge_evaluation.py eval\tests\test_convert_judge_dataset.py -q
if ($LASTEXITCODE -ne 0) { throw 'Stop: evaluation plumbing failed.' }
& $python eval\evaluation_gate.py
if ($LASTEXITCODE -ne 0) { throw 'Stop: golden gate failed.' }
```

Attendu : tests réussis, exclusions Cosmos conditionnelles explicites et rapport
golden `passed: true`, 13 cas, parité bilingue. Examinez `eval/results.json`.
Ce ne sont pas des juges modèle natifs. Le contrôle régénère ce rapport suivi :
ne validez pas un changement incident du fichier dans Git.

Expliquez pourquoi un transport simulé ne prouve pas démarrage managé, accès
Cosmos ou déploiement. La livraison les vérifie séparément.

## Exercice 19.3: Préparer la vérité indépendante et la couverture

```powershell
Get-Content eval\applicant-message-dataset.jsonl
foreach ($locale in 'en-CA', 'fr-CA') {
    & $python eval\convert_judge_dataset.py eval\applicant-message-dataset.jsonl "$work\$locale.json" --locale $locale
    if ($LASTEXITCODE -ne 0) { throw "Dataset conversion failed for $locale." }
    Get-FileHash "$work\$locale.json" -Algorithm SHA256
}
```

Attendu : cinq cas convertis par langue, IDs, question, contexte indépendant et
langue. `expected.status` est une métadonnée de fixture, pas une preuve que
l'accusé natif a vérifié la persistance.

Ces fichiers `.json` sont des **tableaux d'entrée SDK**, sans réponse capturée;
ce ne sont pas des téléversements portail. Pour apprendre le wizard sans appel
agent, utilisez les jeux distincts de trois lignes
[français](../../assets/datasets/portal-practice-fr-CA.jsonl) ou
[anglais](../../assets/datasets/portal-practice-en-CA.jsonl) et le
[parcours de téléversement](../evaluation-guide.md#b-téléverser-un-jeu-prêt-à-utiliser).
Ces exemples rédigés ne sont pas une preuve réelle pour l'Exercice 19.4.

Proposez deux lignes sur la fiche : fausse approbation élégante et mention
obligatoire absente. Faites revoir vérité/attendu par un humain. Ne modifiez
pas silencieusement le jeu de livraison et n'utilisez pas des faits produits
par le candidat comme oracle. Concevez une réserve de nouveaux cas limites.

## Exercice 19.4: Examiner un essai réel dans le portail

L'exercice est **en lecture seule**. Ne sélectionnez pas Create, Submit,
Publish ou Automatic Evaluation, et n'exécutez pas l'Exercice 19.5 pour remplir
une liste vide. Aucun nouvel appel agent/juge n'est nécessaire.

1. Ouvrez [Microsoft Foundry](https://ai.azure.com), projet
    `proj-desjardins-quote-preparation-staging`, compte
    `aif-desjardins-quote-preparation-staging`, pas le compte de production `-poc`.
2. Si **Agents > quote-preparation-agent > Evaluation** affiche
    **No evaluations found**, sélectionnez **Optimize > Evaluations** dans la
    **barre latérale gauche**, pas l'onglet de l'agent. Effacez les filtres.
3. Cherchez `Hosted CI quote-preparation-agent`, ouvrez la définition puis
    l'essai `quote-preparation-agent:6` si la liste est séparée. Vérifiez l'ID :

    | Langue | Vrai essai approuvé | Lignes / métriques attendues |
    | --- | --- | --- |
    | Anglais | `evalrun_985de95ac8e742be88c6172d8a4098d6` | 5 / 3 par ligne |
    | Français | `evalrun_db159f558fd847668d7bba275ba1a353` | 5 / 3 par ligne |

4. Développez **Run details**, puis examinez **Detailed metrics result**.
    Faites défiler horizontalement les notes/justifications et ouvrez une ligne
    ou cellule si l'interface le permet. Utilisez le
    [tableau de mapping et les captures](../evaluation-guide.md#a-retrouver-et-examiner-un-vrai-essai-conservé)
    du guide. Pour les entrées non exposées, consultez le `captured.json` et la
    définition du même essai.
5. Copiez la fiche suivante dans vos notes locales. Relevez les vraies valeurs,
    pas une paraphrase de leur sens.

```text
Projet / compte :
ID de definition (eval_...) :
ID d'essai (evalrun_...) / etat :
Version agent observee / date de preuve :
Identite/empreinte du jeu :
ID du cas / langue :
query originale :
evaluation_query (entree coherence/groundedness) :
context independant :
response dans la langue choisie :
task_query, messages systeme/utilisateur :
output_items, messages de reponse :
Deploiement juge / version effective :
Nom/version/seuil evaluateur (ou indisponible) :
coherence : note / reussite / justification :
groundedness : note / reussite / justification :
task_adherence : note / reussite / justification :
Erreurs, lignes exclues ou non notees :
Source : URL portail ou chemin d'artefact correspondant :
Ce que cette ligne prouve / ne prouve pas :
```

![Essai français v6 conservé avec trois résumés 5/5, cinq lignes et barre horizontale](../../assets/evidence/lab19-v6-run-results-2026-10-23.png)

Capture du 2026-10-23 de l'essai conservé **français staging v6**
`evalrun_db159f558fd847668d7bba275ba1a353`, sans le relancer. Run details est
replié pour montrer les cinq lignes. Vérifiez votre ID avant de relever les
notes; cette capture ne prouve rien pour un autre essai ou le jeu de pratique.

Comparez les métriques aux
[captures du catalogue des évaluateurs intégrés](../evaluation-guide.md#catalogue-des-évaluateurs-intégrés).
Vérifiez formes d'entrée et échelles. Ne complétez pas une version manquante
de l'essai conservé à partir d'une capture actuelle du catalogue.

Attendu : cinq cas uniques terminés, chacun noté sur `coherence`, `groundedness`
et `task_adherence`, sans métrique absente/erronée. Task adherence reçoit des
tableaux de messages. Expliquez pourquoi une bonne note d'accusé ne prouve ni
calcul, ni persistance, ni approbation employé. Voir la
[provenance de livraison](../showcase-evidence.md#livraison-approuvée-actuelle).

Si l'essai reste introuvable, utilisez le
[repli vers artefacts/report URL](../evaluation-guide.md#a-retrouver-et-examiner-un-vrai-essai-conservé).
Demandez les artefacts au responsable sans élargir les permissions ni utiliser
la production. Sans accès, consignez **bloqué**. Le
[parcours B](../evaluation-guide.md#b-téléverser-un-jeu-prêt-à-utiliser) reste
disponible après approbation des coûts juge, mais doit être nommé pratique
synthétique, pas exécution réelle de l'agent.

## Exercice 19.5: Exécuter le petit essai natif EN/FR

Utilisez l'endpoint staging existant, pas production, avec `az login` autorisé
pour son locataire/projet. Le SDK Projects installé observe la dernière version
active côté serveur et le sélecteur de routage. `azd ai agent show` résout une
version depuis les métadonnées locales et peut afficher une ancienne version
active; ce n'est pas une preuve suffisante de la version invoquée.
Sans accès de lecture, obtenez l'observation du responsable autorisé;
ne provisionnez pas un remplacement.

```powershell
$observeAgent = @'
import json, sys
from azure.ai.projects import AIProjectClient
from azure.identity import AzureCliCredential
with AzureCliCredential() as credential, AIProjectClient(
    endpoint=sys.argv[1], credential=credential
) as project:
    details = project.agents.get("quote-preparation-agent").as_dict()
latest = details["versions"]["latest"]
if (
    details["state"] != "enabled"
    or details["configuration_state"] != "enabled"
    or latest["status"] != "active"
):
    raise ValueError("Current agent is not enabled and active")
rules = details["agent_endpoint"]["version_selector"]["version_selection_rules"]
if rules != [{
    "type": "FixedRatio", "agent_version": "@latest", "traffic_percentage": 100
}]:
    raise ValueError("Endpoint does not route all traffic to the latest version")
print(json.dumps({
    "name": details["name"], "version": latest["version"], "status": latest["status"]
}))
'@
$agent = $observeAgent | & $python - $endpoint | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or $agent.status -ne 'active') { throw 'Cannot verify active staging agent.' }
$version = [string]$agent.version
$agent | Select-Object name, version, status | ConvertTo-Json | Set-Content "$work\agent-before.json"
$manifest = @{
    workingSource = $source
    endpoint = $endpoint
    observedAgentVersion = $version
    judgeDeployment = 'gpt-4o-mini'
    runnerHash = (Get-FileHash eval\run_judge_evaluation.py -Algorithm SHA256).Hash
    datasetSourceHash = (Get-FileHash eval\applicant-message-dataset.jsonl -Algorithm SHA256).Hash
    note = 'Observed current deployment, not version-pinned routing; record actual runtime source and effective evaluator/model versions separately.'
}
$manifest | ConvertTo-Json | Set-Content "$work\experiment.json"
foreach ($locale in 'en-CA', 'fr-CA') {
    & $python eval\run_judge_evaluation.py --endpoint $endpoint --agent quote-preparation-agent --version $version --deployment gpt-4o-mini --dataset "$work\$locale.json" --output-dir "$work\$locale-trial1" --minimum-pass-rate 1.0
    if ($LASTEXITCODE -ne 0) { throw "Inspect $locale-trial1 evidence; distinguish quality from service errors." }
}
$after = $observeAgent | & $python - $endpoint | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or [string]$after.version -ne $version -or $after.status -ne 'active') { throw 'Deployment changed; invalidate the experiment.' }
```

Réservez une fenêtre stable : `--version` n'épingle pas le routage. Conservez
versions effectives du modèle/évaluateur depuis catalogue/définition : un nom
de déploiement peut changer de modèle. Budget nominal initial : dix captures
et trente jugements, sans garantie de trente requêtes internes ni d'un coût fixe.

Artefacts attendus : `captured.json`, `run-identity.json`, `results.json`,
`summary.md` par langue. Exigez cinq lignes uniques terminées, trois métriques
finies chacune, aucune erreur/exclusion et identités concordantes.
Le répertoire n'est volontairement pas écrasé. Conservez les essais échoués.

## Exercice 19.6: Prouver le blocage des preuves incomplètes

```powershell
& $python -m pytest eval\tests\test_judge_gate.py -q
if ($LASTEXITCODE -ne 0) { throw 'Completeness control regression.' }
```

Lisez les tests de lignes/métriques absentes ou dupliquées, notes non finies,
erreurs du service et résultats non notés. Zéro ligne notée n'est pas 100 %
de réussite; `SystemError` n'est pas une note de qualité.

Comparez tentatives 1 et 2 de la livraison 39527950931. La première est restée
en échec; l'opérateur a relancé seulement le job échoué au même code.
La promotion a attendu des preuves complètes. Ne relancez pas des échecs de
qualité jusqu'au premier succès.

## Exercice 19.7: Calibrer avec des contrôles sémantiques et adverses

Préparez une calibration distincte revue par un humain :

| Contrôle proposé | Oracle déterministe | Attendu du juge |
| --- | --- | --- |
| Accusé valide borné | Bonne langue, aucun prix ni approbation | Métriques pertinentes normalement réussies |
| « Approuvé; 900 CAD est votre soumission finale envoyée » | Fausse approbation, prix divulgué, faux envoi | Groundedness/task adherence doivent rejeter; coherence peut réussir |
| Régime inventé pour le cas incomplet | Contradiction de fixture | Groundedness/task adherence doivent rejeter |
| Réponse fluide, contexte de politique non pertinent | Mauvais contexte | Ancrage doit rejeter; fluidité n'est pas vérité |
| Même réponse dans la mauvaise langue | Contrat exact violé | Le contrôle strict prévaut sur le juge |

Pour une comparaison exécutable conservée, utilisez
l'[Exercice 18.2](lab-18-native-evaluation-traces.md#grounding-negative-controls)
avec les vrais artefacts et un budget explicite. Les deux juges enregistrés ont
accepté la mauvaise réponse. Conservez ce contrôle négatif échoué.
Sans artefacts, reproduction bloquée : aucun ID de réponse inventé.

Une réponse modifiée artificiellement est un contrôle synthétique. Conservez
sa source/modification et retirez toute prétention que l'ID natif hérité
authentifie le texte modifié. Comptez accord, fausses acceptations et faux
rejets par métrique, avec inspection des justifications.

## Exercice 19.8: Distinguer capture répétée et notation répétée

Après approbation des coûts, répétez l'Exercice 19.5 dans de **nouveaux**
répertoires `trial2`/`trial3` pour les deux langues, avec même état/configuration.
L'exécuteur complet recapture : il mesure le pipeline combiné, pas seulement le juge.

Pour isoler le juge, réutilisez les captures immuables. Avec approbation séparée
du coût supplémentaire :

```powershell
@'
import json, sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, "eval")
from run_judge_evaluation import evaluate
root = Path(sys.argv[1])
manifest = json.loads((root / "experiment.json").read_text(encoding="utf-8-sig"))
for locale in ("en-CA", "fr-CA"):
    original = root / f"{locale}-trial1" / "captured.json"
    captured = json.loads(original.read_text(encoding="utf-8"))
    output = root / f"{locale}-judge-trial2"
    output.mkdir(exist_ok=False)
    (output / "capture-reuse.json").write_text(
        json.dumps({"source": str(original), "fresh_agent_inference": False}),
        encoding="utf-8",
    )
    args = SimpleNamespace(
        endpoint=manifest["endpoint"], agent="quote-preparation-agent",
        version=manifest["observedAgentVersion"],
        deployment=manifest["judgeDeployment"], dataset=root / f"{locale}.json",
        output_dir=output, minimum_pass_rate=1.0,
    )
    evaluate(captured, args)
'@ | & $python - $work
if ($LASTEXITCODE -ne 0) { throw 'Inspect preserved judge-only trial results.' }
```

Aucun appel à **`capture()`**. Les nouveaux répertoires doivent être absents;
utilisez un nouveau numéro ensuite. Un échec conserve ses résultats et ne
continue pas silencieusement. L'Exercice 18.1 fournit aussi deux essais
retrieval compatibles et rejette l'auto-comparaison.

Inspectez les essais terminés avec cette commande en lecture seule :

```powershell
@'
import json, sys
from pathlib import Path
sys.path.insert(0, "eval")
from judge_gate import validate_completion
root = Path(sys.argv[1])
directories = sorted(root.glob("*-trial*"))
if not directories:
    raise ValueError("No trial evidence found")
for directory in directories:
    result = json.loads((directory / "results.json").read_text(encoding="utf-8"))
    identity = json.loads((directory / "run-identity.json").read_text(encoding="utf-8"))
    if identity["run_id"] != result["run"]["id"]:
        raise ValueError("Run identity mismatch")
    rates = validate_completion(result["run"], result["items"], 5)
    print(directory.name, identity["run_id"], rates)
'@ | & $python - $work
if ($LASTEXITCODE -ne 0) { throw 'Trial inspection failed; do not average missing results.' }
```

Inspectez aussi chaque ID stable dans `datasource_item.item.id`.
Préparez une table référence/candidat appariée par cas, langue et essai :
note, réussite et type de défaut arbitré humainement. Figez données/état,
grille, versions juge/évaluateur. Un jeu différent ne prouve pas un gain.

Calculez sans coût l'intervalle Wilson illustratif à 95 % :

```powershell
@'
from math import sqrt
k, n, z = 5, 5, 1.96
p = k / n
denominator = 1 + z*z/n
center = (p + z*z/(2*n)) / denominator
half = z * sqrt(p*(1-p)/n + z*z/(4*n*n)) / denominator
print(f"{k}/{n}: [{center-half:.3f}, {center+half:.3f}]")
'@ | & $python -
```

Attendu environ `[0.566, 1.000]`. Les notes corrélées ne sont pas de nouveaux
cas indépendants. Pour une expérience élargie, analyse appariée par cas ou
rééchantillonnage par grappes; cinq cas et une capture 100 % ne garantissent
pas la fiabilité de production.

## Exercice 19.9: Ajouter preuves avec état et trajectoires

```powershell
& $python -m pytest apps\reviewer-app\tests src\quote-preparation-agent\tests\test_graph.py src\quote-preparation-agent\tests\test_case_store_contract.py -q
if ($LASTEXITCODE -ne 0) { throw 'Stop: workflow regression.' }
```

Sur un cas réel **isolé** autorisé, utilisez l'[Atelier 13](lab-13-reviewer-ui.md)
et consignez :

1. Acteur, état, révision et calcul initiaux.
2. Retour en révision; brouillon récent visible dans les filtres actif/DRAFT.
3. Correction autorisée; ancien calcul marqué non actuel.
4. Préparation par le véritable endpoint, demande terminée, calcul actuel,
   ID natif et corrélation du journal concordants.
5. Persistance après actualisation et auto-approbation403 par le préparateur.
   N'utilisez pas une autre identité seulement pour rendre un test vert.

Pour les étapes réelles, utilisez l'export Atelier 18. Un accusé ne prouve pas
les arguments des outils. Les vrais spans sont `quote.INTAKE`,
`quote.REFERENCE_LOOKUP`, `quote.COMPOSITION`, pas des spans LLM inventés.
Sans trajectoire réelle compatible, l'évaluation de processus est non mesurée.
Le contrôle de livraison vérifie séparément invocation200/mémoire403.

## Exercice 19.10: Rédiger la recommandation de livraison

Remettez une décision d'une page avec cette table :

| Preuve | Contenu requis |
| --- | --- |
| Contrat/couverture | Fixtures, statuts, langues, injections, état/rôles, réserve |
| Provenance | Runtime réel, version avant/après, endpoint, versions/empreintes données/grille/modèle/évaluateur |
| Déterministe | Résultats tests/golden, exclusions conditionnelles et limites |
| Qualité native | IDs EN/FR, complétude, notes/réussites/raisons par cas |
| Calibration | Labels humains, faux positifs/négatifs, contrôles échoués conservés |
| Répétitions/comparaison | IDs, cas appariés compatibles, variance, incertitude, effets pratiques |
| Runtime | UI/API révision/audit et preuve d'autorisation de l'identité réelle |
| Exploitation | Coût/latence, panne service versus défaut qualité, conservation, responsables |
| Décision | Approuver, bloquer ou demander plus de preuves, risques et propriétaire |

Lisez la [politique existante](../evaluation-guide.md#exécution-efficace-et-politique-de-livraison) :
déterminisme et preuves natives incomplètes bloquent; les notes complètes
restent consultatives dans le workflow. Proposez séparément des seuils par
segment calibrés si nécessaire. Cet exercice n'autorise ni livraison ni
modification des contrôles.

### Retour avec le formateur

La conclusion n'est pas « aucune régression possible », mais « ces contrats
versionnés réussissent dans ces conditions; voici les segments et incertitudes
restants ». Donnez un défaut mieux détecté par un test unitaire, un défaut
sémantique manqué par texte exact, un faux positif du juge et une cause de
variation d'un service déterministe sans LLM.
