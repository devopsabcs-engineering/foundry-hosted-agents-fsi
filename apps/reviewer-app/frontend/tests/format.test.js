import test from 'node:test';
import assert from 'node:assert/strict';
import {
  SELF_APPROVAL, calculationLabel, decisionFailure, formatAmount, formatList,
  formatTimestamp, premiumView,
} from '../src/format.js';

test('a missing amount never becomes a number', () => {
  // UNSUPPORTED and INCOMPLETE cases reach PENDING_REVIEW with no amount.
  assert.equal(formatAmount(null, 'CAD'), null);
  assert.equal(formatAmount(undefined, 'CAD'), null);
  assert.equal(formatAmount(Number.NaN, 'CAD'), null);
  assert.notEqual(formatAmount(0, 'CAD'), null);
  // Language never changes whether an amount qualifies.
  assert.equal(formatAmount(null, 'CAD', 'fr-CA'), null);
  assert.equal(formatAmount(undefined, 'CAD', 'fr-CA'), null);
});

test('amounts are formatted from cents with the stored currency, not a hardcoded sign', () => {
  const cad = formatAmount(142500, 'CAD');
  assert.ok(cad.includes('1,425.00'), cad);
  assert.ok(cad.includes('CAD'), cad);
  assert.ok(!cad.includes('$'), cad);
  assert.equal(formatAmount(142500, 'CAD', 'en-CA'), cad);
  assert.ok(formatAmount(142500, 'USD').includes('USD'));
  assert.equal(formatAmount(142500, 'not-a-currency'), '1425.00 not-a-currency');

  // fr-CA formats the same amount with French-Canadian digit grouping, not
  // translated words -- the currency code itself is language-independent.
  const cadFr = formatAmount(142500, 'CAD', 'fr-CA');
  assert.ok(cadFr.includes('CAD'), cadFr);
  assert.ok(!cadFr.includes('$'), cadFr);
  assert.notEqual(cadFr, cad);
  assert.equal(formatAmount(142500, 'not-a-currency', 'fr-CA'), '1425.00 not-a-currency');
});

test('an amount with no currency never renders as a bare number', () => {
  // `currency` is nullable in the store and passed through nullable by app.py,
  // so an unlabelled 1425.00 in the premium column is reachable. A reviewer
  // must never approve against a figure with no unit.
  for (const missing of [null, undefined, '', 0]) {
    assert.equal(formatAmount(142500, missing), null, String(missing));
    assert.equal(formatAmount(142500, missing, 'fr-CA'), null, String(missing));
  }
});

test('premiumView separates a priced case from the two unverifiable states', () => {
  const priced = premiumView({ amountCents: 142500, currency: 'CAD', period: 'TRAINING_YEAR' });
  assert.equal(priced.kind, 'amount');
  assert.ok(priced.amount.includes('CAD'), priced.amount);
  assert.equal(priced.period, 'TRAINING_YEAR');

  // No amount at all: legitimate for UNSUPPORTED and INCOMPLETE calculations.
  const unpriced = premiumView({
    amountCents: null, currency: 'CAD', calculationStatus: 'UNSUPPORTED', issues: ['UNSUPPORTED_INPUT'],
  });
  assert.equal(unpriced.kind, 'unpriced');
  assert.equal(unpriced.label, 'Not priced');
  assert.match(unpriced.reason, /unsupported/);
  assert.match(unpriced.reason, /UNSUPPORTED_INPUT/);

  // An amount with no currency is a different problem and says so.
  const unverifiable = premiumView({ amountCents: 142500, currency: null });
  assert.equal(unverifiable.kind, 'unverifiable');
  assert.equal(unverifiable.label, 'Amount unverifiable');
  assert.match(unverifiable.reason, /no currency/);
  assert.ok(!unverifiable.reason.includes('1425'), unverifiable.reason);

  const labels = new Set([priced.kind, unpriced.label, unverifiable.label]);
  assert.equal(labels.size, 3);

  // Explicit 'en-CA' matches the default exactly.
  assert.equal(premiumView({ amountCents: null, currency: 'CAD' }, 'en-CA').label, 'Not priced');

  // fr-CA renders the same three states in French.
  const pricedFr = premiumView({ amountCents: 142500, currency: 'CAD', period: 'TRAINING_YEAR' }, 'fr-CA');
  assert.equal(pricedFr.kind, 'amount');
  assert.ok(pricedFr.amount.includes('CAD'), pricedFr.amount);

  const unpricedFr = premiumView({
    amountCents: null, currency: 'CAD', calculationStatus: 'UNSUPPORTED', issues: ['UNSUPPORTED_INPUT'],
  }, 'fr-CA');
  assert.equal(unpricedFr.kind, 'unpriced');
  assert.equal(unpricedFr.label, 'Non tarif\u00e9');
  assert.match(unpricedFr.reason, /unsupported/);
  assert.match(unpricedFr.reason, /UNSUPPORTED_INPUT/);

  const unverifiableFr = premiumView({ amountCents: 142500, currency: null }, 'fr-CA');
  assert.equal(unverifiableFr.kind, 'unverifiable');
  assert.equal(unverifiableFr.label, 'Montant non v\u00e9rifiable');
  assert.match(unverifiableFr.reason, /aucune devise/);
});

