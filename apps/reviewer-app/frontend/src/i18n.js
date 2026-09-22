// Hand-rolled bilingual dictionary. Mirrors the web-chat sibling's API
// (LANGUAGES, DEFAULT_LANGUAGE, STRINGS, translate) — no i18n library needed
// for this string count (per bilingual-ui-apps research, "No i18n Library
// Needed").

export const LANGUAGES = ['en-CA', 'fr-CA'];
export const DEFAULT_LANGUAGE = 'en-CA';

const STRINGS = {
  'en-CA': {
    disclaimer: {
      notice: 'Training simulation. Synthetic data only. Not an insurance quote and not a real underwriting decision.',
    },
    activity: {
      recordingDecision: 'Recording decision...',
    },
    topbar: {
      overline: 'DESJARDINS / CASE REVIEW',
      brand: 'Foundry',
      brandSub: 'CASE REVIEW',
      pilotBadge: '{env} pilot',
      notSignedIn: 'Not signed in',
      signOut: 'Sign out',
      languageToggleAria: 'Switch language',
    },
    queue: {
      heading: 'Pending review',
      refresh: 'Refresh',
      emptyFailed: 'The queue could not be loaded, so it is not known whether any cases are waiting. See the message above and use Refresh to try again.',
      emptyNone: 'No cases are waiting for review.',
      regionLabel: 'Case queue',
      caption: 'Cases awaiting review',
      headers: {
        case: 'Case', state: 'State', rev: 'Rev', preparer: 'Preparer',
        submitted: 'Submitted', premium: 'Premium', open: 'Open',
      },
      reviewButton: 'Review',
      reviewAria: 'Review case {caseId}',
      clearButton: 'Clear queue',
      clearGroupLabel: 'Confirm clear queue',
      clearLabel: 'Type {phrase} to confirm',
      clearHelp: 'This permanently deletes every case in the queue. This cannot be undone.',
      clearConfirmButton: 'Confirm clear queue',
      clearStatus: '{count} case(s) deleted.',
    },
    reason: {
      label: 'Reason code for {command} (optional)',
      placeholder: 'MISSING_PLAN',
      helpInvalid: 'Use up to 64 characters: A-Z, 0-9, underscore.',
      helpBlank: 'Leave blank to record no reason.',
      confirm: 'Confirm {command}',
      cancel: 'Cancel',
      commands: { reject: 'reject', revise: 'revise' },
    },
    approve: {
      groupLabel: 'Confirm approval',
      warning: 'Approving records the premium decision against this case and cannot be undone.',
      confirmButton: 'Confirm approve',
    },
    detail: {
      queueButton: 'Queue',
      facts: {
        state: 'State', revision: 'Revision', preparer: 'Preparer', reviewer: 'Reviewer',
        created: 'Created', submitted: 'Submitted', premium: 'Premium', currency: 'Currency',
        period: 'Period', status: 'Status', ruleIds: 'Rule ids', issues: 'Issues',
        rulebookVersion: 'Rulebook version',
      },
      reviewerUnassigned: 'Not assigned',
      calculationHeading: 'Calculation',
      notRecorded: 'Not recorded',
      notCalculated: 'Not calculated',
      decisionHeading: 'Decision',
      settled: 'This case is {state} and can no longer be decided.',
      perPeriod: 'per',
      auditHeading: 'Audit trail',
    },
    decisions: {
      approve: 'Approve', reject: 'Reject', revise: 'Send back for revision',
    },
    audit: {
      newState: 'NEW',
      transition: '{from} to {to}',
      meta: 'rev {revision} \u00b7 {actor} \u00b7 {at}',
    },
    gate: {
      overline: 'QUOTE REVIEW',
      heading: 'Reviews start with access.',
      checking: 'Verifying reviewer access...',
      restricted: 'Internal pilot / reviewers only',
      signIn: 'Sign in with Microsoft',
    },
    status: {
      recorded: 'Case {caseId} recorded as {state}.',
    },
    errors: {
      signInNeedsAttention: 'Your sign-in needs attention. Sign out and sign in again.',
      requestFailed: 'Request failed ({status}).',
      refreshFailedAfterDecision: 'Case {caseId} was recorded as {state}, but the list could not be refreshed. Use Refresh to reload it. Do not decide again.',
      configUnavailable: 'Configuration is unavailable.',
      startupFailed: 'The review workspace could not load. Refresh to try again.',
    },
    format: {
      unknown: 'Unknown',
      none: 'None',
      notCalculated: 'not calculated',
      amountUnverifiable: 'Amount unverifiable',
      noCurrencyRecorded: 'no currency recorded',
      notPriced: 'Not priced',
      decisionFailure: {
        selfApproval: 'You prepared this case, so you cannot decide it. Another reviewer must act.',
        authGenericFallback: 'You are not authorized to decide this case.',
        conflict: 'Another reviewer acted on this case first. It has been reloaded \u2014 review the current state before deciding again.',
        caseGone: 'This case no longer exists. Returning to the queue.',
        sessionExpired: 'Your sign-in is no longer valid. Sign out and sign in again.',
        fallback: 'Request failed ({status}).',
      },
    },
  },
  'fr-CA': {
    disclaimer: {
      notice: "Simulation de formation. Donn\u00e9es synth\u00e9tiques uniquement. Il ne s'agit pas d'une soumission d'assurance ni d'une d\u00e9cision r\u00e9elle de souscription.",
    },
    activity: {
      recordingDecision: 'Enregistrement de la d\u00e9cision...',
    },
    topbar: {
      overline: 'DESJARDINS / R\u00c9VISION DE DOSSIER',
      brand: 'Foundry',
      brandSub: 'R\u00c9VISION DE DOSSIER',
      pilotBadge: 'pilote {env}',
      notSignedIn: 'Non connect\u00e9',
      signOut: 'Se d\u00e9connecter',
      languageToggleAria: 'Changer de langue',
    },
    queue: {
      heading: 'Dossiers en attente de r\u00e9vision',
      refresh: 'Actualiser',
      emptyFailed: "La liste des dossiers n'a pas pu \u00eatre charg\u00e9e; on ignore donc si des dossiers sont en attente. Consultez le message ci-dessus et utilisez Actualiser pour r\u00e9essayer.",
      emptyNone: "Aucun dossier n'est en attente de r\u00e9vision.",
      regionLabel: 'File des dossiers',
      caption: 'Dossiers en attente de r\u00e9vision',
      headers: {
        case: 'Dossier', state: '\u00c9tat', rev: 'R\u00e9v.', preparer: 'Pr\u00e9parateur',
        submitted: 'Soumis', premium: 'Prime', open: 'Ouvrir',
      },
      reviewButton: 'R\u00e9viser',
      reviewAria: 'R\u00e9viser le dossier {caseId}',
      clearButton: 'Vider la file',
      clearGroupLabel: 'Confirmer le vidage de la file',
      clearLabel: 'Saisissez {phrase} pour confirmer',
      clearHelp: 'Cette action supprime d\u00e9finitivement tous les dossiers de la file. Cette op\u00e9ration est irr\u00e9versible.',
      clearConfirmButton: 'Confirmer le vidage de la file',
      clearStatus: '{count} dossier(s) supprim\u00e9(s).',
    },
    reason: {
      label: 'Code de motif pour {command} (facultatif)',
      placeholder: 'MISSING_PLAN',
      helpInvalid: "Utilisez jusqu'\u00e0 64 caract\u00e8res : A-Z, 0-9, tiret bas.",
      helpBlank: 'Laissez vide pour ne consigner aucun motif.',
      confirm: 'Confirmer {command}',
      cancel: 'Annuler',
      commands: { reject: 'le rejet', revise: 'la r\u00e9vision' },
    },
    approve: {
      groupLabel: "Confirmer l'approbation",
      warning: "L'approbation consigne la d\u00e9cision de prime pour ce dossier et ne peut \u00eatre annul\u00e9e.",
      confirmButton: "Confirmer l'approbation",
    },
    detail: {
      queueButton: "File d'attente",
      facts: {
        state: '\u00c9tat', revision: 'R\u00e9vision', preparer: 'Pr\u00e9parateur', reviewer: 'R\u00e9viseur',
        created: 'Cr\u00e9\u00e9', submitted: 'Soumis', premium: 'Prime', currency: 'Devise',
        period: 'P\u00e9riode', status: 'Statut', ruleIds: 'Identifiants de r\u00e8gle', issues: 'Probl\u00e8mes',
        rulebookVersion: 'Version du bar\u00e8me',
      },
      reviewerUnassigned: 'Non attribu\u00e9',
      calculationHeading: 'Calcul',
      notRecorded: 'Non consign\u00e9',
      notCalculated: 'Non calcul\u00e9',
      decisionHeading: 'D\u00e9cision',
      settled: "Ce dossier est \u00e0 l'\u00e9tat {state} et ne peut plus faire l'objet d'une d\u00e9cision.",
      perPeriod: 'par',
      auditHeading: "Journal d'audit",
    },
    decisions: {
      approve: 'Approuver', reject: 'Rejeter', revise: 'Retourner pour r\u00e9vision',
    },
    audit: {
      newState: 'NOUVEAU',
      transition: '{from} vers {to}',
      meta: 'r\u00e9v. {revision} \u00b7 {actor} \u00b7 {at}',
    },
    gate: {
      overline: 'R\u00c9VISION DE SOUMISSION',
      heading: 'La r\u00e9vision commence par l\u2019acc\u00e8s.',
      checking: 'V\u00e9rification de l\u2019acc\u00e8s du r\u00e9viseur...',
      restricted: 'Pilote interne / r\u00e9viseurs seulement',
      signIn: 'Se connecter avec Microsoft',
    },
    status: {
      recorded: 'Dossier {caseId} consign\u00e9 \u00e0 l\u2019\u00e9tat {state}.',
    },
    errors: {
      signInNeedsAttention: 'Votre connexion n\u00e9cessite une attention. D\u00e9connectez-vous puis reconnectez-vous.',
      requestFailed: '\u00c9chec de la demande ({status}).',
      refreshFailedAfterDecision: 'Le dossier {caseId} a \u00e9t\u00e9 consign\u00e9 \u00e0 l\u2019\u00e9tat {state}, mais la liste n\u2019a pas pu \u00eatre actualis\u00e9e. Utilisez Actualiser pour la recharger. Ne prenez pas une nouvelle d\u00e9cision.',
      configUnavailable: "La configuration n'est pas disponible.",
      startupFailed: "L'espace de r\u00e9vision n'a pas pu \u00eatre charg\u00e9. Actualisez pour r\u00e9essayer.",
    },
    format: {
      unknown: 'Inconnu',
      none: 'Aucun',
      notCalculated: 'non calcul\u00e9',
      amountUnverifiable: 'Montant non v\u00e9rifiable',
      noCurrencyRecorded: 'aucune devise consign\u00e9e',
      notPriced: 'Non tarif\u00e9',
      decisionFailure: {
        selfApproval: 'Vous avez pr\u00e9par\u00e9 ce dossier; vous ne pouvez donc pas le d\u00e9cider. Un autre r\u00e9viseur doit agir.',
        authGenericFallback: "Vous n'\u00eates pas autoris\u00e9 \u00e0 d\u00e9cider de ce dossier.",
        conflict: 'Un autre r\u00e9viseur a agi sur ce dossier en premier. Il a \u00e9t\u00e9 recharg\u00e9 \u2014 examinez l\u2019\u00e9tat actuel avant de d\u00e9cider \u00e0 nouveau.',
        caseGone: "Ce dossier n'existe plus. Retour \u00e0 la file d'attente.",
        sessionExpired: 'Votre connexion n\u2019est plus valide. D\u00e9connectez-vous puis reconnectez-vous.',
        fallback: '\u00c9chec de la demande ({status}).',
      },
    },
  },
};

function lookup(language, key) {
  let node = STRINGS[language];
  for (const part of key.split('.')) {
    if (node == null) return undefined;
    node = node[part];
  }
  return typeof node === 'string' ? node : undefined;
}

function interpolate(template, vars) {
  if (!vars) return template;
  return template.replace(/\{(\w+)\}/g, (match, name) => (
    Object.prototype.hasOwnProperty.call(vars, name) ? String(vars[name]) : match
  ));
}

/** Dot-path dictionary lookup with fallback to DEFAULT_LANGUAGE, then the raw key. */
export function translate(language, key, vars) {
  const template = lookup(language, key) ?? lookup(DEFAULT_LANGUAGE, key) ?? key;
  return interpolate(template, vars);
}
