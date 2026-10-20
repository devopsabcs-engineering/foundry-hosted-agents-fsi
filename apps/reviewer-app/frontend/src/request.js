/**
 * Body for an approve/reject/revise POST, kept pure so the revision it carries
 * can be asserted without a DOM.
 *
 * The revision is the one the page is displaying, so a reviewer acting on a
 * stale page loses the server's compare-and-swap instead of silently
 * overwriting a decision they never saw. Approve rejects `reasonCode` with a
 * 422 (`extra="forbid"`), so it is dropped rather than sent.
 */
export function decisionRequest(revision, command, reasonCode) {
  const body = { revision };
  if (command !== 'approve' && reasonCode) body.reasonCode = reasonCode;
  return body;
}

export const CASE_STATES = ['active', 'DRAFT', 'PENDING_REVIEW', 'APPROVED', 'REJECTED'];
export const CORRECTION_VALUES = {
  jurisdiction: ['ON'],
  vehicleClass: ['COMPACT', 'SEDAN'],
  plan: ['TRAINING_BASIC', 'TRAINING_EXTENDED'],
};

export function casesPath(state = 'active') {
  if (!CASE_STATES.includes(state)) throw new Error('Invalid case state');
  return `/api/cases?state=${encodeURIComponent(state)}`;
}

export function prepareRequest(revision, values) {
  const corrections = {};
  for (const [field, choices] of Object.entries(CORRECTION_VALUES)) {
    const value = values?.[field];
    if (value === '' || value == null) continue;
    if (!choices.includes(value)) throw new Error('Invalid correction');
    corrections[field] = value;
  }
  if (!Object.keys(corrections).length) throw new Error('Empty corrections');
  return { revision, corrections };
}

/** A case and its audit must always be replaced together. */
export function caseDetail(body) {
  if (!body?.case || !Array.isArray(body.auditTrail)) throw new Error('Incomplete case detail');
  return { case: body.case, auditTrail: body.auditTrail };
}

/** A failed read must not leave actionable, apparently current data on screen. */
export function unavailableDetail(detail) {
  return { case: detail.case, auditTrail: null, unavailable: true };
}

export function currentPreparation(record) {
  return record.preparation?.revision === record.revision ? record.preparation : null;
}

export function preparationRetry(record) {
  const preparation = currentPreparation(record);
  return preparation?.status === 'FAILED' || preparation?.status === 'REQUESTED';
}
