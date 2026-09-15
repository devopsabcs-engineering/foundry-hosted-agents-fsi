// Pure helpers kept out of main.jsx so `node --test` can exercise the two
// rules that matter most: a null premium must never render as a number, and
// an API status must map to a message that tells the reviewer what to do.

export const UNPRICED = null;

/**
 * Format a persisted premium. Returns null when the case carries no amount,
 * which is legitimate for UNSUPPORTED and INCOMPLETE calculations that still
 * reached PENDING_REVIEW. Callers must render that as an explicit unpriced
 * state rather than substituting a zero.
 */
export function formatAmount(amountCents, currency) {
  if (amountCents === null || amountCents === undefined) return UNPRICED;
  if (typeof amountCents !== 'number' || !Number.isFinite(amountCents)) return UNPRICED;
  // An amount with no currency is not a figure a reviewer can approve against,
  // so it is never returned bare. `premiumView` gives it its own label.
  if (!currency || typeof currency !== 'string') return UNPRICED;
  const amount = amountCents / 100;
  try {
    // currencyDisplay 'code' avoids implying a dollar sign for a currency the
    // server chose; the code travels with the number instead.
    return new Intl.NumberFormat('en-CA', {
      style: 'currency', currency, currencyDisplay: 'code',
    }).format(amount);
  } catch {
    return `${amount.toFixed(2)} ${currency}`;
  }
}

export function formatTimestamp(value) {
  if (!value) return 'Unknown';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return String(value);
  return parsed.toLocaleString('en-CA', { dateStyle: 'medium', timeStyle: 'short' });
}

export function formatList(values) {
  return Array.isArray(values) && values.length ? values.join(', ') : 'None';
}

/** Human label for a persisted calculation status, including the absent case. */
export function calculationLabel(status) {
  return status ? status.replace(/_/g, ' ').toLowerCase() : 'not calculated';
}

/**
 * Decide how a premium renders, as data rather than markup, so the two states
 * a reviewer must never confuse can be asserted without a DOM.
 *
 * `amount`       - a qualified figure carrying its currency code.
 * `unverifiable` - an amount exists but no currency does; showing the number
 *                  alone would invite approval against an unlabelled figure.
 * `unpriced`     - no amount at all, which is legitimate for UNSUPPORTED and
 *                  INCOMPLETE calculations that still reached PENDING_REVIEW.
 */
export function premiumView(record) {
  const source = record ?? {};
  const amount = formatAmount(source.amountCents, source.currency);
  if (amount !== null) return { kind: 'amount', amount, period: source.period ?? null };
  const issues = Array.isArray(source.issues) && source.issues.length
    ? ` \u2014 ${formatList(source.issues)}` : '';
  const priced = typeof source.amountCents === 'number' && Number.isFinite(source.amountCents);
  if (priced) {
    return { kind: 'unverifiable', label: 'Amount unverifiable', reason: `no currency recorded${issues}` };
  }
  return { kind: 'unpriced', label: 'Not priced', reason: `${calculationLabel(source.calculationStatus)}${issues}` };
}

/** Error code the server sets on the one 403 that means self-approval. */
export const SELF_APPROVAL = 'SELF_APPROVAL';

export class ApiError extends Error {
  constructor(status, message, code = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
  }
}

/**
 * Distinct guidance per failure mode. 409 is a stale revision or an invalid
 * transition, 404 means the case is gone. The caller uses `refresh` to decide
 * whether to reload the case or return to the queue instead of resubmitting
 * the same decision.
 *
 * 403 covers self-approval *and* every authorization failure raised in
 * `auth.py` (wrong app, missing scope, revoked role). Only the server's
 * `SELF_APPROVAL` code may claim authorship; any other 403 surfaces the
 * server's own remediation verbatim, because telling a reviewer whose role was
 * revoked that they prepared the case hides the fix.
 */
export function decisionFailure(status, detail, code = null) {
  if (status === 403) {
    if (code === SELF_APPROVAL) {
      return {
        message: 'You prepared this case, so you cannot decide it. Another reviewer must act.',
        refresh: 'case',
      };
    }
    const reason = typeof detail === 'string' && detail
      ? detail : 'You are not authorized to decide this case.';
    return { message: reason, refresh: 'none' };
  }
  if (status === 409) {
    return {
      message: 'Another reviewer acted on this case first. It has been reloaded — review the current state before deciding again.',
      refresh: 'case',
    };
  }
  if (status === 404) {
    return { message: 'This case no longer exists. Returning to the queue.', refresh: 'queue' };
  }
  if (status === 401) {
    return { message: 'Your sign-in is no longer valid. Sign out and sign in again.', refresh: 'none' };
  }
  const fallback = typeof detail === 'string' && detail ? detail : `Request failed (${status}).`;
  return { message: fallback, refresh: 'none' };
}
