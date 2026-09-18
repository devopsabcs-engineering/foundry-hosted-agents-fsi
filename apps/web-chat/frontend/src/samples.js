export const sampleQueries = [
  {
    id: 'case-syn-001',
    title: {
      'en-CA': 'Compact, extended plan (Ontario)',
      'fr-CA': 'Compacte, r\u00e9gime \u00e9tendu (Ontario)',
    },
    prompt: {
      'en-CA': 'Prepare a quote for case CASE-SYN-001: an Ontario compact vehicle on the extended training plan. Confirm the expected premium and submit it for employee review.',
      'fr-CA': 'Pr\u00e9parez une soumission pour le dossier CASE-SYN-001 : un v\u00e9hicule compact en Ontario sur le r\u00e9gime de formation \u00e9tendu. Confirmez la prime pr\u00e9vue et soumettez-la pour r\u00e9vision par un employ\u00e9.',
    },
    tools: ['get_application', 'get_rulebook', 'calculate_quote'],
  },
  {
    id: 'case-syn-002',
    title: {
      'en-CA': 'Sedan, basic plan (Ontario)',
      'fr-CA': 'Berline, r\u00e9gime de base (Ontario)',
    },
    prompt: {
      'en-CA': 'Prepare a quote for case CASE-SYN-002: an Ontario sedan on the basic training plan. Confirm the expected premium and submit it for employee review.',
      'fr-CA': 'Pr\u00e9parez une soumission pour le dossier CASE-SYN-002 : une berline en Ontario sur le r\u00e9gime de formation de base. Confirmez la prime pr\u00e9vue et soumettez-la pour r\u00e9vision par un employ\u00e9.',
    },
    tools: ['get_application', 'get_rulebook', 'calculate_quote'],
  },
  {
    id: 'case-syn-003',
    title: {
      'en-CA': 'Unsupported vehicle type (Ontario)',
      'fr-CA': 'Type de v\u00e9hicule non pris en charge (Ontario)',
    },
    prompt: {
      'en-CA': 'Prepare a quote for case CASE-SYN-003: an unsupported vehicle type in Ontario on the basic training plan. Explain why the quote cannot be calculated and submit it for employee review.',
      'fr-CA': 'Pr\u00e9parez une soumission pour le dossier CASE-SYN-003 : un type de v\u00e9hicule non pris en charge en Ontario sur le r\u00e9gime de formation de base. Expliquez pourquoi la soumission ne peut pas \u00eatre calcul\u00e9e et soumettez-la pour r\u00e9vision par un employ\u00e9.',
    },
    tools: ['get_application', 'get_rulebook'],
  },
  {
    id: 'case-syn-004',
    title: {
      'en-CA': 'Compact revised to sedan, extended plan',
      'fr-CA': 'Compacte r\u00e9vis\u00e9e en berline, r\u00e9gime \u00e9tendu',
    },
    prompt: {
      'en-CA': 'Case CASE-SYN-004 was approved and then revised to a sedan on the extended training plan. Recalculate the quote for draft revision 2 and confirm it still needs employee approval before delivery.',
      'fr-CA': 'Le dossier CASE-SYN-004 a \u00e9t\u00e9 approuv\u00e9, puis r\u00e9vis\u00e9 pour une berline sur le r\u00e9gime de formation \u00e9tendu. Recalculez la soumission pour la r\u00e9vision de brouillon 2 et confirmez qu\u2019elle n\u00e9cessite toujours l\u2019approbation d\u2019un employ\u00e9 avant la livraison.',
    },
    tools: ['get_application', 'get_rulebook', 'calculate_quote'],
  },
  {
    id: 'case-syn-005',
    title: {
      'en-CA': 'Missing plan selection',
      'fr-CA': 'S\u00e9lection de r\u00e9gime manquante',
    },
    prompt: {
      'en-CA': 'Case CASE-SYN-005 has no plan selected for a compact vehicle in Ontario. Explain why the quote cannot be calculated yet and what information is missing.',
      'fr-CA': 'Le dossier CASE-SYN-005 n\u2019a aucun r\u00e9gime s\u00e9lectionn\u00e9 pour un v\u00e9hicule compact en Ontario. Expliquez pourquoi la soumission ne peut pas encore \u00eatre calcul\u00e9e et quelle information manque.',
    },
    tools: ['get_application', 'get_rulebook'],
  },
];
