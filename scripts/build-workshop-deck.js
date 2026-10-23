// Renders bilingual (EN/FR) overview decks for the Desjardins Bilingual
// Hosted Agents Workshop from the shared SLIDES content below into
// docs/assets/decks/foundry-hosted-agents-workshop-fsi-{en,fr}.pptx.
// Idempotent: re-running regenerates both files from scratch each time.
//
// Adapted from the sibling foundry-hosted-agents repository's
// scripts/build-workshop-deck.js: same generation library (PptxGenJS) and
// the same bilingual mechanism (one script, one language parameter per
// deck). The local curriculum is followed by the retained Azure demo and
// native-first session-2 capabilities. Deployment and live-feature evidence
// remain distinct from authored examples.
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import PptxGenJS from 'pptxgenjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '..');
const OUT_DIR = path.join(REPO_ROOT, 'docs', 'assets', 'decks');

const C = {
  bgLight: 'FAFBFC',
  blue: '0078D4', blueDark: '003D6B', blueDeep: '001B3D',
  border: 'E1E5E8',
  textPri: '1A1A1A', textLight: '767676',
};

function newSlide(pptx) {
  const s = pptx.addSlide();
  s.background = { fill: C.bgLight };
  return s;
}

function footer(slide, label) {
  slide.addShape('rect', { x: 0, y: 7.42, w: 13.33, h: 0.03, fill: { color: C.border } });
  slide.addText(label, {
    x: 0.5, y: 7.15, w: 9, h: 0.28, fontSize: 9, color: C.textLight, fontFace: 'Segoe UI',
  });
}

function header(slide, { kicker, title }) {
  slide.addShape('rect', { x: 0, y: 0, w: 13.33, h: 0.09, fill: { color: C.blue } });
  if (kicker) {
    slide.addText(kicker.toUpperCase(), {
      x: 0.5, y: 0.32, w: 12.3, h: 0.3, fontSize: 11, bold: true, color: C.blue,
      fontFace: 'Segoe UI', charSpacing: 1,
    });
  }
  slide.addText(title, {
    x: 0.5, y: 0.6, w: 12.3, h: 0.7, fontSize: 26, bold: true, color: C.blueDeep, fontFace: 'Segoe UI',
  });
  slide.addShape('rect', { x: 0.5, y: 1.3, w: 12.3, h: 0.012, fill: { color: C.border } });
}

function bullets(slide, items) {
  const runs = items.map((text) => ({
    text,
    options: {
      color: C.textPri, fontSize: 15, fontFace: 'Segoe UI',
      breakLine: true, bullet: { code: '25CF', indent: 20 },
    },
  }));
  slide.addText(runs, {
    x: 0.6, y: 1.6, w: 12.1, h: 5.5, valign: 'top', lineSpacingMultiple: 1.25,
  });
}

