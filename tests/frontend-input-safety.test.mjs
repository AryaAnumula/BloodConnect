import test from 'node:test';
import assert from 'node:assert/strict';
import { showStatus } from '../frontend/static/js/api/client.js';

test('existing status helper uses textContent, never an HTML sink', () => {
  const original = globalThis.document;
  const assigned = [];
  const target = {
    set textContent(value) { assigned.push(value); },
    set innerHTML(value) { throw new Error('Unsafe HTML sink'); },
    insertAdjacentHTML() { throw new Error('Unsafe HTML sink'); }
  };
  globalThis.document = { querySelector(selector) { assert.equal(selector, '#status'); return target; } };
  try {
    const untrusted = '<img src=x onerror="window.__bb11_script_ran__=true">';
    showStatus(untrusted);
    assert.deepEqual(assigned, [untrusted]);
  } finally {
    if (original === undefined) delete globalThis.document;
    else globalThis.document = original;
  }
});
