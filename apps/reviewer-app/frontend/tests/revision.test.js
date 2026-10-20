import test, { after, before } from 'node:test';
import assert from 'node:assert/strict';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';
import { fileURLToPath } from 'node:url';
import { randomUUID } from 'node:crypto';
import { CASE_STATES, caseDetail, casesPath, currentPreparation, preparationRetry, prepareRequest, unavailableDetail } from '../src/request.js';
import { prepareCase } from '../src/preparation.js';
import { translate } from '../src/i18n.js';

const draft = { caseId: 'case /1', state: 'DRAFT', revision: 3, amountCents: 142500, currency: 'CAD', preparation: null };
const audit = [{ sequence: 7, command: 'revise', revision: 3 }];
const snapshot = { case: draft, auditTrail: audit };
const completed = {
  case: { ...draft, state: 'PENDING_REVIEW', revision: 4, preparation: { status: 'COMPLETED', revision: 4 } },
  auditTrail: [{ sequence: 8, command: 'prepare', revision: 4 }],
};

test('queue defaults to active and supports only the five contract filters', () => {
  assert.equal(casesPath(), '/api/cases?state=active');
  for (const state of CASE_STATES) assert.equal(casesPath(state), `/api/cases?state=${state}`);
  assert.throws(() => casesPath('all'));
});

test('prepare sends the displayed revision and nonempty allowlisted corrections only', () => {
  assert.deepEqual(prepareRequest(3, { plan: 'TRAINING_EXTENDED', jurisdiction: '', vehicleClass: '' }),
    { revision: 3, corrections: { plan: 'TRAINING_EXTENDED' } });
  assert.deepEqual(prepareRequest(0, { jurisdiction: 'ON', vehicleClass: 'SEDAN', amountCents: 1 }),
    { revision: 0, corrections: { jurisdiction: 'ON', vehicleClass: 'SEDAN' } });
  for (const corrections of [{}, { plan: '' }, { plan: '{"price":1}' }, { jurisdiction: 'QC' }, { vehicleClass: 'TRUCK' }]) {
    assert.throws(() => prepareRequest(3, corrections));
  }
});

test('prior revision preparation never labels the current revision requested, failed or completed', () => {
  for (const status of ['REQUESTED', 'FAILED', 'COMPLETED']) {
    const record = { ...draft, preparation: { revision: 2, status } };
    assert.equal(currentPreparation(record), null);
    assert.equal(preparationRetry(record), false);
    record.preparation.revision = 3;
    assert.equal(currentPreparation(record).status, status);
    assert.equal(preparationRetry(record), status !== 'COMPLETED');
  }
});

test('atomic detail validation and unavailable snapshots never pair a new case with old audit', () => {
  assert.deepEqual(caseDetail(snapshot), snapshot);
  for (const invalid of [{ case: draft }, { case: draft, auditTrail: null }, { auditTrail: [] }]) {
    assert.throws(() => caseDetail(invalid));
  }
  assert.deepEqual(unavailableDetail(snapshot), { case: draft, auditTrail: null, unavailable: true });
  assert.equal(unavailableDetail({ case: completed.case }).auditTrail, null);
});

test('prepare POST uses a fresh UUID per explicit attempt and adopts the returned case and audit together', async () => {
  const calls = [];
  const api = async (path, options) => { calls.push({ path, options }); return completed; };
  for (let attempt = 0; attempt < 2; attempt++) {
    const result = await prepareCase(api, snapshot, { plan: 'TRAINING_BASIC' }, randomUUID);
    assert.equal(result.confirmed, true);
    assert.deepEqual(result.detail, completed);
  }
  assert.equal(calls.length, 2);
  assert.equal(calls[0].path, '/api/cases/case%20%2F1/prepare');
  assert.equal(calls[0].options.method, 'POST');
  assert.deepEqual(JSON.parse(calls[0].options.body), { revision: 3, corrections: { plan: 'TRAINING_BASIC' } });
  const keys = calls.map(call => call.options.headers['Idempotency-Key']);
  assert.notEqual(keys[0], keys[1]);
  for (const key of keys) assert.match(key, /^[\da-f-]{36}$/);
});

test('failed, ambiguous and lease-conflict POSTs refresh detail once, never silently succeed or automatically retry', async () => {
  for (const status of ['FAILED', 'REQUESTED']) {
    for (const code of [409, 500]) {
      const calls = [];
      const latest = { case: { ...draft, preparation: { status, revision: 3 } }, auditTrail: [{ sequence: 8 }] };
      const error = new Error(`Request failed (${code})`);
      const api = async (path, options) => {
        calls.push({ path, options });
        if (options) throw error;
        return latest;
      };
      const result = await prepareCase(api, snapshot, { plan: 'TRAINING_BASIC' }, randomUUID);
      assert.equal(result.confirmed, false);
      assert.equal(result.error, error);
      assert.deepEqual(result.detail, latest);
      assert.equal(calls.length, 2);
      assert.equal(calls[1].path, '/api/cases/case%20%2F1');
      assert.equal(calls[1].options, undefined);
    }
  }
});