// ── Shared bilingual slide content ──────────────────────────────────────
// Each lab entry mirrors one lab file under docs/labs/ and docs/fr/labs/:
// { kicker, title: {en, fr}, bullets: {en: [...], fr: [...]} }, drawn from
// that lab's own Learning Objectives section.
const LAB_SLIDES = [
  {
    kicker: { en: 'Lab 00', fr: 'Atelier 00' },
    title: { en: 'Setup', fr: 'Configuration' },
    bullets: {
      en: [
        'Create a Python virtual environment for the workshop',
        'Install dependencies for the calculator, the approval repository, both MCP servers, and the agent',
        'Run the existing pytest suites as a sanity check',
        'Locate the synthetic-only, non-binding disclosure repeated in every lab',
      ],
      fr: [
        'Créer un environnement virtuel Python pour l\u2019atelier',
        'Installer les dépendances du calculateur, du dépôt d\u2019approbation, des deux serveurs MCP et de l\u2019agent',
        'Exécuter les suites pytest existantes comme vérification de bon fonctionnement',
        'Repérer la mention synthétique et non contraignante répétée dans chaque atelier',
      ],
    },
  },
  {
    kicker: { en: 'Lab 01', fr: 'Atelier 01' },
    title: { en: 'Fixtures and Schema', fr: 'Données et schéma' },
    bullets: {
      en: [
        'Describe the five synthetic fixtures and the calculation status each produces',
        'Explain the schema\u2019s if/then/else rules tying status to amountCents and issues',
        'Explain the rule tying workflow state to approvedRevision',
        'Validate every fixture against the JSON Schema',
      ],
      fr: [
        'Décrire les cinq données synthétiques et le statut de calcul que chacune produit',
        'Expliquer les règles if/then/else du schéma liant le statut à amountCents et issues',
        'Expliquer la règle liant l\u2019état de flux de travail à approvedRevision',
        'Valider chaque donnée par rapport au schéma JSON',
      ],
    },
  },
  {
    kicker: { en: 'Lab 02', fr: 'Atelier 02' },
    title: { en: 'The Deterministic Calculator', fr: 'Le calculateur déterministe' },
    bullets: {
      en: [
        'Trace calculate_quote\u2019s resolution order in apps/workshop/calculator.py',
        'State the four calculation statuses the calculator can return',
        'Add a new test case and confirm it passes',
        'Prove a rulebook lookup miss never produces an invented amount',
      ],
      fr: [
        'Retracer l\u2019ordre de résolution de calculate_quote dans apps/workshop/calculator.py',
        'Énoncer les quatre statuts de calcul possibles',
        'Ajouter un nouveau cas de test et confirmer qu\u2019il réussit',
        'Prouver qu\u2019un référentiel incomplet ne produit jamais un montant inventé',
      ],
    },
  },
  {
    kicker: { en: 'Lab 03', fr: 'Atelier 03' },
    title: { en: 'Approval Repository and State Machine', fr: 'Dépôt d\u2019approbation et machine à états' },
    bullets: {
      en: [
        'Describe the DRAFT, PENDING_REVIEW, APPROVED, REJECTED state machine',
        'Explain why a reviewer can never be the same person who prepared a case',
        'Trigger and catch a SelfApprovalError',
        'Confirm revising a decided case resets it to DRAFT',
      ],
      fr: [
        'Décrire la machine à états DRAFT, PENDING_REVIEW, APPROVED, REJECTED',
        'Expliquer pourquoi un réviseur ne peut jamais être la personne qui a préparé un dossier',
        'Déclencher et intercepter une SelfApprovalError',
        'Confirmer qu\u2019une révision d\u2019un dossier tranché le remet à DRAFT',
      ],
    },
  },
  {
    kicker: { en: 'Lab 04', fr: 'Atelier 04' },
    title: { en: 'The Application MCP Server', fr: 'Le serveur MCP d\u2019application' },
    bullets: {
      en: [
        'Explain why application-server runs independently, with no shared runtime',
        'Confirm it exposes exactly one tool: get_application(fixture_id)',
        'Start the server and query it for a known and an unknown fixture ID',
        'Confirm no write-capable tool is exposed',
      ],
      fr: [
        'Expliquer pourquoi application-server s\u2019exécute indépendamment, sans exécution partagée',
        'Confirmer qu\u2019il n\u2019expose qu\u2019un seul outil : get_application(fixture_id)',
        'Démarrer le serveur et l\u2019interroger pour un identifiant connu et un identifiant inconnu',
        'Confirmer qu\u2019aucun outil capable d\u2019écriture n\u2019est exposé',
      ],
    },
  },
  {
    kicker: { en: 'Lab 05', fr: 'Atelier 05' },
    title: { en: 'The Rulebook MCP Server', fr: 'Le serveur MCP de référentiel' },
    bullets: {
      en: [
        'Explain why rulebook-server runs independently, with no shared runtime',
        'Confirm it exposes exactly one tool: get_rulebook(rulebook_id)',
        'Start the server and query it for the pinned rulebook and an unknown one',
        'Explain the WORKSHOP_AUTHORS_ONLY authority marker',
      ],
      fr: [
        'Expliquer pourquoi rulebook-server s\u2019exécute indépendamment, sans exécution partagée',
        'Confirmer qu\u2019il n\u2019expose qu\u2019un seul outil : get_rulebook(rulebook_id)',
        'Démarrer le serveur et l\u2019interroger pour le référentiel épinglé et un identifiant inconnu',
        'Expliquer le marqueur d\u2019autorité WORKSHOP_AUTHORS_ONLY',
      ],
    },
  },
  {
    kicker: { en: 'Lab 06', fr: 'Atelier 06' },
    title: { en: 'The LangGraph Agent', fr: 'L\u2019agent LangGraph' },
    bullets: {
      en: [
        'Name the three sequential stages: intake, reference lookup, composition',
        'Explain the supervisor\u2019s routing rule and its invalid-case short-circuit',
        'Explain why toolbox.py calls MCP tools in-process, not over a client session',
        'Confirm the agent never calls approve, reject, or revise',
      ],
      fr: [
        'Nommer les trois étapes séquentielles : accueil, recherche de référence, composition',
        'Expliquer la règle de routage du superviseur et son court-circuit pour un cas invalide',
        'Expliquer pourquoi toolbox.py appelle les outils MCP en processus, pas via une session client',
        'Confirmer que l\u2019agent n\u2019appelle jamais approve, reject ou revise',
      ],
    },
  },
  {
    kicker: { en: 'Lab 07', fr: 'Atelier 07' },
    title: { en: 'Run the Agent End to End', fr: 'Exécuter l\u2019agent de bout en bout' },
    bullets: {
      en: [
        'Run the CLI end to end against a fixture, with no Azure call',
        'Confirm the applicant message never includes an amount or reviewer-only field',
        'Act as the human reviewer directly against ApprovalRepository',
        'Confirm an invalid case reference produces a bounded rejection message',
      ],
      fr: [
        'Exécuter l\u2019interface en ligne de commande sur une donnée, sans appel à Azure',
        'Confirmer que le message au demandeur ne contient jamais un montant ou un champ réviseur',
        'Agir comme réviseur humain directement contre ApprovalRepository',
        'Confirmer qu\u2019une référence invalide produit un message de refus borné',
      ],
    },
  },
  {
    kicker: { en: 'Lab 08', fr: 'Atelier 08' },
    title: { en: 'Evaluation Suite', fr: 'Suite d\u2019évaluation' },
    bullets: {
      en: [
        'Locate the paired EN/FR golden dataset and the deterministic evaluation gate',
        'Name the seven check categories the gate is designed to cover',
        'Run the evaluation gate against this project\u2019s implementation',
        'Write a small deterministic arithmetic check of your own',
      ],
      fr: [
        'Repérer le jeu de données de référence bilingue et la porte d\u2019évaluation déterministe',
        'Nommer les sept catégories de vérification que la porte doit couvrir',
        'Exécuter la porte d\u2019évaluation contre l\u2019implémentation de ce projet',
        'Écrire votre propre petite vérification arithmétique déterministe',
      ],
    },
  },
  {
    kicker: { en: 'Lab 09', fr: 'Atelier 09' },
    title: { en: 'Local Cleanup, Retained Azure Demo', fr: 'Nettoyage local, démo Azure conservée' },
    bullets: {
      en: [
        'Stop any MCP server process started in Labs 04-05',
        'Remove any on-disk approval-repository state you created',
        'The local curriculum does not itself provision Azure resources',
        'Keep the restored staging and production demo deployed; do not run azd down',
      ],
      fr: [
        'Arrêter tout processus de serveur MCP démarré aux ateliers 04-05',
        'Retirer tout état sur disque créé pour le dépôt d\u2019approbation',
        'Le parcours local ne provisionne pas lui-même de ressources Azure',
        'Conserver la démo restaurée en staging et production ; ne pas lancer azd down',
      ],
    },
  },
];

