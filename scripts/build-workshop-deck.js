// Renders bilingual (EN/FR) overview decks for the Desjardins Bilingual
// Hosted Agents Workshop from the shared SLIDES content below into
// docs/assets/decks/foundry-hosted-agents-workshop-fsi-{en,fr}.pptx.
// Idempotent: re-running regenerates both files from scratch each time.
//
// Adapted from the sibling foundry-hosted-agents repository's
// scripts/build-workshop-deck.js: same generation library (PptxGenJS) and
// the same bilingual mechanism (one script, one language parameter per
// deck). Slide content is limited to a title/objectives-per-lab summary,
// scoped to this project's ten quote-preparation labs; it does not carry
// forward the sibling's release-evidence slides, since this workshop
// never deploys to Azure (see docs/labs/lab-09-teardown.md).
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
    title: { en: 'Teardown', fr: 'Démantèlement' },
    bullets: {
      en: [
        'Stop any MCP server process started in Labs 04-05',
        'Remove any on-disk approval-repository state you created',
        'Confirm this workshop provisioned no Azure resources',
        'Confirm there is nothing to azd down or delete in a subscription',
      ],
      fr: [
        'Arrêter tout processus de serveur MCP démarré aux ateliers 04-05',
        'Retirer tout état sur disque créé pour le dépôt d\u2019approbation',
        'Confirmer que cet atelier n\u2019a provisionné aucune ressource Azure',
        'Confirmer qu\u2019il n\u2019y a rien à supprimer via azd down ou dans un abonnement',
      ],
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
  title: { en: 'Ten Labs, One Local Vertical Slice', fr: 'Dix ateliers, une tranche verticale locale' },
  bullets: {
    en: LAB_SLIDES.map((lab) => `${lab.kicker.en} \u2014 ${lab.title.en}`),
    fr: LAB_SLIDES.map((lab) => `${lab.kicker.fr} \u2014 ${lab.title.fr}`),
  },
};

const CLOSING_SLIDE = {
  kicker: { en: 'Wrap-up', fr: 'Conclusion' },
  title: { en: 'A Local, Synthetic Vertical Slice', fr: 'Une tranche verticale locale et synthétique' },
  bullets: {
    en: [
      'Every fixture, rulebook, and calculator output is synthetic and non-binding',
      'The calculator, approval repository, MCP servers, and agent all run locally; no Azure deployment exists yet',
      'A human reviewer, never the agent, decides whether a draft can reach the applicant',
      'Full bilingual step-by-step labs: this deck\u2019s companion GitHub Pages site',
    ],
    fr: [
      'Chaque donnée, règle et résultat de calcul est synthétique et non contraignant',
      'Le calculateur, le dépôt d\u2019approbation, les serveurs MCP et l\u2019agent s\u2019exécutent tous localement ; aucun déploiement Azure n\u2019existe encore',
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

  for (const lab of LAB_SLIDES) {
    const slide = newSlide(pptx);
    header(slide, { kicker: lab.kicker[lang], title: lab.title[lang] });
    bullets(slide, lab.bullets[lang]);
    footer(slide, lang === 'en' ? 'Desjardins Bilingual Hosted Agents Workshop' : 'Atelier bilingue Desjardins sur les agents hébergés');
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
