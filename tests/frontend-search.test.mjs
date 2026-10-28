import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const js = readFileSync('frontend/static/js/pages/search.js', 'utf8');
const html = readFileSync('frontend/templates/search.html', 'utf8');

test('search page includes all agreed filters and pagination controls', () => {
  for (const value of [
    'blood_group',
    'eligibility_status',
    'page_size',
    'previous-page',
    'next-page',
    'donor-results-body',
  ]) {
    assert.ok(html.includes(value), `Missing search field or control: ${value}`);
  }

  for (const group of ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']) {
    assert.ok(html.includes(`value="${group}"`), `Missing blood group: ${group}`);
  }
});

test('search builds query parameters and uses the agreed API endpoint', () => {
  assert.ok(js.includes('new URLSearchParams()'));
  assert.ok(js.includes('/api/v1/donors?'));
  assert.ok(js.includes("params.set('page'"));
  assert.ok(js.includes("params.set('page_size'"));
  assert.ok(js.includes('location.length > 120'));
});

test('donor results are rendered safely without HTML injection sinks', () => {
  assert.ok(js.includes('document.createElement'));
  assert.ok(js.includes('cell.textContent'));
  assert.ok(js.includes('resultsBody.replaceChildren()'));
  assert.doesNotMatch(js, /\.innerHTML\s*=/);
  assert.doesNotMatch(js, /\.insertAdjacentHTML\s*\(/);
});

test('search validates the response and handles expected API errors', () => {
  for (const expected of [
    'data.count',
    'data.page',
    'data.page_size',
    'data.results',
    'error.status === 400',
    'error.status === 403',
    'error.status === 501',
    'error.status === 503',
  ]) {
    assert.ok(js.includes(expected), `Missing response check: ${expected}`);
  }
});

test('search does not display donor health answers or calculate eligibility', () => {
  assert.doesNotMatch(js, /health_answers|medical_history|date_of_birth/i);
  assert.doesNotMatch(js, /calculateEligibility|calculate_eligibility/);
});
