import test from 'node:test';
import assert from 'node:assert/strict';
import { apiFetch, resetCsrfToken } from '../frontend/static/js/api/client.js';

test('client rejects external paths before sending cookies', async () => {
  await assert.rejects(apiFetch('https://example.test/steal'), /same-origin/);
});
test('client initializes CSRF and sends same-origin cookie request', async () => {
  resetCsrfToken();
  const original = globalThis.fetch; const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url, options });
    if (url.endsWith('/csrf')) return new Response(JSON.stringify({ csrf_token: 'synthetic-csrf-token' }), { status: 200 });
    return new Response(JSON.stringify({ error: { code: 'not_implemented', message: 'Feature unfinished.' } }), { status: 501 });
  };
  try {
    await assert.rejects(apiFetch('/api/v1/auth/login', { method: 'POST', body: { email: 'donor@example.test', password: 'test-only' } }), error => error.status === 501 && error.code === 'not_implemented');
    assert.equal(calls[1].options.credentials, 'same-origin');
    assert.equal(calls[1].options.headers['X-CSRFToken'], 'synthetic-csrf-token');
    assert.equal(calls[0].options.credentials, 'same-origin');
  } finally { globalThis.fetch = original; resetCsrfToken(); }
});
