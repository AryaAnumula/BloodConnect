
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const templatePath = new URL(
  '../frontend/templates/eligibility.html',
  import.meta.url
);
const scriptPath = new URL(
  '../frontend/static/js/pages/eligibility.js',
  import.meta.url
);

test('eligibility page contains the donor UUID form and all result fields', async () => {
  const html = await readFile(templatePath, 'utf8');

  for (const id of [
    'eligibility-form',
    'donor-id',
    'eligibility-result',
    'result-id',
    'result-donor-id',
    'result-status',
    'result-reason-codes',
    'result-reasons',
    'result-assessed-at',
    'result-rules-version',
    'result-stale'
  ]) {
    assert.ok(html.includes(`id="${id}"`), `Missing element: ${id}`);
  }

  assert.match(html, /js\/pages\/eligibility\.js/);
  assert.match(html, /does not perform a medical assessment/i);
});

test('eligibility page validates UUIDs and safely renders API values', async () => {
  const script = await readFile(scriptPath, 'utf8');

  assert.match(script, /eligibility\/result/);
  assert.match(script, /encodeURIComponent\(donorId\)/);
  assert.match(script, /textContent/);
  assert.match(script, /501/);
  assert.match(script, /403/);
  assert.match(script, /404/);
  assert.match(script, /503/);
  assert.match(script, /is_stale/);

  assert.doesNotMatch(script, /\.innerHTML\s*=/);
  assert.doesNotMatch(script, /insertAdjacentHTML\s*\(/);
});

test('eligibility page ignores stale requests in success and error handlers', async () => {
  const script = await readFile(scriptPath, 'utf8');

  assert.match(script, /let latestRequestId = 0;/);
  assert.match(script, /const requestId = \+\+latestRequestId;/);

  const staleRequestChecks =
    script.match(/requestId !== latestRequestId/g) ?? [];

  assert.equal(
    staleRequestChecks.length,
    2,
    'Both success and error handlers must ignore stale requests'
  );
});
