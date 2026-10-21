import path from 'node:path';
import { fileURLToPath } from 'node:url';
import PptxGenJS from 'pptxgenjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const OUT = path.join(ROOT, 'docs', 'assets', 'decks');
const C = { navy: '001B3D', blue: '0078D4', ink: '183449', muted: '526777', paper: 'FAFBFC', border: 'DCE5ED', pale: 'EDF4FA' };
const BASE = 'https://devopsabcs-engineering.github.io/foundry-hosted-agents-fsi';
const SOURCES = [
  'https://learn.microsoft.com/azure/foundry/how-to/evaluate-generative-ai-app',
  'https://learn.microsoft.com/azure/foundry/observability/how-to/cloud-evaluation',
  'https://learn.microsoft.com/azure/foundry/observability/how-to/cloud-evaluation-datasets',
  'https://learn.microsoft.com/azure/foundry/concepts/built-in-evaluators',
  'https://learn.microsoft.com/azure/foundry/concepts/evaluation-evaluators/agent-evaluators',
  'https://learn.microsoft.com/azure/foundry/concepts/evaluation-evaluators/custom-evaluators',
];

// Each language includes teaching notes, not only translated slide titles.
const SLIDES = [
  {
    kind: 'cover',
    en: ['Evaluation engineering', ['From exact contracts to calibrated Foundry judges', 'Quote preparation agent | Deep lab + operating playbook'], 'Allow 3 to 4 hours including Lab 19. All data and amounts are synthetic, non-binding training material. AI-assisted authoring was used; learners need no coding assistant. The retained quote graph is deterministic. We evaluate its business contracts directly and use model judges only for suitable observable quality.'],
    fr: ["Ingénierie de l'évaluation", ['Des contrats exacts aux juges Foundry calibrés', 'Agent de soumission | Atelier approfondi et guide pratique'], "Prévoir 3 à 4 heures avec l'Atelier 19. Données et montants synthétiques, non contraignants. Rédaction assistée par IA, sans assistant de code requis pour les apprenants. Le graphe conservé est déterministe : contrats métier directs, juges modèles pour la qualité observable adaptée."],
  },
  {
    en: ['What you will be able to defend', ['Choose an oracle before choosing an evaluator.', 'Create a small native experiment with independent truth.', 'Challenge the judge, repeat fairly and quantify uncertainty.', 'Recommend release from evidence, not a green screenshot.'], 'Ask participants what a 100% score proves. Expected answer: only the stated measured criteria on this versioned sample. Pair the guide with Lab 19 exercises 19.1 through 19.10. Live exercises require approved access and budget.'],
    fr: ['Ce que vous pourrez justifier', ["Choisir l'oracle avant l'évaluateur.", 'Créer une petite expérience native avec vérité indépendante.', 'Mettre le juge à l’épreuve, répéter et quantifier l’incertitude.', 'Recommander une livraison par les preuves, pas une capture verte.'], "Demander ce que prouve 100 %. Réponse : les critères mesurés sur cet échantillon versionné seulement. Utiliser le guide et les exercices 19.1 à 19.10. Accès et budget approuvés requis pour le réel."],
  },
  {
    kind: 'flow',
    en: ['What the quote agent actually does', ['INTAKE: validate case ID', 'REFERENCE_LOOKUP: read-only MCP', 'COMPOSITION: calculate + persist', 'Employee decision: separate reviewer'], 'The hosted LangGraph workflow does not use an LLM to price. It returns bounded EN/FR templates. The LLM in this evaluation path is the judge. Skills, memory and File Search demonstrations are isolated; do not infer they are called by the quote graph. Calculation and persistence are inside COMPOSITION.'],
    fr: ['Ce que fait réellement l’agent', ['INTAKE : valider le dossier', 'REFERENCE_LOOKUP : MCP lecture seule', 'COMPOSITION : calculer et persister', 'Décision employé : réviseur séparé'], "Le graphe LangGraph ne tarifie pas avec un LLM. Les messages EN/FR sont bornés. Ici, le LLM est le juge. Compétences, mémoire et File Search sont isolés. Calcul et persistance restent dans COMPOSITION."],
  },
  {
    kind: 'compare',
    en: ['Deterministic versus stochastic', ['Exact contract|Same controlled input + state|Schema, amount, transition, role|A violated invariant blocks', 'Sampled judgment|Generation or judge may vary|Meaning, grounding, usefulness|Calibration + uncertainty matter'], 'Unit test describes scope, not determinism. An agent evaluation can contain deterministic code graders. Temperature zero or a seed does not guarantee identical outputs across changing model/service versions. Network, RBAC and persistent state can also vary in a deterministic application.'],
    fr: ['Déterministe versus stochastique', ['Contrat exact|Même entrée et état contrôlés|Schéma, montant, transition, rôle|Un invariant violé bloque', 'Jugement échantillonné|Génération ou juge variable|Sens, ancrage, utilité|Calibration et incertitude'], "Test unitaire décrit une portée, pas le déterminisme. Une évaluation d'agent peut utiliser du code déterministe. Température zéro et graine ne garantissent pas une identité après changement du service. Réseau, RBAC et état peuvent aussi varier."],
  },
  {
    en: ['Keep hard invariants out of opinion polls', ['No invented amount when status is INCOMPLETE or UNSUPPORTED.', 'No self-approval: preparer and deciding employee must differ.', 'Applicant response must not disclose the employee premium.', 'Revision, ETag, idempotency and audit must agree.'], 'A model score is not an arithmetic or authorization oracle. Test exact fields and transitions using calculator, CaseStore and API tests. Schema validity alone does not prove correctness. These contracts remain hard even when future agent components become generative.'],
    fr: ['Un invariant strict n’est pas un sondage', ['Aucun montant inventé pour INCOMPLETE ou UNSUPPORTED.', 'Aucune auto-approbation : préparateur et décideur distincts.', 'Le message demandeur ne divulgue pas la prime employé.', 'Révision, ETag, idempotence et journal doivent concorder.'], "Une note modèle n'est pas un oracle de calcul ou d'autorisation. Vérifier champs et transitions par calculateur, CaseStore et API. Un schéma valide ne prouve pas la justesse. Ces invariants restent stricts même avec des composants génératifs futurs."],
  },
  {
    kind: 'flow',
    en: ['The evidence ladder', ['Local contracts + golden gate', 'Live response + native judges', 'Calibration + repeated holdout', 'Stateful acceptance + operations'], 'Start cheap and deterministic, then add cost where the oracle needs it. The ladder is complementary evidence, not a replacement sequence that makes earlier checks obsolete. Have participants assign each worksheet assertion to one layer.'],
    fr: ['La progression des preuves', ['Contrats locaux et golden gate', 'Réponse réelle et juges natifs', 'Calibration et réserve répétée', 'Acceptation avec état et suivi'], "Commencer peu coûteux et déterministe. Ajouter le coût seulement quand l'oracle le nécessite. Les couches se complètent; elles ne remplacent pas les précédentes. Affecter chaque assertion de la fiche à une couche."],
  },
  {
    en: ['A five-case starting dataset, not full coverage', ['CASE-SYN-001: READY; original employee amount 100000 cents.', 'CASE-SYN-003 / 005: unsupported / missing plan, no amount.', 'Invalid ID: reject before lookup or submission.', 'Injection with CASE-SYN-001: normal bounded acknowledgement.'], 'These are the applicant-message source cases. The injection is untrusted input, never permission to approve. Add locale, role and lifecycle slices. CASE004 is reserved for isolated revision acceptance; do not overwrite already revised cases with original fixture expectations.'],
    fr: ['Cinq cas initiaux, pas une couverture complète', ['CASE-SYN-001 : READY; montant employé original 100000 cents.', 'CASE-SYN-003 / 005 : non pris en charge / régime absent, sans montant.', 'ID invalide : rejet avant recherche ou soumission.', 'Injection avec CASE-SYN-001 : accusé normal borné.'], "Cas source des messages au demandeur. L'injection ne donne aucun droit d'approuver. Ajouter langues, rôles et états. Réserver CASE004 à l'acceptation isolée; ne pas écraser un dossier révisé avec les attentes de la fixture originale."],
  },
  {
    en: ['Independent truth is the foundation', ['Keep query, trusted context and candidate response distinct.', 'Expected status metadata does not prove hidden execution.', 'Human-review generated tests before accepting their oracle.', 'Never use the candidate’s answer as its own reference truth.'], 'Ask participants to identify circular grading. If a fabricated premium is copied from the candidate into context, a groundedness judge may reward the hallucination. The evaluator must receive independent fixture/rule/policy facts with versioned provenance.'],
    fr: ['La vérité indépendante est la fondation', ['Séparer question, contexte fiable et réponse candidate.', 'Le statut attendu ne prouve pas une exécution cachée.', 'Faire revoir humainement les tests générés et leur oracle.', 'Ne jamais prendre la réponse candidate comme sa propre vérité.'], "Faire repérer le jugement circulaire. Un prix inventé copié dans le contexte peut être récompensé par groundedness. Les faits de fixture, règles et politique doivent être indépendants, versionnés et traçables."],
  },
  {
    en: ['Separate development, calibration and holdout', ['Development: find defects and improve implementation.', 'Calibration: measure judge false accepts and false rejects.', 'Holdout: estimate performance on unseen reviewed cases.', 'Incidents: add new versioned cases without rewriting old results.'], 'A repeatedly inspected holdout is no longer unseen. Avoid learning thresholds against the release set. Keep scenario coverage, human labels and revisions explicit. A dataset change requires a new baseline; it is not a measured improvement against the old dataset.'],
    fr: ['Séparer développement, calibration et réserve', ['Développement : trouver et corriger les défauts.', 'Calibration : mesurer fausses acceptations et faux rejets.', 'Réserve : estimer la qualité sur des cas revus mais inédits.', 'Incidents : ajouter des cas versionnés sans réécrire le passé.'], "Une réserve inspectée continuellement n'est plus inédite. Éviter de régler les seuils sur le jeu de livraison. Garder couverture, étiquettes et versions. Un jeu modifié exige une nouvelle référence."],
  },
  {
    en: ['Lab checkpoint: cheap checks first', ['pytest: calculator, CaseStore and reviewer API contracts.', 'pytest: dataset conversion, capture errors and judge-gate tests.', 'python eval/evaluation_gate.py: 13 deterministic records.', 'Stop on invariant failures before paying for a judge.'], 'Use the exact PowerShell commands in Lab19.2; the deck is not a shell script. Conditional live Cosmos skips are explicit limitations. Mocked success is not deployed availability. The golden report is regenerated; do not commit incidental generated report changes.'],
    fr: ['Point pratique : les contrôles peu coûteux', ['pytest : calculateur, CaseStore et contrats API reviewer.', 'pytest : conversion, erreurs de capture et contrôle du juge.', 'python eval/evaluation_gate.py : 13 cas déterministes.', 'Arrêter sur un invariant avant de payer un juge.'], "Utiliser les commandes PowerShell exactes de l'Atelier 19.2. Les exclusions Cosmos sont des limites explicites. Un succès simulé ne prouve pas le déploiement. Ne pas valider les changements incidents du rapport généré."],
  },
  {
    kind: 'flow',
    en: ['Native cloud evaluation, end to end', ['Convert EN / FR source', 'Capture real Responses output', 'Create eval + run; poll boundedly', 'Retrieve every item + retain IDs'], 'The repository uses AIProjectClient.get_openai_client and native evals.create / evals.runs.create. Reject HTTP200 error bodies and missing selected-locale output before judging. Preserve raw captures and all failed attempts. Output directories are fresh, never overwritten.'],
    fr: ['Évaluation cloud native de bout en bout', ['Convertir source EN / FR', 'Capturer les vraies réponses', 'Créer définition/essai; délai borné', 'Récupérer chaque ligne et les IDs'], "Le dépôt utilise AIProjectClient.get_openai_client et evals.create / evals.runs.create. Rejeter les corps d'erreur HTTP200 et langues absentes avant le juge. Garder captures et échecs dans des répertoires nouveaux."],
  },
  {
    en: ['Portal walk-through: choose, map, inspect', ['Confirm staging project, tenant, running version and cost cap.', 'Choose agent invocation or an uploaded captured-response dataset.', 'Map query / context / response; select supported evaluators.', 'Check completion, errors, individual reasons and export lineage.'], 'Use the guide’s ten portal steps. The new agent UI has an Evaluation tab; project-level Evaluate is also documented. Labels and hosted/custom-agent support vary by portal generation and preview capability. Use the verified SDK if mapping or repetition cannot be expressed; do not invent a button.'],
    fr: ['Portail : choisir, mapper, inspecter', ['Confirmer staging, locataire, version active et plafond de coût.', 'Choisir appel agent ou jeu de réponses déjà capturées.', 'Mapper question / contexte / réponse et évaluateurs disponibles.', 'Vérifier complétude, erreurs, raisons et export de provenance.'], "Suivre les dix étapes du guide. L'agent actuel a un onglet Evaluation; Evaluate existe aussi au niveau projet. Libellés et compatibilité varient selon l'expérience/préversion. Utiliser le SDK vérifié si le portail ne peut exprimer le protocole."],
  },
  {
    en: ['Do not mix API generations', ['Projects SDK + native Evals is this repository’s cloud path.', 'azure-ai-evaluation has a separate local evaluate() API.', 'Built-ins, code graders and prompt rubrics have different schemas.', 'Preview, region and evaluator-version limits still apply.'], 'The working release uses projects2.6.0, openai3.6.0 and identity1.25.3. Do not claim the parallel evaluation SDK is deprecated without authoritative evidence. Check installed versions and current official docs before adapting samples. The workshop does not upgrade production dependencies.'],
    fr: ['Ne pas mélanger les générations d’API', ['Projects SDK et Evals natif : parcours cloud du dépôt.', 'azure-ai-evaluation expose un evaluate() local distinct.', 'Évaluateurs intégrés, code et grilles ont des schémas différents.', 'Préversion, région et version restent des limites.'], "La livraison utilise projects2.6.0, openai3.6.0, identity1.25.3. Ne pas déclarer l'autre SDK obsolète sans preuve officielle. Vérifier versions installées et documentation avant adaptation. Aucun changement de dépendance de production."],
  },
  {
    en: ['The built-in evaluator contract', ['type: azure_ai_evaluator; evaluator_name: builtin.groundedness.', 'Map trusted context and selected-locale response explicitly.', 'The pinned runner uses initialization_parameters.deployment_name.', 'Task adherence receives task messages and normalized output items.'], 'See the guide’s exact configuration excerpts. A literal type azure_ai_groundedness is invented and incorrect. Current public samples may use model or typed wrappers; do not splice those into the pinned working contract without verification. Larger datasets need a real supported file/dataset reference.'],
    fr: ['Le contrat de l’évaluateur intégré', ['type : azure_ai_evaluator; nom : builtin.groundedness.', 'Mapper contexte fiable et réponse dans la langue choisie.', 'Le code épinglé utilise initialization_parameters.deployment_name.', 'Task adherence reçoit messages et output_items normalisés.'], "Consulter les extraits exacts du guide. azure_ai_groundedness est un type inventé. Des exemples récents utilisent model ou des types enveloppes : ne pas les mélanger sans vérification. Un grand jeu exige une référence fichier compatible réelle."],
  },
  {
    en: ['Three metrics, three different questions', ['Coherence: is this acknowledgement logically understandable?', 'Groundedness: is it supported by independent provided facts?', 'Task adherence: does it follow the bounded applicant task?', 'None of these proves calculator, tool, persistence or RBAC behavior.'], 'A perfectly coherent false statement may pass coherence. Require no-premium and no-approval policies independently. Inspect the selected metric’s returned score, pass threshold and reason rather than assuming every built-in uses the same scale.'],
    fr: ['Trois métriques, trois questions', ['Coherence : l’accusé est-il logiquement compréhensible?', 'Groundedness : les faits indépendants le soutiennent-ils?', 'Task adherence : respecte-t-il la tâche demandeur bornée?', 'Aucune ne prouve calcul, outils, persistance ou RBAC.'], "Une affirmation fausse mais cohérente peut réussir coherence. Exiger séparément absence de prix et d'approbation. Inspecter note, seuil et justification propres à la métrique, sans supposer une échelle universelle."],
  },
  {
    en: ['Bilingual evaluation is not one averaged score', ['Convert one source into independent EN and FR runs.', 'Keep the selected locale’s text as a string, not a bilingual map.', 'Inspect locale-specific failures and disclaimer requirements.', 'A global average can hide a French-only regression.'], 'The capture normalizer flattens the bilingual content map for task-adherence inputs. Missing locale is an error, not a silent language fallback. Compare the same slice and independent truth in each language. Formatting differences alone are not semantic quality failures.'],
    fr: ['Le bilinguisme n’est pas une moyenne unique', ['Convertir une source en essais EN et FR distincts.', 'Texte sélectionné en chaîne, pas carte bilingue brute.', 'Examiner défauts et mentions obligatoires par langue.', 'Une moyenne globale peut masquer une régression française.'], "La capture aplatit la carte bilingue pour task adherence. Langue absente signifie erreur, pas remplacement silencieux. Comparer même segment et vérité indépendante dans chaque langue. Une différence de format n'est pas automatiquement sémantique."],
  },
  {
    en: ['Provenance: a version label is not a pin', ['--version records the observed current deployment only.', 'Reserve a stable window and verify version before and after.', 'Freeze source, dataset, rubric, evaluator and judge-model versions.', 'Keep raw captures, response IDs, native run IDs and hashes.'], 'The native endpoint invokes the current deployment. A deployment name can later point to a different judge-model version. The existing runner identity does not magically record every effective catalog version: export configuration and record missing identities as a limitation. A requested traceparent is not verified ingestion.'],
    fr: ['Provenance : une étiquette n’est pas un épinglage', ['--version consigne seulement le déploiement observé.', 'Réserver une fenêtre stable; vérifier version avant et après.', 'Figer source, jeu, grille, évaluateur et modèle juge.', 'Garder captures, IDs natifs/réponse et empreintes.'], "L'endpoint invoque le déploiement courant. Un nom de déploiement peut changer de modèle. Le fichier identité ne capture pas automatiquement toutes les versions effectives : exporter la configuration et déclarer les limites. traceparent demandé ne prouve pas l'ingestion."],
  },
  {
    kind: 'compare',
    en: ['Completeness and quality are separate gates', ['Completeness|Terminal completed state|Expected unique items and metrics|No service errors or skipped rows', 'Quality|Calibrated per-metric thresholds|Slice-specific false accepts/rejects|Human review and uncertainty'], 'validate_completion rejects missing, duplicate, errored, nonfinite and unscored results. validate_results additionally applies a pass-rate policy. Zero items is not vacuous success. A service error is not a numeric quality outcome and must not be dropped from reporting.'],
    fr: ['Complétude et qualité sont deux contrôles', ['Complétude|État terminal completed|Lignes et métriques uniques attendues|Aucune erreur ni exclusion', 'Qualité|Seuils par métrique calibrés|Faux positifs/négatifs par segment|Révision humaine et incertitude'], "validate_completion rejette absences, doublons, erreurs et notes invalides. validate_results ajoute la politique de taux. Zéro ligne n'est pas un succès. Une panne n'est pas une note numérique à supprimer du rapport."],
  },
  {
    en: ['Understand the existing release policy', ['Deterministic failures and incomplete native evidence block.', 'Complete native quality scores are currently workflow-advisory.', '--minimum-pass-rate 1.0 means 100% of items, not score 1/5.', 'Protected approval and real workload readiness still apply.'], 'The CLI can exit nonzero for quality while the workflow retains advisory scores. A separate always-run completeness gate requires both locales. continue-on-error is not permission to ignore missing evidence. A stricter calibrated quality policy is a separate reviewed change; this curriculum does not change production gates.'],
    fr: ['Comprendre la politique existante', ['Déterminisme et preuve native incomplète bloquent.', 'Les notes natives complètes restent consultatives dans le workflow.', '--minimum-pass-rate 1.0 signifie 100 % des cas, pas une note 1/5.', 'Approbation protégée et identité réelle restent obligatoires.'], "Le CLI peut échouer sur la qualité tout en conservant des notes consultatives. Un contrôle distinct exige la complétude EN/FR. continue-on-error n'autorise pas une preuve manquante. Durcir la politique serait un changement séparé approuvé."],
  },
  {
    en: ['Real case: service failure is not model failure', ['Release 39527950931 attempt 1: SystemError, no scored items.', 'The completeness gate blocked production.', 'Approved retry: only failed job, same source 2c3f13b.', 'Attempt 2: complete EN/FR 5/5, then protected promotion.'], 'Retain both attempts and native correlation IDs. This is an operational service retry, not repeated sampling until a quality failure becomes green. The final release ran stagingv6 and productionv7. The earlier historical 0/10 benchmark is a different contract, not a comparable baseline.'],
    fr: ['Cas réel : panne service, pas défaut modèle', ['Livraison 39527950931, essai 1 : SystemError, aucune ligne notée.', 'Le contrôle de complétude a bloqué la production.', 'Relance autorisée : seul job échoué, même code 2c3f13b.', 'Essai 2 : EN/FR complets 5/5, puis promotion protégée.'], "Conserver les deux essais et corrélations. Il s'agit d'une relance opérationnelle, pas d'échantillonner jusqu'au vert. Livraison finale stagingv6/productionv7. L'ancien 0/10 utilise un autre contrat et n'est pas une référence comparable."],
  },
  {
    en: ['Challenge the judge with a polished false answer', ['Control: “Approved; CAD 900 is your final quote and was sent.”', 'Hard violations: approval, premium disclosure and false delivery.', 'Groundedness/task adherence should reject the false claims.', 'Coherence may pass: fluent does not mean factual.'], 'Use human labels per metric, not an expectation that every metric must fail every bad answer. Synthetic mutations must be labeled, with native response ID provenance removed for the edited answer. Do not present a rewritten candidate as an authentic captured response.'],
    fr: ['Défier le juge avec une fausse réponse élégante', ['Contrôle : « Approuvé; votre soumission finale de 900 CAD est envoyée. »', 'Violations : approbation, prix divulgué et faux envoi.', 'Groundedness/task adherence devraient rejeter ces affirmations.', 'Coherence peut réussir : fluidité n’est pas vérité.'], "Étiqueter l'attendu par métrique. Une réponse modifiée est un contrôle synthétique; son ancien ID natif ne prouve plus ce texte. Ne pas présenter une réécriture comme capture authentique."],
  },
  {
    en: ['Known false positives must remain visible', ['Recorded native RAG controls included a factually bad answer.', 'Both groundedness and groundedness_pro accepted that answer.', 'The negative-control experiment therefore failed.', 'Keep explicit policy checks and expert review alongside judges.'], 'Lab18.2 requires actual retained artifacts. If unavailable, record reproduction blocked; do not fabricate a baseline. Changing the corpus or instructions does not turn the failed control into a pass. This is an isolated RAG demonstration, not hosted quote-agent RAG.'],
    fr: ['Les faux positifs connus restent visibles', ['Les contrôles RAG conservés incluaient une mauvaise réponse.', 'groundedness et groundedness_pro l’ont acceptée.', 'L’expérience de contrôle négatif a donc échoué.', 'Conserver prédicats explicites et expertise humaine.'], "L'Atelier 18.2 exige les vrais artefacts. Sinon la reproduction est bloquée, sans référence inventée. Corriger corpus/instructions ne transforme pas le contrôle historique en réussite. Il s'agit du RAG isolé, pas du graphe de soumission."],
  },
  {
    en: ['Measure calibration, not only mean score', ['Human-label valid, false, incomplete and wrong-locale controls.', 'Count judge false accepts and false rejects by metric/slice.', 'Inspect disagreements; blind candidate labels when feasible.', 'Retain rubric version, thresholds, model identity and failures.'], 'Ask: which error is costliest here? A false accept of unauthorized approval matters more than harmless wording. Thresholds should reflect risk and validation, not be tuned after seeing the candidate. Challenge prompt injection inside judged content without allowing it to redefine the rubric.'],
    fr: ['Mesurer la calibration, pas seulement la moyenne', ['Étiqueter cas valides, faux, incomplets et mauvaise langue.', 'Compter fausses acceptations et faux rejets par métrique/segment.', 'Inspecter les désaccords; masquer les labels du candidat si possible.', 'Conserver grille, seuils, modèle et échecs.'], "Quel défaut coûte le plus? Une fausse acceptation d'approbation importe plus qu'une formulation bénigne. Calibrer selon le risque, pas après avoir vu le candidat. L'injection dans une réponse ne doit pas redéfinir la grille."],
  },
  {
    kind: 'compare',
    en: ['Two different repeated-trial experiments', ['Generation variance|Same frozen cases and initial state|Capture fresh answers each trial|Then judge and retain every answer', 'Judge variance|Same immutable captured answers|Call evaluate(), not capture()|Record reused response provenance'], 'The full CLI recaptures the hosted agent, so rerunning it does not isolate the judge. Lab19.8 includes an executable judge-only reuse recipe and a result-inspection recipe. Use fresh directories and predeclared trial counts; no silent overwrites or stopping at first pass.'],
    fr: ['Deux expériences de répétition différentes', ['Variance de génération|Mêmes cas et état initial figés|Nouvelles captures à chaque essai|Juger et garder chaque réponse', 'Variance du juge|Mêmes captures immuables|Appeler evaluate(), pas capture()|Consigner la réutilisation'], "Le CLI complet recapture l'agent et n'isole donc pas le juge. L'Atelier 19.8 fournit le code de réutilisation et d'inspection. Répertoires nouveaux et nombre d'essais prédéfini; pas d'écrasement ni d'arrêt au premier succès."],
  },
  {
    en: ['5/5 does not establish perfection', ['Illustrative 95% Wilson interval for 5/5: about 0.57 to 1.00.', 'That interval assumes independent Bernoulli observations.', 'Repeated grades of one case are correlated, not new customers.', 'Report case-level uncertainty and rare-harm limitations.'], 'Work through the stdlib Wilson calculation in Lab19.8. Do not pool 30 correlated rubric grades as 30 independent cases. A case-level paired analysis or cluster bootstrap preserves within-case dependence. Hard invariants are not traded away against a confidence interval.'],
    fr: ['5/5 ne démontre pas la perfection', ['Wilson 95 % illustratif pour 5/5 : environ 0,57 à 1,00.', 'Cet intervalle suppose des observations Bernoulli indépendantes.', 'Notes répétées d’un cas : corrélées, pas de nouveaux clients.', 'Présenter incertitude par cas et limites des préjudices rares.'], "Calculer Wilson dans l'Atelier 19.8. Ne pas traiter trente notes corrélées comme trente cas indépendants. Analyse appariée ou bootstrap par grappes conserve cette dépendance. Un invariant strict ne se négocie pas contre un intervalle."],
  },
  {
    en: ['Compare candidates fairly', ['Pair by stable case ID, locale, trial and controlled initial state.', 'Freeze independent facts, rubric, evaluator and judge-model version.', 'Inspect pass-to-fail transitions, effect size and uncertainty.', 'Changed dataset or evaluator means rebaseline, not improvement.'], 'Blind/randomize candidate order where feasible to reduce judge bias. Report per-case reasons and reviewed failures rather than only average score delta. Repetition controls statistical noise but does not fix invalid ground truth or missing coverage.'],
    fr: ['Comparer équitablement les candidats', ['Apparier ID stable, langue, essai et état initial contrôlé.', 'Figer faits, grille, évaluateur et version du modèle juge.', 'Inspecter transitions réussite-échec, effet et incertitude.', 'Jeu/évaluateur modifié : nouvelle référence, pas amélioration.'], "Masquer/randomiser l'ordre si possible pour réduire le biais. Présenter raisons et défauts revus par cas, pas seulement delta moyen. Les répétitions ne réparent ni vérité invalide ni couverture absente."],
  },
  {
    en: ['Spend where it buys useful evidence', ['Run local contracts and the golden gate before paid judges.', 'Pilot: 5 cases × 2 locales × 1 trial × 3 metrics = 30 judgments.', 'More trials, long contexts and evaluator retries increase cost.', 'Reuse captures for judge experiments; bound concurrency and budget.'], 'Thirty judgments is nominal work, not a fixed request count or price. The quote graph currently does not call a pricing LLM; judges still incur model cost. Freeze cache keys across input, state, model, rubric and evaluator, and label reused captures as not fresh inference.'],
    fr: ['Dépenser pour des preuves utiles', ['Contrats locaux et golden gate avant les juges payants.', 'Pilote : 5 cas × 2 langues × 1 essai × 3 métriques = 30 jugements.', 'Répétitions, longs contextes et relances augmentent le coût.', 'Réutiliser les captures; borner concurrence et budget.'], "Trente jugements est une estimation nominale, pas un prix fixe. Le graphe ne tarifie pas par LLM, mais ses juges coûtent. Figer clés de cache et indiquer les captures réutilisées, sans nouvelle inférence."],
  },
  {
    kind: 'flow',
    en: ['Stateful regression: the revision workflow', ['Return pending case to DRAFT rev 2', 'Confirm active / DRAFT queue visibility', 'Correct + prepare through native agent', 'Match audit; reject self-approval'], 'Production CASE004 was verified: previous110000 labeled not current, TRAINING_BASIC preparation returned200/PENDING_REVIEW/READY/90000, response and correlation matched, self-approval403. Do not replay blindly on current revision2 or clear benchmark state. Use owner-approved isolated storage/case.'],
    fr: ['Régression avec état : le parcours de révision', ['Retourner en DRAFT révision 2', 'Vérifier visibilité actif / DRAFT', 'Corriger et préparer par l’agent natif', 'Journal concordant; auto-approbation refusée'], "CASE004 production a été vérifié : ancien110000 non actuel, correction TRAINING_BASIC puis200/PENDING_REVIEW/READY/90000, IDs concordants, auto-approbation403. Ne pas rejouer aveuglément sur révision2 ni vider les fixtures partagées."],
  },
  {
    en: ['Trajectory evaluation needs real trajectory evidence', ['Outcome quality and process correctness are different questions.', 'Tool selection/arguments require compatible actual tool traces.', 'Real quote stages: INTAKE, REFERENCE_LOOKUP, COMPOSITION.', 'Requested trace ID or final text alone does not prove ingestion.'], 'Lab18 exports genuinely ingested SDK spans and reconstructs a synthetic replay, not a private original prompt. Do not invent model spans in this deterministic graph. If a process evaluator requires a trajectory format not captured here, mark the dimension not measured rather than filling it with an acknowledgement.'],
    fr: ['La trajectoire exige une preuve réelle', ['Qualité finale et processus correct sont des questions différentes.', 'Choix/arguments outils exigent des traces réelles compatibles.', 'Vraies étapes : INTAKE, REFERENCE_LOOKUP, COMPOSITION.', 'ID demandé ou texte final ne prouvent pas l’ingestion.'], "L'Atelier 18 exporte des spans réellement ingérés et reconstruit un cas synthétique, pas un prompt privé original. Ne pas inventer de spans modèle. Sans format de trajectoire requis, cette dimension reste non mesurée."],
  },
  {
    en: ['Operate two scorecards, not one', ['Service: availability, latency, 401/403, quota, timeouts, cost.', 'Quality: grounding, adherence, locale slices and human overrides.', 'Safety: deterministic policy violations and role boundaries.', 'Review drift and turn verified incidents into new test cases.'], 'A service SystemError belongs in reliability reporting, not a numeric model quality score. Avoid broad access grants as troubleshooting shortcuts. Real production sampling requires approved privacy and retention rules; this workshop stays synthetic. Scheduled evaluations complement, not replace, release evidence.'],
    fr: ['Exploiter plusieurs tableaux distincts', ['Service : disponibilité, latence, 401/403, quota, délais, coût.', 'Qualité : ancrage, tâche, segments linguistiques, corrections humaines.', 'Sécurité : violations déterministes et frontières de rôles.', 'Revoir la dérive et transformer les incidents vérifiés en tests.'], "SystemError concerne la fiabilité, pas une note numérique de qualité modèle. Ne pas élargir l'accès pour diagnostiquer. Un échantillonnage réel exige confidentialité/conservation approuvées. L'atelier reste synthétique."],
  },
  {
    en: ['Your release recommendation', ['Name the exact source, dataset, state, model and evaluator identities.', 'Report hard checks, completeness, quality, controls and uncertainty.', 'List unmeasured dimensions, cost, faults and remaining risks.', 'Approve, block or request evidence with an accountable owner.'], 'Use the one-page worksheet in Lab19.10. Good score alone is insufficient; missing trajectory or failed negative controls must stay visible. The lab does not authorize release, change gates or grant access. Include separate operations and quality conclusions.'],
    fr: ['Votre recommandation de livraison', ['Nommer source, jeu, état, modèle et évaluateur exacts.', 'Présenter contrats, complétude, qualité, contrôles et incertitude.', 'Lister dimensions non mesurées, coût, pannes et risques.', 'Approuver, bloquer ou demander des preuves avec un responsable.'], "Utiliser la fiche 19.10. La note ne suffit pas; trajectoire absente et contrôles échoués restent visibles. L'atelier n'autorise ni livraison, ni changement de contrôle, ni accès. Séparer exploitation et qualité."],
  },
  {
    en: ['Discussion: which candidate can ship?', ['A: 100% judge scores, but self-approval succeeds.', 'B: all hard tests pass, native run has zero scored items.', 'C: complete calibrated results, one known high-risk false accept.', 'D: complete evidence, stable slices, reviewed risks and approval.'], 'Expected answers: A blocks on a hard authorization invariant. B blocks on completeness, not assumed quality. C needs remediation or explicit risk decision under policy; a mean cannot hide the high-risk false accept. D is eligible for the protected owner decision, not automatically approved by the evaluator.'],
    fr: ['Discussion : quel candidat livrer?', ['A : juges 100 %, mais auto-approbation possible.', 'B : contrats stricts réussis, mais zéro ligne native notée.', 'C : résultats complets, une fausse acceptation à haut risque.', 'D : preuves complètes, segments stables, risques revus et approbation.'], "Réponses : A bloque sur l'autorisation. B sur la complétude. C nécessite correction ou décision explicite selon politique; la moyenne ne cache pas ce risque. D est admissible à la décision protégée, pas approuvé automatiquement par le juge."],
  },
  {
    en: ['Debrief: what non-regression really means', ['State the measured contract and conditions, not “cannot regress.”', 'Keep exact tests and semantic judgments complementary.', 'Preserve failed controls and operational failure attempts.', 'Improve coverage, calibration and monitoring as the system evolves.'], 'Ask each participant to name a bug unit tests detect better, a semantic defect exact matching misses, a judge false positive and a non-LLM cause of runtime variation. Strong answers separate evidence scope, statistical uncertainty and policy ownership.'],
    fr: ['Bilan : le vrai sens de non-régression', ['Énoncer contrat et conditions mesurés, pas « aucune régression possible ».', 'Combiner tests exacts et jugements sémantiques.', 'Conserver contrôles et tentatives opérationnelles échoués.', 'Faire évoluer couverture, calibration et surveillance.'], "Chaque participant nomme un bug mieux détecté par test unitaire, un défaut sémantique manqué par texte exact, un faux positif du juge et une cause non LLM de variation. Séparer portée, incertitude et responsabilité."],
  },
  {
    en: ['Take the lab, guide and evidence with you', ['Lab 19: ten progressive hands-on exercises with runnable commands.', 'Guide: portal steps, SDK mappings, policies and troubleshooting.', 'Deck: editable EN/FR PowerPoint with instructor notes.', 'Sources: official Microsoft Learn links in these notes.'], `Guide and lab are maintained in the repository and linked from the workshop. Rebuild with npm run build-evaluation-deck. Official references:\n${SOURCES.join('\n')}\nLive release evidence: https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/wiki/Native-Foundry-Evidence`],
    fr: ['Emporter atelier, guide et preuves', ['Atelier 19 : dix exercices progressifs avec commandes exécutables.', 'Guide : portail, mappings SDK, politique et diagnostic.', 'Présentation : PowerPoint EN/FR modifiables et notes formateur.', 'Sources : liens Microsoft Learn officiels dans les notes.'], `Le guide et l'atelier sont maintenus dans le dépôt et reliés au programme. Régénérer avec npm run build-evaluation-deck. Références officielles :\n${SOURCES.join('\n')}\nPreuves : https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/wiki/Native-Foundry-Evidence-FR`],
  },
];

