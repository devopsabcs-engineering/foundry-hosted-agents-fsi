export const LANGUAGES = ['en-CA', 'fr-CA'];
export const DEFAULT_LANGUAGE = 'en-CA';

export const STRINGS = {
  'en-CA': {
    sidebar: {
      brand: 'Foundry',
      brandSub: 'QUOTE WORKSPACE',
      newQuote: 'New quote',
      thisSession: 'THIS SESSION',
      conversationsLabel: 'Conversations',
      deleteConversation: 'Delete conversation',
      notSignedIn: 'Not signed in',
      signOut: 'Sign out',
    },
    topbar: {
      overline: 'DESJARDINS / QUOTE PREPARATION',
      title: 'Quote preparation',
      pilotBadge: '{env} pilot',
      switchToFrench: 'Switch to French',
      switchToEnglish: 'Switch to English',
    },
    gate: {
      agentOverline: 'QUOTE PREPARATION AGENT',
      newQuoteHeading: 'A new quote.',
      needsAccessHeading: 'Quotes start with access.',
      verifying: 'Verifying pilot access...',
      ready: 'Ready',
      restricted: 'Internal pilot / authorized members only',
      signIn: 'Sign in with Microsoft',
    },
    composer: {
      placeholder: 'Describe the quote request or ask a follow-up...',
      messageAriaLabel: 'Quote message',
      stopResponse: 'Stop response',
      sendMessage: 'Send message',
      demoQueriesSummary: 'Synthetic demo queries',
    },
    message: {
      you: 'YOU',
      agent: 'QUOTE AGENT',
      preparingQuote: 'Preparing quote',
      copyAnswer: 'Copy answer',
      copied: 'Copied',
      conversationLabel: 'Conversation',
    },
    errors: {
      signInNeedsAttention: 'Your sign-in needs attention. Sign out and sign in again.',
      responseStopped: 'Response stopped.',
      requestFailed: 'Request failed ({status}).',
      configUnavailable: 'Configuration is unavailable.',
      workspaceLoadFailed: 'The quote workspace could not load. Refresh to try again.',
    },
    disclaimer: {
      text: 'Synthetic training data only. Not an insurance quote. Verify calculations before any decision.',
    },
  },
  'fr-CA': {
    sidebar: {
      brand: 'Foundry',
      brandSub: 'ESPACE DE TRAVAIL SOUMISSIONS',
      newQuote: 'Nouvelle soumission',
      thisSession: 'CETTE SESSION',
      conversationsLabel: 'Conversations',
      deleteConversation: 'Supprimer la conversation',
      notSignedIn: 'Non connecté',
      signOut: 'Se déconnecter',
    },
    topbar: {
      overline: 'DESJARDINS / PRÉPARATION DE SOUMISSIONS',
      title: 'Préparation de soumission',
      pilotBadge: 'pilote {env}',
      switchToFrench: 'Passer au français',
      switchToEnglish: 'Passer \u00e0 l\u2019anglais',
    },
    gate: {
      agentOverline: 'AGENT DE PRÉPARATION DE SOUMISSIONS',
      newQuoteHeading: 'Une nouvelle soumission.',
      needsAccessHeading: 'Une soumission commence par l\u2019accès.',
      verifying: 'Vérification de l\u2019accès pilote...',
      ready: 'Prêt',
      restricted: 'Pilote interne / membres autorisés seulement',
      signIn: 'Se connecter avec Microsoft',
    },
    composer: {
      placeholder: 'Décrivez la demande de soumission ou posez une question de suivi...',
      messageAriaLabel: 'Message de soumission',
      stopResponse: 'Arrêter la réponse',
      sendMessage: 'Envoyer le message',
      demoQueriesSummary: 'Requêtes de démonstration synthétiques',
    },
    message: {
      you: 'VOUS',
      agent: 'AGENT DE SOUMISSION',
      preparingQuote: 'Préparation de la soumission',
      copyAnswer: 'Copier la réponse',
      copied: 'Copié',
      conversationLabel: 'Conversation',
    },
    errors: {
      signInNeedsAttention: 'Votre connexion nécessite une attention particulière. Déconnectez-vous et reconnectez-vous.',
      responseStopped: 'Réponse arrêtée.',
      requestFailed: 'Échec de la requête ({status}).',
      configUnavailable: 'La configuration est indisponible.',
      workspaceLoadFailed: 'L\u2019espace de travail des soumissions n\u2019a pas pu être chargé. Actualisez la page pour réessayer.',
    },
    disclaimer: {
      text: 'Données d\u2019entraînement synthétiques seulement. Ceci n\u2019est pas une soumission d\u2019assurance. Vérifiez les calculs avant toute décision.',
    },
  },
};

function resolve(dictionary, key) {
  return key.split('.').reduce((node, part) => (node && typeof node === 'object' ? node[part] : undefined), dictionary);
}

function interpolate(template, vars) {
  if (typeof template !== 'string' || !vars) return template;
  return template.replace(/\{(\w+)\}/g, (match, name) => (name in vars ? String(vars[name]) : match));
}

export function translate(language, key, vars) {
  const dictionary = STRINGS[language] ?? STRINGS[DEFAULT_LANGUAGE];
  const template = resolve(dictionary, key) ?? resolve(STRINGS[DEFAULT_LANGUAGE], key);
  return interpolate(template, vars);
}