test('failed refresh removes the old audit and disables the unavailable detail', async () => {
  const result = await prepareCase(async () => { throw new Error('offline'); }, snapshot, { plan: 'TRAINING_BASIC' }, randomUUID);
  assert.equal(result.confirmed, false);
  assert.equal(result.detail.unavailable, true);
  assert.equal(result.detail.auditTrail, null);
});

test('an incomplete or non-completed success response is not announced as prepared', async () => {
  for (const body of [{ case: draft }, snapshot, {
    ...completed, case: { ...completed.case, preparation: { status: 'COMPLETED', revision: 3 } },
  }]) {
    const result = await prepareCase(async (_path, options) => options ? body : snapshot, snapshot, { jurisdiction: 'ON' }, randomUUID);
    assert.equal(result.confirmed, false);
    assert.deepEqual(result.detail, snapshot);
  }
});

let server;
let components;
before(async () => {
  server = await createServer({
    root: fileURLToPath(new URL('..', import.meta.url)), configFile: false,
    optimizeDeps: { noDiscovery: true, include: [] },
    server: { middlewareMode: true, watch: null }, appType: 'custom',
  });
  components = await server.ssrLoadModule('/src/Revision.jsx');
});
after(async () => { await server?.close(); });

function render(name, language, props) {
  return renderToStaticMarkup(createElement(components[name], {
    language, t: (key, vars) => translate(language, key, vars), ...props,
  }));
}

test('bilingual draft form exposes labeled synthetic selects, optional plan, persisted corrections and preparer warning', () => {
  for (const language of ['en-CA', 'fr-CA']) {
    const html = render('Revision', language, { record: draft });
    for (const field of ['jurisdiction', 'vehicleClass', 'plan']) {
      assert.ok(html.includes(`for="correction-${field}"`));
      assert.ok(html.includes(`id="correction-${field}"`));
      assert.ok(html.includes(translate(language, `revision.${field}`)));
    }
    assert.ok(html.includes('TRAINING_BASIC'));
    assert.ok(html.includes('TRAINING_EXTENDED'));
    assert.ok(!html.includes('type="text"'));
    assert.ok(!html.includes('required=""'));
    assert.ok(html.includes(translate(language, 'revision.ownPreparer')));
    assert.ok(html.includes('type="submit" disabled=""'));
  }
});

test('requested and failed forms offer explicit retries with lease notice and saved corrections', () => {
  for (const language of ['en-CA', 'fr-CA']) {
    for (const status of ['REQUESTED', 'FAILED']) {
      const record = { ...draft, preparation: { status, revision: 3, corrections: { plan: 'TRAINING_BASIC' } } };
      const html = render('Revision', language, { record });
      assert.ok(html.includes(translate(language, 'revision.retry')));
      assert.ok(html.includes('240'));
      assert.ok(html.includes('<option value="TRAINING_BASIC" selected="">'));
      assert.ok(html.includes('type="submit">'));
      if (status === 'REQUESTED') assert.ok(html.includes('role="status"'));
      const unavailable = render('Revision', language, { record, unavailable: true });
      assert.ok(unavailable.includes('type="submit" disabled=""'));
      assert.ok(!unavailable.includes('type="button" disabled=""'));
    }
  }
});

test('prior preparation is visibly previous and never exposes a misleading pending or retry state', () => {
  for (const language of ['en-CA', 'fr-CA']) {
    const html = render('Revision', language, {
      record: { ...draft, preparation: { revision: 2, status: 'REQUESTED', corrections: { plan: 'TRAINING_EXTENDED' } } },
    });
    assert.ok(html.includes(translate(language, 'revision.previous', { revision: 2 })));
    assert.ok(!html.includes('role="status"'));
    assert.ok(!html.includes(translate(language, 'revision.retry')));
  }
});

test('audit renders legacy events and readable corrections, calculation and provenance in both languages', () => {
  for (const language of ['en-CA', 'fr-CA']) {
    assert.equal(render('AuditDetails', language, { event: { details: null } }), '');
    const html = render('AuditDetails', language, { event: {
      reasonCode: 'MISSING_PLAN', details: {
        corrections: { jurisdiction: 'ON', vehicleClass: 'SEDAN', plan: 'TRAINING_BASIC' },
        preparationId: 'prepare-123', responseId: 'resp-123',
        calculation: { status: 'CALCULATED', amountCents: 0, rulebookVersion: 'v3', ruleIds: ['R1'], issues: [] },
      },
    } });
    for (const value of ['MISSING_PLAN', 'ON', 'SEDAN', 'TRAINING_BASIC', 'prepare-123', 'resp-123', 'CALCULATED', '>0<', 'v3', 'R1']) {
      assert.ok(html.includes(value), value);
    }
    for (const key of ['responseId', 'preparationId', 'amountCents']) {
      assert.ok(html.includes(translate(language, `revision.${key}`)));
    }
  }
});