test('premiumView tolerates an absent record and a zero premium', () => {
  assert.equal(premiumView(undefined).kind, 'unpriced');
  assert.equal(premiumView({}).label, 'Not priced');
  assert.equal(premiumView({ amountCents: 0, currency: 'CAD' }).kind, 'amount');

  assert.equal(premiumView(undefined, 'fr-CA').kind, 'unpriced');
  assert.equal(premiumView({}, 'fr-CA').label, 'Non tarif\u00e9');
  assert.equal(premiumView({ amountCents: 0, currency: 'CAD' }, 'fr-CA').kind, 'amount');
});

test('unknown timestamps and empty lists render explicitly', () => {
  assert.equal(formatTimestamp(null), 'Unknown');
  assert.equal(formatTimestamp(null, 'en-CA'), 'Unknown');
  assert.equal(formatTimestamp('not a date'), 'not a date');
  assert.ok(formatTimestamp('2026-09-15T12:00:00+00:00').includes('2026'));
  assert.equal(formatList([]), 'None');
  assert.equal(formatList(undefined), 'None');
  assert.equal(formatList(['A', 'B']), 'A, B');
  assert.equal(calculationLabel(null), 'not calculated');
  assert.equal(calculationLabel('UNSUPPORTED'), 'unsupported');

  // fr-CA: the absent-value fallbacks translate; the raw status reformatting
  // (spaces + lowercase) is a language-independent transform of the code.
  assert.equal(formatTimestamp(null, 'fr-CA'), 'Inconnu');
  assert.equal(formatTimestamp('not a date', 'fr-CA'), 'not a date');
  assert.ok(formatTimestamp('2026-09-15T12:00:00+00:00', 'fr-CA').includes('2026'));
  assert.equal(formatList([], 'fr-CA'), 'Aucun');
  assert.equal(formatList(undefined, 'fr-CA'), 'Aucun');
  assert.equal(formatList(['A', 'B'], 'fr-CA'), 'A, B');
  assert.equal(calculationLabel(null, 'fr-CA'), 'non calcul\u00e9');
  assert.equal(calculationLabel('UNSUPPORTED', 'fr-CA'), 'unsupported');
});