const SHOWCASE_SLIDES = [
  {
    kicker: { en: 'Session 2 / Native first', fr: 'Séance 2 / Natif en premier' },
    title: { en: 'What Lives in Foundry?', fr: 'Que trouve-t-on dans Foundry ?' },
    bullets: {
      en: [
        'Foundry: project, hosted agent identity/version, toolboxes, evaluations and native APIs',
        'Azure Container Apps: chat, reviewer and read-only MCP services remain external to the project',
        'Cosmos DB: auditable business approval state, not a substitute for native memory',
        'Keep the restored demo running; evaluate additions separately before release',
      ],
      fr: [
        'Foundry : projet, identité/version de l’agent, toolboxes, évaluations et API natives',
        'Azure Container Apps : clavardage, révision et MCP restent externes au projet',
        'Cosmos DB : état métier auditable des approbations, distinct de la mémoire native',
        'Conserver la démo restaurée ; évaluer les ajouts séparément avant publication',
      ],
    },
  },
  {
    kicker: { en: 'Session 2 / Knowledge and services', fr: 'Séance 2 / Connaissances et services' },
    title: { en: 'Ground the Answer in Real Sources', fr: 'Ancrer la réponse dans les sources' },
    bullets: {
      en: [
        'Native File Search verified: 6 versioned sources, 6 cited EN/FR answers and 2 refusals',
        'Managed retrieval needs neither a new Search service nor an embedding deployment',
        'Native Document Intelligence verified: 8 grounded invoice fields, without new model deployment',
        'Foundry IQ/Search integration is separate; no hosted-agent knowledge attachment is claimed',
      ],
      fr: [
        'File Search natif vérifié : 6 sources versionnées, 6 réponses EN/FR citées et 2 refus',
        'La récupération gérée ne demande ni nouveau Search ni déploiement d’embedding',
        'Document Intelligence natif vérifié : 8 champs de facture ancrés, sans nouveau modèle',
        'Foundry IQ/Search reste distinct ; aucune connexion à l’agent hébergé n’est affirmée',
      ],
    },
  },
  {
    kicker: { en: 'Session 2 / Memory and skills', fr: 'Séance 2 / Mémoire et compétences' },
    title: { en: 'Reuse Without Overclaiming Isolation', fr: 'Réutiliser sans surestimer l’isolation' },
    bullets: {
      en: [
        'Inspect actual stored synthetic memory and prove negative cross-scope lookup',
        'A memory scope partitions data; it does not authorize the caller',
        'Register a project-authored runtime skill; do not call it a Microsoft built-in',
        'Verified: native skill v1 consumed by an isolated Responses runtime, not the hosted agent',
      ],
      fr: [
        'Inspecter la mémoire synthétique réelle et tester l’absence dans un autre scope',
        'Un scope partitionne les données ; il n’autorise pas l’appelant',
        'Enregistrer une compétence de projet, sans la présenter comme intégrée par Microsoft',
        'Vérifié : compétence native v1 consommée par Responses isolé, pas par l’agent hébergé',
      ],
    },
  },
  {
    kicker: { en: 'Session 2 / Evaluate and investigate', fr: 'Séance 2 / Évaluer et investiguer' },
    title: { en: 'Measured Native Evidence', fr: 'Des preuves natives mesurées' },
    bullets: {
      en: [
        'Native generation succeeded: 8 examples downloaded; local fixtures are not a generation job',
        'Built-in retrieval evaluator v15: relevant control 5/5, irrelevant control 1/5 in staging',
        'Both native grounding judges missed a bad control; no quality pass or optimization claimed',
        'Approved native red-team scan failed before scoring; this is not a safety pass',
        'Trace deterministic stages and policy hashes; never invent LLM tokens or model spans',
      ],
      fr: [
        'Génération native réussie : 8 exemples téléchargés ; une donnée locale n’est pas un job natif',
        'Évaluateur retrieval intégré v15 : contexte pertinent 5/5, non pertinent 1/5 en staging',
        'Les deux juges d’ancrage ont manqué le contrôle erroné ; ni succès qualité ni gain affirmé',
        'Le scan red team natif approuvé a échoué avant notation ; aucun succès sécurité',
        'Tracer les étapes déterministes et le hachage ; ne pas inventer de jetons ou d’appels LLM',
      ],
    },
  },
  {
    kicker: { en: 'Session 2 / Architecture decision', fr: 'Séance 2 / Décision d’architecture' },
    title: { en: 'Compare Natively Before Adding Platforms', fr: 'Comparer nativement avant d’ajouter une plateforme' },
    bullets: {
      en: [
        'Persist evaluator version, source revision, dataset hash, parameters and native run IDs',
        'Foundry evaluations compare measured variants; they are not a renamed MLflow service',
        'Azure ML offers MLflow tracking; do not imply a verified Foundry Experiments blade',
        'Add Langfuse or Phoenix only for a documented unmet requirement and approved data boundary',
      ],
      fr: [
        'Conserver version d’évaluateur, révision Git, hachage des données, paramètres et ID natifs',
        'Les évaluations comparent des variantes ; ce n’est pas un service MLflow renommé',
        'Azure ML offre MLflow ; aucun écran Experiments Foundry équivalent n’est confirmé',
        'Ajouter Langfuse ou Phoenix seulement pour un écart mesuré et une frontière approuvée',
      ],
    },
  },
  {
    kicker: { en: 'Session 2 / Current evidence', fr: 'Séance 2 / Preuves actuelles' },
    title: { en: 'Verified and Deferred Are Different', fr: 'Vérifié et différé restent distincts' },
    bullets: {
      en: [
        'Retained quote release: staging v6 and production v7; documentation does not redeploy it',
        'Isolated staging IQ companion v2: 8/8 bilingual checks; production remains unpromoted',
        'Native Content Understanding invoice extraction passed in staging and production',
        'Protocol-only red-team shadow passes offline tests, not native acceptance or scan approval',
      ],
      fr: [
        'Livraison conservée : staging v6 et production v7 ; la documentation ne la redéploie pas',
        'Compagnon IQ staging v2 isolé : 8/8 contrôles bilingues ; production non promue',
        'Extraction de facture Content Understanding native réussie en staging et production',
        'Clone red team protocolaire testé hors ligne, sans acceptation native ni autorisation de scan',
      ],
    },
    notes: {
      en: 'Retained release 39527950931 attempt 2, source 2c3f13b. Staging IQ is fsi-showcase-iq:2, not the quote agent. Production IQ is blocked by a missing Search query role. The original approved native red-team scan failed before scoring. Its approval does not authorize the new protocol shadow. Deferred work: https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/issues/49\nEvidence: https://devopsabcs-engineering.github.io/foundry-hosted-agents-fsi/showcase-evidence.html',
      fr: 'Livraison conservée 39527950931, tentative 2, source 2c3f13b. IQ staging est fsi-showcase-iq:2, pas l’agent de soumission. Le rôle de requête Search manque pour IQ production. Le scan red team natif approuvé a échoué avant notation; son autorisation ne couvre pas le nouveau clone protocolaire. Travail différé : https://github.com/devopsabcs-engineering/foundry-hosted-agents-fsi/issues/49\nPreuves : https://devopsabcs-engineering.github.io/foundry-hosted-agents-fsi/fr/showcase-evidence.html',
    },
  },
  {
    kicker: { en: 'Lab 19 / Evaluation engineering', fr: 'Atelier 19 / Ingénierie des évaluations' },
    title: { en: 'Continue with the Evaluation Deep Lab', fr: 'Poursuivre avec l’atelier d’évaluation' },
    bullets: {
      en: [
        'Complete curriculum: local Labs 00-09, pilot 10-14, native 15-18 and evaluation Lab 19',
        'Read-only portal walkthrough: overview, detailed results and three built-in evaluator captures',
        'Use supplied EN/FR synthetic JSONL controls; uploads and paid submissions need approval',
        'Dedicated evaluation decks: 37 editable slides per language, with instructor notes',
      ],
      fr: [
        'Programme complet : bases 00-09, pilote 10-14, natif 15-18 et évaluation à l’Atelier 19',
        'Portail en lecture seule : vue d’ensemble, résultats et trois évaluateurs intégrés',
        'Contrôles JSONL synthétiques EN/FR fournis ; téléversement et soumission payante à autoriser',
        'Présentations d’évaluation distinctes : 37 diapositives modifiables par langue et notes',
      ],
    },
    notes: {
      en: 'Allow 3-4 hours for ten exercises. The practice rows are authored synthetic controls, not captured agent responses. Retained screenshots prove only their identified run.\nGuide: https://devopsabcs-engineering.github.io/foundry-hosted-agents-fsi/evaluation-guide.html\nLab: https://devopsabcs-engineering.github.io/foundry-hosted-agents-fsi/labs/lab-19-evaluation-engineering\nDataset: https://devopsabcs-engineering.github.io/foundry-hosted-agents-fsi/assets/datasets/portal-practice-en-CA.jsonl\nDeck: https://devopsabcs-engineering.github.io/foundry-hosted-agents-fsi/assets/decks/foundry-evaluation-engineering-en.pptx',
      fr: 'Prévoir 3 à 4 heures pour dix exercices. Les contrôles synthétiques rédigés ne sont pas des réponses agent capturées. Les captures ne prouvent que l’essai identifié.\nGuide : https://devopsabcs-engineering.github.io/foundry-hosted-agents-fsi/fr/evaluation-guide.html\nAtelier : https://devopsabcs-engineering.github.io/foundry-hosted-agents-fsi/fr/labs/lab-19-evaluation-engineering\nDonnées : https://devopsabcs-engineering.github.io/foundry-hosted-agents-fsi/assets/datasets/portal-practice-fr-CA.jsonl\nPrésentation : https://devopsabcs-engineering.github.io/foundry-hosted-agents-fsi/assets/decks/foundry-evaluation-engineering-fr.pptx',
    },
  },
];

