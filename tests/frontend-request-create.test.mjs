// BB-17 STEP B: executes the real request-create page JS against a controlled DOM and a
// TEST-ONLY fake apiFetch. Not a browser, not a real backend: these tests prove what the
// page sends and how it renders responses, NOT that a request is saved or owned.
import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { readFileSync } from 'node:fs';

const SAVED_ID = '00000000-0000-4000-8000-0000000000aa'; // synthetic
const HOSTILE = '<img src=x onerror="globalThis.__bb17_ran__=1">';

function element() {
  return {
    textContent: '', hidden: true, disabled: false, children: [], events: {}, focused: 0,
    addEventListener(name, fn) { this.events[name] = fn; },
    appendChild(child) { this.children.push(child); },
    replaceChildren(...children) { this.children = children; },
    focus() { this.focused += 1; },
    set innerHTML(_) { throw new Error('Unsafe HTML sink'); },
    insertAdjacentHTML() { throw new Error('Unsafe HTML sink'); },
  };
}

function setup(initial = {}) {
  const nodes = new Map();
  const get = id => { if (!nodes.has(id)) nodes.set(id, element()); return nodes.get(id); };
  const form = get('#request-form');
  const button = element();
  let resets = 0;
  form.querySelector = () => button;
  form.reset = () => { resets += 1; };
  let values = { blood_group: 'O-', component_type: 'RBC', quantity: '2', urgency_level: 'URGENT', ...initial };
  const calls = [];
  const status = [];
  const document = { querySelector: get, createElement: () => element() };
  const code = readFileSync('frontend/static/js/pages/request-create.js', 'utf8')
    .replace(/^\s*import[^;]+;\s*/m, '');
  vm.runInNewContext(code, {
    document,
    // TEST-ONLY fake of the shared client; each call is resolved/rejected by the test.
    apiFetch: (path, options) => new Promise((resolve, reject) => calls.push({ path, options, resolve, reject })),
    showStatus: message => status.push(message),
    FormData: class { constructor() { this.data = { ...values }; } get(name) { return this.data[name] ?? null; } },
  });
  return {
    get, calls, status, button,
    get resets() { return resets; },
    set(next) { values = { ...values, ...next }; },
    submit: () => form.events.submit({ preventDefault() {} }),
    errorTexts: () => get('#request-errors').children.map(child => child.textContent),
  };
}

const savedResponse = overrides => ({
  id: SAVED_ID, requester_id: '00000000-0000-4000-8000-0000000000bb', blood_group: 'O-',
  component_type: 'RBC', quantity: 2, fulfilled_quantity: 0, urgency_level: 'URGENT',
  status: 'SUBMITTED', rejection_reason: null, created_at: '2026-11-15T04:00:00Z', ...overrides,
});

test('BB17 sends exactly the four fields with a numeric whole quantity to the agreed path', async () => {
  const h = setup();
  const pending = h.submit();
  assert.equal(h.calls.length, 1);
  assert.equal(h.calls[0].path, '/api/v1/requests');
  assert.equal(h.calls[0].options.method, 'POST');
  assert.deepEqual(JSON.parse(JSON.stringify(h.calls[0].options.body)),
    { blood_group: 'O-', component_type: 'RBC', urgency_level: 'URGENT', quantity: 2 });
  h.calls[0].resolve(savedResponse());
  await pending;
  assert.equal(h.get('#out-request-link').href, `/requests/${SAVED_ID}`);
});

test('BB17 never sends owner, status or other server-controlled fields even if present in the form', async () => {
  const h = setup({ requester_id: 'x', status: 'APPROVED', fulfilled_quantity: '5', role: 'STAFF' });
  const pending = h.submit();
  assert.deepEqual(Object.keys(h.calls[0].options.body).sort(),
    ['blood_group', 'component_type', 'quantity', 'urgency_level']);
  h.calls[0].resolve(savedResponse());
  await pending;
});

test('BB17 rejects missing choices and invalid quantities before calling the API', async () => {
  const cases = [
    [{ blood_group: '' }, 'Blood group'], [{ component_type: '' }, 'Component'],
    [{ urgency_level: '' }, 'Urgency'], [{ quantity: '' }, 'Quantity'], [{ quantity: '0' }, 'Quantity'],
    [{ quantity: '-1' }, 'Quantity'], [{ quantity: '1.5' }, 'Quantity'], [{ quantity: '2.0' }, 'Quantity'],
    [{ quantity: '1e2' }, 'Quantity'], [{ quantity: 'abc' }, 'Quantity'], [{ quantity: '101' }, 'Quantity'],
    [{ quantity: '99999999999999999999' }, 'Quantity'],
  ];
  for (const [input, label] of cases) {
    const h = setup(input);
    await h.submit();
    assert.equal(h.calls.length, 0, JSON.stringify(input));
    assert.ok(h.errorTexts().some(text => text.startsWith(`${label}:`)), JSON.stringify(input));
    assert.equal(h.status.at(-1), 'Please correct the highlighted fields.');
  }
});