test('each decision failure gets its own message and recovery', () => {
  const forbidden = decisionFailure(403, 'You prepared this case and cannot decide it.', SELF_APPROVAL);
  assert.match(forbidden.message, /cannot decide it/);
  assert.equal(forbidden.refresh, 'case');

  const conflict = decisionFailure(409, 'ignored');
  assert.match(conflict.message, /acted on this case first/);
  assert.equal(conflict.refresh, 'case');

  const missing = decisionFailure(404, 'ignored');
  assert.match(missing.message, /no longer exists/);
  assert.equal(missing.refresh, 'queue');

  const unique = new Set([forbidden.message, conflict.message, missing.message]);
  assert.equal(unique.size, 3);

  assert.equal(decisionFailure(422, 'Bad body.').message, 'Bad body.');
  assert.equal(decisionFailure(500, null).message, 'Request failed (500).');
  assert.equal(decisionFailure(500, null).refresh, 'none');

  // fr-CA: the client-authored override messages translate; a server-supplied
  // `detail` still passes through untouched regardless of language.
  const forbiddenFr = decisionFailure(403, 'ignored', SELF_APPROVAL, 'fr-CA');
  assert.match(forbiddenFr.message, /ne pouvez donc pas le d\u00e9cider/);
  assert.equal(forbiddenFr.refresh, 'case');

  const conflictFr = decisionFailure(409, 'ignored', null, 'fr-CA');
  assert.match(conflictFr.message, /agi sur ce dossier en premier/);
  assert.equal(conflictFr.refresh, 'case');

  const missingFr = decisionFailure(404, 'ignored', null, 'fr-CA');
  assert.match(missingFr.message, /n'existe plus/);
  assert.equal(missingFr.refresh, 'queue');

  assert.equal(decisionFailure(422, 'Bad body.', null, 'fr-CA').message, 'Bad body.');
  assert.equal(decisionFailure(500, null, null, 'fr-CA').message, '\u00c9chec de la demande (500).');
  assert.equal(decisionFailure(500, null, null, 'fr-CA').refresh, 'none');
});

test('only the self-approval code claims authorship; other 403s keep their remediation', () => {
  // auth.py raises 403 for an unauthorized app, a missing scope, and a revoked
  // role. Telling those reviewers they prepared the case hides the real fix.
  const revoked = 'Reviewer role is required. Contact the pilot administrator.';
  const denied = decisionFailure(403, revoked, null);
  assert.equal(denied.message, revoked);
  assert.equal(denied.refresh, 'none');
  assert.ok(!denied.message.includes('prepared'), denied.message);

  for (const detail of ['This application is not authorized.', 'Review permission is required.']) {
    assert.equal(decisionFailure(403, detail, null).message, detail);
  }

  const selfApproval = decisionFailure(403, 'ignored detail', SELF_APPROVAL);
  assert.match(selfApproval.message, /You prepared this case/);
  assert.equal(selfApproval.refresh, 'case');
  assert.notEqual(selfApproval.message, denied.message);

  // A 403 the server sent with no detail still says something actionable.
  const bare = decisionFailure(403, '', null);
  assert.match(bare.message, /not authorized/);
  assert.ok(!bare.message.includes('prepared'), bare.message);

  // An unrelated code must not be mistaken for self-approval.
  assert.equal(decisionFailure(403, revoked, 'SOMETHING_ELSE').message, revoked);

  // fr-CA: a server-supplied detail still passes through untouched; only the
  // no-detail fallback and the self-approval override translate.
  const deniedFr = decisionFailure(403, revoked, null, 'fr-CA');
  assert.equal(deniedFr.message, revoked);
  assert.equal(deniedFr.refresh, 'none');

  const selfApprovalFr = decisionFailure(403, 'ignored detail', SELF_APPROVAL, 'fr-CA');
  assert.match(selfApprovalFr.message, /Vous avez pr\u00e9par\u00e9 ce dossier/);
  assert.equal(selfApprovalFr.refresh, 'case');
  assert.notEqual(selfApprovalFr.message, deniedFr.message);

  const bareFr = decisionFailure(403, '', null, 'fr-CA');
  assert.match(bareFr.message, /n'\u00eates pas autoris/);
  assert.ok(!bareFr.message.includes('pr\u00e9par\u00e9'), bareFr.message);
});