const TITLE_SLIDE = {
  title: {
    en: 'Desjardins Bilingual Hosted Agents Workshop',
    fr: 'Atelier bilingue Desjardins sur les agents hébergés',
  },
  subtitle: {
    en: 'Hands-on: a synthetic auto-insurance quote-preparation agent with a deterministic calculator and a mandatory employee-approval gate',
    fr: 'Pratique : un agent synthétique de préparation de soumissions d\u2019assurance auto avec un calculateur déterministe et une étape d\u2019approbation obligatoire',
  },
};

const AGENDA_SLIDE = {
  kicker: { en: 'Agenda', fr: 'Programme' },
  title: { en: 'Local Foundations, Hosted Demo, Native Showcase', fr: 'Bases locales, démo hébergée et fonctions natives' },
  bullets: {
    en: [...LAB_SLIDES.map((lab) => `${lab.kicker.en} \u2014 ${lab.title.en}`), 'Labs 10-14: controlled pilot surfaces', 'Labs 15-18: isolated native showcase', 'Lab 19: evaluation engineering deep lab'],
    fr: [...LAB_SLIDES.map((lab) => `${lab.kicker.fr} \u2014 ${lab.title.fr}`), 'Ateliers 10-14 : pilote contrôlé', 'Ateliers 15-18 : fonctions natives isolées', 'Atelier 19 : évaluation approfondie'],
  },
};

