import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { sampleQueries } from '../src/samples.js';

const LANGUAGES = ['en-CA', 'fr-CA'];

test('demo queries exactly match reviewed synthetic fixtures', () => {
  assert.equal(sampleQueries.length, 3);
  assert.equal(new Set(sampleQueries.map(sample => sample.id)).size, 3);
  for (const sample of sampleQueries) {
    const fixtureId = sample.id.replace('case-syn-', 'CASE-SYN-');
    const fixturePath = new URL(`../../../../data/synthetic/fixtures/${sample.id}${{
      'case-syn-002': '-sedan', 'case-syn-003': '-unsupported', 'case-syn-004': '-revision', 'case-syn-005': '-missing-plan',
    }[sample.id] || ''}.json`, import.meta.url);
    const fixture = JSON.parse(readFileSync(fixturePath, 'utf8'));
    assert.equal(fixture.fixtureId, fixtureId);
    assert.deepEqual(new Set(Object.keys(sample.title)), new Set(LANGUAGES));
    assert.deepEqual(new Set(Object.keys(sample.prompt)), new Set(LANGUAGES));
    for (const language of LANGUAGES) {
      assert.ok(sample.title[language].length > 0);
      assert.ok(sample.prompt[language].includes(fixtureId));
      assert.ok(sample.prompt[language].length < 8000);
    }
    assert.ok(sample.tools.length >= 1);
  }
});
