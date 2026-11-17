// Real BB19 page module with a controlled DOM/apiFetch: UI tests, not DB integration.
import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { readFileSync } from 'node:fs';

const ID = '00000000-0000-4000-8000-000000000019';
const OWNER = '00000000-0000-4000-8000-000000000020';
const OTHER = '00000000-0000-4000-8000-000000000021';
const HOSTILE = '<img src=x onerror="globalThis.trackingPwned=1">';
const item = changes => ({ id: ID, requester_id: OWNER, status: 'SUBMITTED', quantity: 3,
  fulfilled_quantity: 0, blood_group: 'A+', component_type: 'WHOLE_BLOOD', urgency_level: 'CRITICAL',
  created_at: '2026-11-15T08:00:00Z', rejection_reason: null, ...changes });
function element() {
  return { dataset: {}, value: '', textContent: '', disabled: false, hidden: false, children: [], events: {},
    addEventListener(name, callback) { this.events[name] = callback; },
    appendChild(child) { this.children.push(child); },
    replaceChildren(...children) { this.children = children; },
    set innerHTML(_) { throw new Error('Unsafe HTML sink'); },
    insertAdjacentHTML() { throw new Error('Unsafe HTML sink'); } };
}
function setup({ detail = false, requestId = ID } = {}) {
  const nodes = new Map();
  const get = selector => { if (!nodes.has(selector)) nodes.set(selector, element()); return nodes.get(selector); };
  get('#tracking-page').dataset = { view: detail ? 'detail' : 'list', requestId };
  get('#tracking-close').hidden = true;
  const calls = [], messages = [];
  const code = readFileSync('frontend/static/js/pages/request-tracking.js', 'utf8').replace(/^import[^;]+;\s*/m, '');
  vm.runInNewContext(code, { document: { querySelector: get, createElement: element }, URLSearchParams,
    apiFetch: (path, options) => new Promise((resolve, reject) => calls.push({ path, options, resolve, reject })),
    showStatus: message => messages.push(message) });
  return { get, calls, messages, click: name => get(name).events.click(),
    filter: status => { get('#tracking-status').value = status; get('#tracking-filter').events.submit({ preventDefault() {} }); } };
}
const tick = () => new Promise(resolve => setImmediate(resolve));
function identity(h, index, role = 'REQUESTER', id = OWNER) { h.calls[index].resolve({ user: { role, id } }); }
function page(results, count = results.length, number = 1) { return { results, count, page: number, page_size: 20 }; }
async function loadedList(rows = [item()], count) {
  const h = setup(); identity(h, 0); h.calls[1].resolve(page(rows, count)); await tick(); return h;
}
async function loadedDetail(value = item(), role = 'REQUESTER') {
  const h = setup({ detail: true }); identity(h, 0, role); h.calls[1].resolve(value); await tick(); return h;
}
function texts(node) { return [node.textContent, ...node.children.flatMap(texts)].join('\n'); }

