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
      heading: 'Case queue',
      refresh: 'Refresh',
      emptyFailed: 'The queue could not be loaded, so it is not known whether any cases are waiting. See the message above and use Refresh to try again.',
      emptyNone: 'No cases match this state filter.',
      regionLabel: 'Case queue',
      caption: 'Cases matching the selected state',
      headers: {
        case: 'Case', state: 'State', rev: 'Rev', preparer: 'Preparer',
        submitted: 'Updated', premium: 'Premium', open: 'Open',
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
        created: 'Created', submitted: 'Updated', premium: 'Premium', currency: 'Currency',
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
    revision: {
      heading: 'Correct and prepare again',
      filter: 'Case state',
      states: { active: 'Active (draft and pending review)', DRAFT: 'Draft', PENDING_REVIEW: 'Pending review', APPROVED: 'Approved', REJECTED: 'Rejected' },
      jurisdiction: 'Jurisdiction (optional)',
      vehicleClass: 'Vehicle class (optional)',
      plan: 'Plan (optional)',
      keepOriginal: 'Keep original / saved value',
      help: 'Select at least one synthetic correction. Saved corrections accumulate across revisions. A blank field keeps the original or previously saved value. No prices or free text are accepted.',
      ownPreparer: 'Preparing this revision makes you its preparer. Another employee must approve or decide it.',
      persisted: 'Saved corrections and preparation',
      noCorrections: 'No corrections recorded.',
      current: 'Current revision {revision}',
      previous: 'Previous preparation — revision {revision}, not the current revision',
      statuses: { REQUESTED: 'Requested', COMPLETED: 'Completed', FAILED: 'Failed' },
      pending: 'Preparation is still requested; its outcome may be unknown. Refresh to check before retrying.',
      retryNotice: 'Explicit retry: a new request key will be used. A pending request has a 240-second server lease; retrying before it expires may be refused (409). Refresh first to check whether it completed.',
      retry: 'Retry preparation',
      prepare: 'Prepare revised case',
      refresh: 'Refresh case and audit',
      preparing: 'Preparing revised case… This may take a moment.',
      prepared: 'Revised case prepared and submitted for review. Another employee must decide it.',
      prepareFailed: 'Preparation was not confirmed. The latest case and audit were requested; check their state before retrying.',
      prepareOutcomeUnknown: 'The hosted-agent outcome could not be confirmed. Refresh before an explicit retry.',
      unavailable: 'Current case detail is unavailable. Displayed case values may be outdated; decisions and preparation are disabled. Refresh the case and audit to continue.',
      auditUnavailable: 'Current audit trail unavailable. Refresh the case and audit; no previous trail is shown as current.',
      draftDecision: 'This draft must be prepared and submitted again before another employee can decide it.',
      previousCalculation: 'Previous submitted calculation — not current',
      responseId: 'Hosted-agent response ID',
      preparationId: 'Preparation correlation ID',
      reasonCode: 'Reason code',
      amountCents: 'Recorded amount (cents)',
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
      refreshFailedAfterDecision: 'Case {caseId} was recorded as {state}, but the case/audit or queue refresh failed. Refresh to reload it. Do not decide again.',
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
      heading: 'File des dossiers',
      refresh: 'Actualiser',
      emptyFailed: "La liste des dossiers n'a pas pu \u00eatre charg\u00e9e; on ignore donc si des dossiers sont en attente. Consultez le message ci-dessus et utilisez Actualiser pour r\u00e9essayer.",
      emptyNone: 'Aucun dossier ne correspond au filtre d’état.',
      regionLabel: 'File des dossiers',
      caption: 'Dossiers correspondant au filtre d’état',
      headers: {
        case: 'Dossier', state: '\u00c9tat', rev: 'R\u00e9v.', preparer: 'Pr\u00e9parateur',
        submitted: 'Mis à jour', premium: 'Prime', open: 'Ouvrir',
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
        created: 'Cr\u00e9\u00e9', submitted: 'Mis à jour', premium: 'Prime', currency: 'Devise',
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
    revision: {
      heading: 'Corriger et préparer de nouveau',
      filter: 'État du dossier',
      states: { active: 'Actifs (brouillons et en attente)', DRAFT: 'Brouillon', PENDING_REVIEW: 'En attente de révision', APPROVED: 'Approuvé', REJECTED: 'Rejeté' },
      jurisdiction: 'Territoire (facultatif)',
      vehicleClass: 'Catégorie du véhicule (facultative)',
      plan: 'Régime (facultatif)',
      keepOriginal: 'Conserver la valeur initiale ou enregistrée',
      help: 'Sélectionnez au moins une correction synthétique. Les corrections enregistrées s’accumulent au fil des révisions. Un champ vide conserve la valeur initiale ou enregistrée. Aucun prix ni texte libre n’est accepté.',
      ownPreparer: 'En préparant cette révision, vous devenez son préparateur. Un autre employé doit l’approuver ou la décider.',
      persisted: 'Corrections et préparation enregistrées',
      noCorrections: 'Aucune correction consignée.',
      current: 'Révision actuelle {revision}',
      previous: 'Préparation précédente — révision {revision}, pas la révision actuelle',
      statuses: { REQUESTED: 'Demandée', COMPLETED: 'Terminée', FAILED: 'Échouée' },
      pending: 'La préparation est toujours demandée; son résultat peut être inconnu. Actualisez pour vérifier avant de réessayer.',
      retryNotice: 'Nouvelle tentative explicite : une nouvelle clé sera utilisée. Une demande en attente a un bail serveur de 240 secondes; une tentative avant son expiration peut être refusée (409). Actualisez d’abord pour vérifier si elle est terminée.',
      retry: 'Réessayer la préparation',
      prepare: 'Préparer le dossier révisé',
      refresh: 'Actualiser le dossier et le journal',
      preparing: 'Préparation du dossier révisé… Cela peut prendre un moment.',
      prepared: 'Dossier révisé préparé et soumis pour révision. Un autre employé doit le décider.',
      prepareFailed: 'La préparation n’est pas confirmée. Le dossier et le journal actuels ont été demandés; vérifiez leur état avant de réessayer.',
      prepareOutcomeUnknown: 'Le résultat de l’agent hébergé n’a pas pu être confirmé. Actualisez avant une nouvelle tentative explicite.',
      unavailable: 'Le détail actuel du dossier est indisponible. Les valeurs affichées peuvent être périmées; les décisions et la préparation sont désactivées. Actualisez le dossier et le journal pour continuer.',
      auditUnavailable: 'Journal actuel indisponible. Actualisez le dossier et le journal; aucun journal précédent n’est présenté comme actuel.',
      draftDecision: 'Ce brouillon doit être préparé et soumis de nouveau avant qu’un autre employé puisse le décider.',
      previousCalculation: 'Calcul soumis précédemment — non actuel',
      responseId: 'Identifiant de réponse de l’agent hébergé',
      preparationId: 'Identifiant de corrélation de préparation',
      reasonCode: 'Code de motif',
      amountCents: 'Montant consigné (cents)',
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
      refreshFailedAfterDecision: 'Le dossier {caseId} a été consigné à l’état {state}, mais l’actualisation du dossier, du journal ou de la file a échoué. Actualisez pour les recharger. Ne prenez pas une nouvelle décision.',
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
