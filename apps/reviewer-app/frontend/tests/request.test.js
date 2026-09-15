import test from 'node:test';
import assert from 'node:assert/strict';
import { decisionRequest } from '../src/request.js';

test('every decision carries the revision the reviewer was shown', () => {
  // The revision is what makes the server reject a decision taken against a
  // page that has since gone stale. Dropping it would let a reviewer overwrite
  // a decision they never saw, so it is asserted on all three commands.
  for (const command of ['approve', 'reject', 'revise']) {
    assert.equal(decisionRequest(7, command).revision, 7, command);
    assert.equal(decisionRequest(7, command, 'MISSING_PLAN').revision, 7, command);
    assert.ok('revision' in decisionRequest(1, command), command);
  }
});

test('the revision is sent verbatim, never coerced or defaulted', () => {
  assert.equal(decisionRequest(1, 'approve').revision, 1);
  assert.strictEqual(decisionRequest(42, 'reject', 'X').revision, 42);
  // A falsy-but-real revision must survive rather than being replaced.
  assert.strictEqual(decisionRequest(0, 'approve').revision, 0);
});

test('approve never sends a reason code', () => {
  // The approve endpoint is `extra="forbid"`, so a reasonCode there is a 422.
  assert.deepEqual(decisionRequest(3, 'approve', 'MISSING_PLAN'), { revision: 3 });
  assert.deepEqual(decisionRequest(3, 'approve'), { revision: 3 });
});

test('reject and revise carry a reason code only when one was given', () => {
  assert.deepEqual(decisionRequest(3, 'reject', 'MISSING_PLAN'), { revision: 3, reasonCode: 'MISSING_PLAN' });
  assert.deepEqual(decisionRequest(3, 'revise', 'NEEDS_DETAIL'), { revision: 3, reasonCode: 'NEEDS_DETAIL' });
  // An empty prompt means no reason, not an empty string, which is a 422.
  assert.deepEqual(decisionRequest(3, 'reject', ''), { revision: 3 });
  assert.deepEqual(decisionRequest(3, 'revise', undefined), { revision: 3 });
});

test('the body carries nothing the server would refuse', () => {
  const keys = Object.keys(decisionRequest(3, 'reject', 'MISSING_PLAN')).sort();
  assert.deepEqual(keys, ['reasonCode', 'revision']);
});