test('BB19 list requests all own statuses by omission, never a client owner', () => {
  const h = setup();
  assert.equal(h.calls[0].path, '/api/v1/auth/me');
  assert.equal(h.calls[1].path, '/api/v1/requests?page=1&page_size=20');
});
test('BB19 saved statuses and partial count render as safe text with detail link', async () => {
  const h = await loadedList([item({ status: 'APPROVED', fulfilled_quantity: 1 }),
    item({ status: 'REJECTED', rejection_reason: HOSTILE })]);
  const content = texts(h.get('#tracking-records'));
  assert.match(content, /Fulfilled: 1 \/ 3 units. Remaining: 2/);
  assert.match(content, /Partially fulfilled/);
  assert.ok(content.includes(HOSTILE));
  assert.equal(globalThis.trackingPwned, undefined);
  const anchor = h.get('#tracking-records').children[0].children.at(-1);
  assert.equal(anchor.href, `/requests/${ID}`);
});
test('BB19 all five persisted lifecycle states are displayed', async () => {
  for (const status of ['SUBMITTED', 'APPROVED', 'REJECTED', 'ISSUED', 'CLOSED']) {
    const h = await loadedDetail(item({ status, fulfilled_quantity: status === 'ISSUED' || status === 'CLOSED' ? 3 : 0 }));
    assert.match(texts(h.get('#tracking-records')), new RegExp(status[0] + status.slice(1).toLowerCase()));
  }
});
test('BB19 role or owner mismatch never renders a staff queue as My requests', async () => {
  for (const [role, row] of [['STAFF', item()], ['REQUESTER', item({ requester_id: OTHER })]]) {
    const h = setup(); identity(h, 0, role); h.calls[1].resolve(page([row])); await tick();
    assert.equal(h.get('#tracking-records').children.length, 0);
  }
});
test('BB19 malformed IDs/counts/progress cannot create links or close controls', async () => {
  for (const row of [item({ id: '../../auth/logout' }), item({ fulfilled_quantity: 4 }), item({ quantity: '3' })]) {
    const h = await loadedList([row]);
    assert.equal(h.get('#tracking-records').children.length, 0);
  }
});
test('BB19 filtering and pagination use strict query and reset the page', async () => {
  const h = await loadedList([item()], 42);
  h.click('#tracking-next');
  assert.equal(h.calls.at(-1).path, '/api/v1/requests?page=2&page_size=20');
  h.filter('APPROVED');
  assert.equal(h.calls.at(-1).path, '/api/v1/requests?page=1&page_size=20&status=APPROVED');
  h.filter('EVIL&requester_id=x');
  assert.equal(h.calls.at(-1).path, '/api/v1/requests?page=1&page_size=20');
});
test('BB19 slow older responses cannot overwrite the newest filter', async () => {
  const h = setup(); h.filter('CLOSED');
  identity(h, 2); h.calls[3].resolve(page([item({ status: 'CLOSED', fulfilled_quantity: 3 })])); await tick();
  identity(h, 0); h.calls[1].resolve(page([item()])); await tick();
  assert.match(texts(h.get('#tracking-records')), /Closed/);
  assert.doesNotMatch(texts(h.get('#tracking-records')), /Awaiting staff review/);
});
test('BB19 refresh clears private data on denied or missing session', async () => {
  const h = await loadedList(); h.click('#tracking-refresh');
  assert.equal(h.get('#tracking-records').children.length, 0);
  identity(h, 2); h.calls[3].reject({ code: 'authentication_required' }); await tick();
  assert.match(h.messages.at(-1), /Sign in/);
  assert.equal(h.get('#tracking-next').disabled, true);
});
test('BB19 empty and beyond-last pages show truthful totals', async () => {
  const empty = await loadedList([]);
  assert.match(empty.messages.at(-1), /No requests/);
  const h = await loadedList([item()], 21); h.click('#tracking-next');
  identity(h, 2); h.calls[3].resolve(page([], 20, 2)); await tick();
  assert.equal(h.get('#tracking-summary').textContent, '20 matching requests.');
  assert.equal(h.get('#tracking-prev').disabled, false);
  assert.equal(h.get('#tracking-next').disabled, true);
});
test('BB19 close control only appears to the owning requester of fully issued record', async () => {
  const own = await loadedDetail(item({ status: 'ISSUED', fulfilled_quantity: 3 }));
  assert.equal(own.get('#tracking-close').hidden, false);
  for (const [row, role] of [[item({ status: 'APPROVED', fulfilled_quantity: 1 }), 'REQUESTER'],
    [item({ status: 'CLOSED', fulfilled_quantity: 3 }), 'REQUESTER'],
    [item({ status: 'ISSUED', fulfilled_quantity: 3 }), 'STAFF'],
    [item({ status: 'ISSUED', fulfilled_quantity: 1 }), 'REQUESTER']]) {
    const h = await loadedDetail(row, role);
    assert.equal(h.get('#tracking-close').hidden, true);
  }
});
test('BB19 close sends a no-body POST, prevents duplicates and refreshes persisted result', async () => {
  const h = await loadedDetail(item({ status: 'ISSUED', fulfilled_quantity: 3 }));
  h.click('#tracking-close'); h.click('#tracking-close');
  assert.equal(h.calls.length, 3);
  assert.equal(h.calls[2].path, `/api/v1/requests/${ID}/close`);
  assert.deepEqual(JSON.parse(JSON.stringify(h.calls[2].options)), { method: 'POST' });
  assert.equal(h.get('#tracking-close').disabled, true);
  assert.doesNotMatch(h.messages.at(-1), /Closed/);
  h.calls[2].resolve(item({ status: 'CLOSED', fulfilled_quantity: 3 })); await tick();
  identity(h, 3); h.calls[4].resolve(item({ status: 'CLOSED', fulfilled_quantity: 3 })); await tick();
  assert.match(texts(h.get('#tracking-records')), /Closed/);
  assert.equal(h.get('#tracking-close').hidden, true);
});
test('BB19 failed close does not claim success and re-enables controls', async () => {
  const h = await loadedDetail(item({ status: 'ISSUED', fulfilled_quantity: 3 }));
  h.click('#tracking-close'); h.calls[2].reject({ code: 'storage_unavailable' }); await tick();
  assert.match(h.messages.at(-1), /could not be closed/);
  assert.equal(h.get('#tracking-close').disabled, false);
  assert.equal(h.get('#tracking-refresh').disabled, false);
});
test('BB19 stale close state422 refreshes authoritative state', async () => {
  const h = await loadedDetail(item({ status: 'ISSUED', fulfilled_quantity: 3 }));
  h.click('#tracking-close'); h.calls[2].reject({ code: 'invalid_transition' }); await tick();
  identity(h, 3); h.calls[4].resolve(item({ status: 'CLOSED', fulfilled_quantity: 3 })); await tick();
  assert.match(h.messages.at(-1), /cannot be closed in its current state/);
  assert.match(texts(h.get('#tracking-records')), /Closed/);
});
test('BB19 detail uses the same hidden404 message and clears stale private data', async () => {
  const h = await loadedDetail(); h.click('#tracking-refresh');
  identity(h, 2); h.calls[3].reject({ code: 'not_found', message: HOSTILE }); await tick();
  assert.equal(h.messages.at(-1), 'Request not found.');
  assert.equal(h.get('#tracking-records').children.length, 0);
});
test('BB19 malformed detail path does not perform any API request', () => {
  const h = setup({ detail: true, requestId: '../../auth/logout' });
  assert.equal(h.calls.length, 0);
  assert.equal(h.messages.at(-1), 'Request not found.');
});