const CLOSING_SLIDE = {
  kicker: { en: 'Wrap-up', fr: 'Conclusion' },
  title: { en: 'A Retained, Synthetic Customer Demo', fr: 'Une démo client synthétique conservée' },
  bullets: {
    en: [
      'Every fixture, rulebook, and calculator output is synthetic and non-binding',
      'Staging and production are restored; enhancements require separate measured live acceptance',
      'A human reviewer, never the agent, decides whether a draft can reach the applicant',
      'Full bilingual step-by-step labs: this deck\u2019s companion GitHub Pages site',
    ],
    fr: [
      'Chaque donnée, règle et résultat de calcul est synthétique et non contraignant',
      'Staging et production sont restaurés ; les ajouts nécessitent des preuves réelles distinctes',
      'Une personne réviseure humaine, jamais l\u2019agent, décide si une ébauche peut atteindre le demandeur',
      'Ateliers complets, bilingues, pas à pas : le site GitHub Pages compagnon de ce deck',
    ],
  },
};

function buildDeck(lang) {
  const pptx = new PptxGenJS();
  pptx.defineLayout({ name: 'WIDE', width: 13.33, height: 7.5 });
  pptx.layout = 'WIDE';

  const titleSlide = newSlide(pptx);
  titleSlide.background = { fill: C.blueDeep };
  titleSlide.addText(TITLE_SLIDE.title[lang], {
    x: 0.8, y: 2.7, w: 11.7, h: 1.3, fontSize: 36, bold: true, color: 'FFFFFF', fontFace: 'Segoe UI',
  });
  titleSlide.addText(TITLE_SLIDE.subtitle[lang], {
    x: 0.8, y: 3.9, w: 11.7, h: 0.9, fontSize: 16, color: 'CFE4FA', fontFace: 'Segoe UI', italic: true,
  });
  titleSlide.addNotes(
    lang === 'en'
      ? 'Every fixture, rulebook, and calculator output in this workshop is synthetic and non-binding. No regulator or insurer has reviewed or endorsed this material.'
      : 'Chaque donnée, règle et résultat de calcul de cet atelier est synthétique et non contraignant. Aucun organisme de réglementation ni assureur n\u2019a révisé ou approuvé ce contenu.'
  );

  const agendaSlide = newSlide(pptx);
  header(agendaSlide, { kicker: AGENDA_SLIDE.kicker[lang], title: AGENDA_SLIDE.title[lang] });
  bullets(agendaSlide, AGENDA_SLIDE.bullets[lang]);
  footer(agendaSlide, lang === 'en' ? 'Desjardins Bilingual Hosted Agents Workshop' : 'Atelier bilingue Desjardins sur les agents hébergés');

  for (const lab of [...LAB_SLIDES, ...SHOWCASE_SLIDES]) {
    const slide = newSlide(pptx);
    header(slide, { kicker: lab.kicker[lang], title: lab.title[lang] });
    bullets(slide, lab.bullets[lang]);
    footer(slide, lang === 'en' ? 'Desjardins Bilingual Hosted Agents Workshop' : 'Atelier bilingue Desjardins sur les agents hébergés');
    if (lab.notes) slide.addNotes(lab.notes[lang]);
  }

  const closingSlide = newSlide(pptx);
  header(closingSlide, { kicker: CLOSING_SLIDE.kicker[lang], title: CLOSING_SLIDE.title[lang] });
  bullets(closingSlide, CLOSING_SLIDE.bullets[lang]);
  footer(closingSlide, lang === 'en' ? 'Desjardins Bilingual Hosted Agents Workshop' : 'Atelier bilingue Desjardins sur les agents hébergés');

  pptx.slides.forEach((slide, index) => slide.addText(`${index + 1} / ${pptx.slides.length}`, {
    x: 12.4, y: 7.14, w: 0.6, h: 0.24, fontSize: 9, color: C.textLight, align: 'right',
  }));

  return pptx;
}

async function main() {
  const fs = await import('node:fs');
  fs.mkdirSync(OUT_DIR, { recursive: true });

  const en = buildDeck('en');
  await en.writeFile({ fileName: path.join(OUT_DIR, 'foundry-hosted-agents-workshop-fsi-en.pptx') });

  const fr = buildDeck('fr');
  await fr.writeFile({ fileName: path.join(OUT_DIR, 'foundry-hosted-agents-workshop-fsi-fr.pptx') });

  console.log('Wrote:', OUT_DIR);
}

main();
