export const sampleQueries = [
  {
    id: 'case-syn-002',
    title: 'Sedan, basic plan (Ontario)',
    prompt: 'Prepare a quote for case CASE-SYN-002: an Ontario sedan on the basic training plan. Confirm the expected premium and submit it for employee review.',
    tools: ['get_application', 'get_rulebook', 'calculate_quote'],
  },
  {
    id: 'case-syn-004',
    title: 'Compact revised to sedan, extended plan',
    prompt: 'Case CASE-SYN-004 was approved and then revised to a sedan on the extended training plan. Recalculate the quote for draft revision 2 and confirm it still needs employee approval before delivery.',
    tools: ['get_application', 'get_rulebook', 'calculate_quote'],
  },
  {
    id: 'case-syn-005',
    title: 'Missing plan selection',
    prompt: 'Case CASE-SYN-005 has no plan selected for a compact vehicle in Ontario. Explain why the quote cannot be calculated yet and what information is missing.',
    tools: ['get_application', 'get_rulebook'],
  },
];
