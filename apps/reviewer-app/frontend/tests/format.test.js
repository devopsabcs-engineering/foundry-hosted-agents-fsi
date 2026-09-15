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
});

test('amounts are formatted from cents with the stored currency, not a hardcoded sign', () => {
  const cad = formatAmount(142500, 'CAD');
  assert.ok(cad.includes('1,425.00'), cad);
  assert.ok(cad.includes('CAD'), cad);
  assert.ok(!cad.includes('$'), cad);
  assert.ok(formatAmount(142500, 'USD').includes('USD'));
  assert.equal(formatAmount(142500, 'not-a-currency'), '1425.00 not-a-currency');
});

test('an amount with no currency never renders as a bare number', () => {
  // `currency` is nullable in the store and passed through nullable by app.py,
  // so an unlabelled 1425.00 in the premium column is reachable. A reviewer
  // must never approve against a figure with no unit.
  for (const missing of [null, undefined, '', 0]) {
    assert.equal(formatAmount(142500, missing), null, String(missing));
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
});

test('premiumView tolerates an absent record and a zero premium', () => {
  assert.equal(premiumView(undefined).kind, 'unpriced');
  assert.equal(premiumView({}).label, 'Not priced');
  assert.equal(premiumView({ amountCents: 0, currency: 'CAD' }).kind, 'amount');
});

test('unknown timestamps and empty lists render explicitly', () => {
  assert.equal(formatTimestamp(null), 'Unknown');
  assert.equal(formatTimestamp('not a date'), 'not a date');
  assert.ok(formatTimestamp('2026-09-15T12:00:00+00:00').includes('2026'));
  assert.equal(formatList([]), 'None');
  assert.equal(formatList(undefined), 'None');
  assert.equal(formatList(['A', 'B']), 'A, B');
  assert.equal(calculationLabel(null), 'not calculated');
  assert.equal(calculationLabel('UNSUPPORTED'), 'unsupported');
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
});