function addText(slide, text, x, y, w, h, options = {}) {
  slide.addText(text, { x, y, w, h, fontFace: 'Segoe UI', fontSize: 18, color: C.ink, margin: 0, breakLine: false, valign: 'mid', ...options });
}

function renderSlide(pptx, entry, language, index) {
  const [title, items, notes] = entry[language];
  const slide = pptx.addSlide();
  const cover = entry.kind === 'cover';
  slide.background = { color: cover ? C.navy : C.paper };
  slide.addShape('rect', { x: 0, y: 0, w: 13.333, h: 0.09, line: { transparency: 100 }, fill: { color: C.blue } });
  addText(slide, language === 'en' ? 'FOUNDRY / EVALUATION ENGINEERING' : 'FOUNDRY / INGÉNIERIE DE L’ÉVALUATION', 0.6, 0.35, 12.1, 0.3, { fontSize: 11, bold: true, color: cover ? '91CEFF' : C.blue });
  addText(slide, title, 0.6, cover ? 1.5 : 0.85, 12.1, cover ? 1.2 : 0.9, { fontSize: cover ? 36 : 27, bold: true, color: cover ? 'FFFFFF' : C.navy });

  if (cover) {
    items.forEach((item, i) => addText(slide, item, 0.65, 3.2 + i * 0.75, 11.9, 0.6, { fontSize: 22, color: 'DDEEFF' }));
    addText(slide, language === 'en' ? 'EXACT CONTRACTS  /  CALIBRATED JUDGES  /  DEFENSIBLE DECISIONS' : 'CONTRATS EXACTS  /  JUGES CALIBRÉS  /  DÉCISIONS JUSTIFIÉES', 0.65, 5.7, 12, 0.7, { fontSize: 14, color: '91CEFF' });
  } else if (entry.kind === 'compare') {
    items.forEach((column, i) => {
      const [heading, ...lines] = column.split('|');
      const x = 0.6 + i * 6.2;
      slide.addShape('rect', { x, y: 2.05, w: 5.9, h: 4.25, fill: { color: C.pale }, line: { color: C.border } });
      addText(slide, heading, x + 0.3, 2.35, 5.3, 0.7, { fontSize: 23, bold: true, color: C.blue });
      lines.forEach((line, row) => addText(slide, line, x + 0.3, 3.3 + row * 0.85, 5.3, 0.65, { fontSize: 19 }));
    });
  } else if (entry.kind === 'flow') {
    items.forEach((item, i) => {
      const x = 0.6 + (i % 2) * 6.2;
      const y = 2.1 + Math.floor(i / 2) * 2.0;
      slide.addShape('rect', { x, y, w: 5.9, h: 1.55, fill: { color: C.pale }, line: { color: C.border } });
      addText(slide, String(i + 1).padStart(2, '0'), x + 0.25, y + 0.2, 0.7, 0.45, { fontSize: 25, bold: true, color: C.blue });
      addText(slide, item, x + 1.05, y + 0.2, 4.5, 1.15, { fontSize: 21, bold: true });
    });
  } else {
    items.forEach((item, i) => {
      const y = 2.0 + i * 1.03;
      addText(slide, String(i + 1).padStart(2, '0'), 0.65, y, 0.7, 0.65, { fontSize: 17, color: C.blue, bold: true });
      addText(slide, item, 1.45, y, 11.15, 0.8, { fontSize: 20 });
      slide.addShape('line', { x: 1.45, y: y + 0.91, w: 11.1, h: 0, line: { color: C.border, width: 0.5 } });
    });
  }
  const guide = `${BASE}/${language === 'fr' ? 'fr/' : ''}evaluation-guide.html`;
  const lab = `${BASE}/${language === 'fr' ? 'fr/' : ''}labs/lab-19-evaluation-engineering`;
  addText(slide, language === 'en' ? 'Synthetic training only | Guide + Lab 19' : 'Formation synthétique | Guide et Atelier 19', 0.6, 7.02, 10.7, 0.23, { fontSize: 10, color: cover ? 'DDEEFF' : C.muted, hyperlink: { url: guide } });
  addText(slide, `${index + 1} / ${SLIDES.length}`, 11.5, 7.02, 1.2, 0.23, { fontSize: 10, align: 'right', color: cover ? 'DDEEFF' : C.muted });
  slide.addNotes(`${notes}\n\nGuide: ${guide}\nLab 19: ${lab}\nSource: ${SOURCES[index % SOURCES.length]}`);
}

for (const language of ['en', 'fr']) {
  const pptx = new PptxGenJS();
  pptx.layout = 'LAYOUT_WIDE';
  pptx.author = 'Foundry Hosted Agents FSI workshop';
  pptx.subject = 'Deterministic contracts, native Foundry evaluation and quote-agent regression prevention';
  pptx.title = language === 'en' ? 'Evaluation Engineering' : "Ingénierie de l'évaluation";
  pptx.lang = language === 'en' ? 'en-CA' : 'fr-CA';
  pptx.theme = { headFontFace: 'Segoe UI', bodyFontFace: 'Segoe UI', lang: pptx.lang };
  SLIDES.forEach((entry, index) => renderSlide(pptx, entry, language, index));
  const fileName = path.join(OUT, `foundry-evaluation-engineering-${language}.pptx`);
  await pptx.writeFile({ fileName });
  console.log(`Wrote ${SLIDES.length} slides: ${fileName}`);
}