test('BB17 accepts the approved quantity boundaries 1 and 100', async () => {
  for (const quantity of ['1', '100', ' 7 ']) {
    const h = setup({ quantity });
    const pending = h.submit();
    assert.equal(h.calls.length, 1, quantity);
    assert.equal(h.calls[0].options.body.quantity, Number(quantity.trim()));
    h.calls[0].resolve(savedResponse());
    await pending;
  }
});

test('BB17 empty form reports every field', async () => {
  const h = setup({ blood_group: '', component_type: '', quantity: '', urgency_level: '' });
  await h.submit();
  assert.equal(h.calls.length, 0);
  assert.equal(h.errorTexts().length, 4);
  assert.notEqual(h.get('#request-quantity-error').textContent, '');
});

test('BB17 prevents duplicate submission while a request is in flight and re-enables after', async () => {
  const h = setup();
  const first = h.submit();
  await h.submit();
  assert.equal(h.calls.length, 1);
  assert.equal(h.button.disabled, true);
  h.calls[0].resolve(savedResponse());
  await first;
  assert.equal(h.button.disabled, false);
});

test('BB17 shows confirmation from the server response (rendering only, fake response)', async () => {
  const h = setup();
  const pending = h.submit();
  h.calls[0].resolve(savedResponse());
  await pending;
  const confirmation = h.get('#request-confirmation');
  assert.equal(confirmation.hidden, false);
  assert.equal(confirmation.focused, 1);
  assert.equal(h.get('#out-request-id').textContent, SAVED_ID);
  assert.equal(h.get('#out-request-status').textContent, 'SUBMITTED');
  assert.equal(h.get('#out-request-quantity').textContent, '2');
  assert.equal(h.get('#out-request-created-at').textContent, '2026-11-15T04:00:00Z');
  assert.equal(h.resets, 1);
  assert.match(h.status.at(-1), /Request submitted/);
});

test('BB17 does not show a confirmation for a response without a real id or SUBMITTED status', async () => {
  for (const bad of [{}, null, savedResponse({ id: 'not-a-uuid' }), savedResponse({ id: 7 }),
    savedResponse({ status: 'APPROVED' }), savedResponse({ status: undefined })]) {
    const h = setup();
    const pending = h.submit();
    h.calls[0].resolve(bad);
    await pending;
    assert.equal(h.get('#request-confirmation').hidden, true, JSON.stringify(bad));
    assert.equal(h.resets, 0);
    assert.match(h.status.at(-1), /could not be confirmed/);
  }
});

test('BB17 renders hostile response values as literal text only', async () => {
  const h = setup();
  const pending = h.submit();
  h.calls[0].resolve(savedResponse({ blood_group: HOSTILE, created_at: { toString: () => HOSTILE } }));
  await pending;
  assert.equal(h.get('#out-request-blood-group').textContent, HOSTILE);
  assert.equal(h.get('#out-request-created-at').textContent, '');
  assert.equal(globalThis.__bb17_ran__, undefined);
});

test('BB17 shows server field errors as literal text and ignores unknown field names', async () => {
  const h = setup();
  const pending = h.submit();
  h.calls[0].reject(Object.assign(new Error('Request validation failed.'), {
    status: 400, code: 'validation_error',
    fields: { quantity: [HOSTILE], requester_id: ['SECRET'], non_field_errors: ['Unexpected input field.'] },
  }));
  await pending;
  assert.deepEqual(h.errorTexts(), [`Quantity: ${HOSTILE}`, 'Unexpected input field.']);
  assert.equal(h.get('#request-quantity-error').textContent, HOSTILE);
  assert.ok(!h.errorTexts().join(' ').includes('SECRET'));
  assert.equal(h.get('#request-confirmation').hidden, true);
  assert.equal(h.resets, 0);
});

test('BB17 maps denials to fixed messages without echoing server text', async () => {
  const cases = [
    ['authentication_required', /Sign in with a requester account/],
    ['forbidden', /not permitted to submit/],
    ['csrf_failed', /security check failed/],
    ['policy_unresolved', /request policy is configured/],
  ];
  for (const [code, expected] of cases) {
    const h = setup();
    const pending = h.submit();
    h.calls[0].reject(Object.assign(new Error(HOSTILE), { status: code === 'policy_unresolved' ? 409 : 403, code, fields: {} }));
    await pending;
    assert.match(h.status.at(-1), expected);
    assert.equal(h.get('#request-confirmation').hidden, true);
  }
});

test('BB17 network or unknown failure keeps the input and allows a retry', async () => {
  const h = setup();
  const first = h.submit();
  h.calls[0].reject(new Error('Synthetic network failure'));
  await first;
  assert.equal(h.status.at(-1), 'Could not submit the request. Please try again.');
  assert.equal(h.resets, 0);
  const second = h.submit();
  assert.equal(h.calls.length, 2);
  h.calls[1].resolve(savedResponse());
  await second;
  assert.equal(h.resets, 1);
});
