import test from 'node:test';
import assert from 'node:assert/strict';
import { createNotificationServer } from '../src/server.mjs';
const token = 'test-only-internal-token-not-a-production-secret';
async function withServer(run) {
  const server = createNotificationServer({ token });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  try { await run(`http://127.0.0.1:${server.address().port}`); }
  finally { await new Promise(resolve => server.close(resolve)); }
}
test('liveness explicitly says delivery is unfinished', () => withServer(async base => {
  const response = await fetch(`${base}/health/live`);
  assert.equal(response.status, 200);
  assert.equal((await response.json()).delivery, 'not_implemented');
}));
test('internal delivery rejects callers without its own service token', () => withServer(async base => {
  const response = await fetch(`${base}/internal/notifications`, { method: 'POST' });
  assert.equal(response.status, 401);
}));
test('authenticated internal call does not fabricate a successful delivery', () => withServer(async base => {
  const response = await fetch(`${base}/internal/notifications`, { method: 'POST', headers: { Authorization: `Bearer ${token}` } });
  assert.equal(response.status, 501);
}));
