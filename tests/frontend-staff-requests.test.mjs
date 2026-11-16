// BB-18: executes the real staff-requests page JS with a controlled DOM and a TEST-ONLY fake
// apiFetch. Not a browser or a real backend: proves what the page requests/sends and how it
// renders responses. Ordering, decisions and access are proven by the Django PostgreSQL tests.
import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { readFileSync } from 'node:fs';

const A = '00000000-0000-4000-8000-00000000000a';
const B = '00000000-0000-4000-8000-00000000000b';
const HOSTILE = '<img src=x onerror="globalThis.__bb18_ran__=1">';

function element(tag = 'div') {
  return {
    tag, textContent: '', value: '', disabled: false, hidden: false, children: [], events: {}, attrs: {},
    addEventListener(name, fn) { this.events[name] = fn; },
    appendChild(child) { this.children.push(child); },
    replaceChildren(...children) { this.children = children; },
    setAttribute(name, value) { this.attrs[name] = String(value); },
    set innerHTML(_) { throw new Error('Unsafe HTML sink'); },
    insertAdjacentHTML() { throw new Error('Unsafe HTML sink'); },
  };
}

function setup() {
  const nodes = new Map();
  const get = id => { if (!nodes.has(id)) nodes.set(id, element()); return nodes.get(id); };
  get('#queue-status').value = 'SUBMITTED';
  const calls = [];
  const status = [];
  const code = readFileSync('frontend/static/js/pages/staff-requests.js', 'utf8').replace(/^\s*import[^;]+;\s*/m, '');
  vm.runInNewContext(code, {
    document: { querySelector: get, createElement: tag => element(tag) },
    // TEST-ONLY fake of the shared client; each call is resolved/rejected by the test.
    apiFetch: (path, options) => new Promise((resolve, reject) => calls.push({ path, options, resolve, reject })),
    showStatus: message => status.push(message),
    URLSearchParams,
  });
  return { get, calls, status };
}

const tick = () => new Promise(resolve => setImmediate(resolve));
const item = (id, overrides = {}) => ({
  id, requester_id: '00000000-0000-4000-8000-0000000000ff', blood_group: 'O-', component_type: 'RBC',
  quantity: 2, fulfilled_quantity: 0, urgency_level: 'CRITICAL', status: 'SUBMITTED',
  rejection_reason: null, created_at: '2026-11-15T05:00:00+00:00', ...overrides,
});
const page = (results, count = results.length) => ({ count, page: 1, page_size: 20, results });
const rows = h => h.get('#queue-body').children;
const actionCell = row => row.children[7];
const findButton = (row, text) => actionCell(row).children.find(node => node.tag === 'button' && node.textContent === text);
const reasonInput = row => actionCell(row).children.find(node => node.tag === 'input');
const rowError = row => actionCell(row).children.find(node => node.attrs?.role === 'alert');

async function loaded(results, count) {
  const h = setup();
  assert.equal(h.calls.length, 1);
  h.calls[0].resolve(page(results, count));
  await tick();
  return h;
}

test('BB18 loads the SUBMITTED queue from the real collection URL with strict query keys', () => {
  const h = setup();
  assert.equal(h.calls[0].path, '/api/v1/requests?status=SUBMITTED&page=1&page_size=20');
  assert.equal(h.calls[0].options, undefined); // GET
});

test('BB18 renders rows in server order with labels and literal text', async () => {
  const h = await loaded([item(A), item(B, { urgency_level: 'ROUTINE', component_type: 'WHOLE_BLOOD', blood_group: HOSTILE })]);
  assert.equal(rows(h).length, 2);
  assert.deepEqual(rows(h)[0].children.slice(0, 7).map(c => c.textContent),
    ['Critical', 'O-', 'Red blood cells (RBC)', '2', 'Submitted', '2026-11-15T05:00:00+00:00', A]);
  assert.equal(rows(h)[1].children[0].textContent, 'Routine');
  assert.equal(rows(h)[1].children[1].textContent, HOSTILE);
  assert.equal(globalThis.__bb18_ran__, undefined);
  assert.equal(h.get('#queue-summary').textContent, '2 submitted requests.');
  assert.equal(h.get('#queue-page').textContent, 'Page 1 of 1');
});

test('BB18 approve sends exactly {status: APPROVED} by PATCH, then reloads the queue', async () => {
  const h = await loaded([item(A)]);
  findButton(rows(h)[0], 'Approve').events.click();
  const call = h.calls[1];
  assert.equal(call.path, `/api/v1/requests/${A}/status`);
  assert.equal(call.options.method, 'PATCH');
  assert.deepEqual(JSON.parse(JSON.stringify(call.options.body)), { status: 'APPROVED' });
  assert.equal(findButton(rows(h)[0], 'Approve').disabled, true);
  call.resolve(item(A, { status: 'APPROVED' }));
  await tick();
  assert.equal(h.calls.length, 3); // refreshed from the server
  assert.match(h.status.at(-1), /approved/);
  h.calls[2].resolve(page([]));
  await tick();
  assert.equal(rows(h).length, 0);
});

test('BB18 reject requires a trimmed reason of 1..240 before any request is sent', async () => {
  const h = await loaded([item(A)]);
  const row = rows(h)[0];
  for (const bad of ['', '   ', 'x'.repeat(241)]) {
    reasonInput(row).value = bad;
    findButton(row, 'Reject').events.click();
    assert.equal(h.calls.length, 1, JSON.stringify(bad));
    assert.match(rowError(row).textContent, /1 to 240/);
  }
  reasonInput(row).value = '  Missing required request information  ';
  findButton(row, 'Reject').events.click();
  assert.deepEqual(JSON.parse(JSON.stringify(h.calls[1].options.body)),
    { status: 'REJECTED', rejection_reason: 'Missing required request information' });
});

test('BB18 a 240-character reason is accepted', async () => {
  const h = await loaded([item(A)]);
  reasonInput(rows(h)[0]).value = 'r'.repeat(240);
  findButton(rows(h)[0], 'Reject').events.click();
  assert.equal(h.calls.length, 2);
});

test('BB18 one decision at a time per row', async () => {
  const h = await loaded([item(A)]);
  findButton(rows(h)[0], 'Approve').events.click();
  findButton(rows(h)[0], 'Approve').events.click();
  reasonInput(rows(h)[0]).value = 'x';
  findButton(rows(h)[0], 'Reject').events.click();
  assert.equal(h.calls.length, 2);
});

test('BB18 already-decided conflict (422) explains and reloads instead of claiming success', async () => {
  const h = await loaded([item(A)]);
  findButton(rows(h)[0], 'Approve').events.click();
  h.calls[1].reject(Object.assign(new Error('x'), { status: 422, code: 'invalid_transition', fields: {} }));
  await tick();
  assert.match(h.status.at(-1), /already been decided/);
  assert.equal(h.calls.length, 3);
});

test('BB18 server field errors show as text and controls are restored', async () => {
  const h = await loaded([item(A)]);
  const row = rows(h)[0];
  reasonInput(row).value = 'ok';
  findButton(row, 'Reject').events.click();
  h.calls[1].reject(Object.assign(new Error('x'), { status: 400, code: 'validation_error',
    fields: { rejection_reason: [HOSTILE], requester_id: ['SECRET'] } }));
  await tick();
  assert.equal(rowError(row).textContent, HOSTILE);
  assert.ok(!rowError(row).textContent.includes('SECRET'));
  assert.equal(findButton(row, 'Approve').disabled, false);
  assert.equal(findButton(row, 'Reject').disabled, false);
  assert.equal(h.calls.length, 2); // no reload claimed a save
});

test('BB18 denial and storage errors use fixed messages', async () => {
  for (const [code, expected] of [['forbidden', /not permitted/], ['authentication_required', /staff account/],
    ['csrf_failed', /security check/], ['storage_unavailable', /Nothing was changed/]]) {
    const h = await loaded([item(A)]);
    findButton(rows(h)[0], 'Approve').events.click();
    h.calls[1].reject(Object.assign(new Error(HOSTILE), { code, fields: {} }));
    await tick();
    assert.match(h.status.at(-1), expected, code);
  }
});

test('BB18 queue load denial clears the table and shows a fixed message', async () => {
  const h = setup();
  h.calls[0].reject(Object.assign(new Error(HOSTILE), { status: 403, code: 'forbidden', fields: {} }));
  await tick();
  assert.equal(rows(h).length, 0);
  assert.match(h.status.at(-1), /not permitted to review/);
});

test('BB18 malformed queue response is not rendered', async () => {
  const h = setup();
  h.calls[0].resolve({ results: 'nope' });
  await tick();
  assert.equal(rows(h).length, 0);
  assert.match(h.status.at(-1), /Could not load/);
});

test('BB18 decided rows have no controls; rejected rows show the saved reason as text', async () => {
  const h = await loaded([item(A, { status: 'REJECTED', rejection_reason: HOSTILE }), item(B, { status: 'APPROVED' })]);
  assert.equal(findButton(rows(h)[0], 'Approve'), undefined);
  assert.equal(actionCell(rows(h)[0]).children[0].textContent, `Reason: ${HOSTILE}`);
  // BB-16: an APPROVED row has no review buttons, only the issue control.
  assert.equal(findButton(rows(h)[1], 'Approve'), undefined);
  assert.equal(findButton(rows(h)[1], 'Reject'), undefined);
  assert.ok(findButton(rows(h)[1], 'Issue units'));
});

test('BB18 rows with a non-UUID id get no decision controls (no crafted paths)', async () => {
  const h = await loaded([item('../../auth/logout')]);
  assert.equal(findButton(rows(h)[0], 'Approve'), undefined);
});

test('BB18 status filter and pagination request the right pages', async () => {
  const h = await loaded([item(A)], 45);
  assert.equal(h.get('#queue-page').textContent, 'Page 1 of 3');
  assert.equal(h.get('#queue-prev').disabled, true);
  assert.equal(h.get('#queue-next').disabled, false);
  h.get('#queue-next').events.click();
  assert.equal(h.calls.at(-1).path, '/api/v1/requests?status=SUBMITTED&page=2&page_size=20');
  h.get('#queue-status').value = 'REJECTED';
  h.get('#queue-filter').events.submit({ preventDefault() {} });
  assert.equal(h.calls.at(-1).path, '/api/v1/requests?status=REJECTED&page=1&page_size=20');
  h.get('#queue-status').value = 'EVIL&page_size=1000';
  h.get('#queue-filter').events.submit({ preventDefault() {} });
  assert.equal(h.calls.at(-1).path, '/api/v1/requests?status=SUBMITTED&page=1&page_size=20');
});

test('BB18 a slow older load cannot overwrite a newer one', async () => {
  const h = setup();
  h.get('#queue-status').value = 'APPROVED';
  h.get('#queue-filter').events.submit({ preventDefault() {} });
  h.calls[1].resolve(page([item(B, { status: 'APPROVED' })]));
  await tick();
  h.calls[0].resolve(page([item(A)]));
  await tick();
  assert.equal(rows(h).length, 1);
  assert.equal(rows(h)[0].children[6].textContent, B);
});

// ---- BB-16 issue controls (TEST-ONLY fake apiFetch; real issuing needs the inventory provider) ----
const issueInput = row => actionCell(row).children.find(node => node.tag === 'textarea');
const approved = (id, overrides = {}) => item(id, { status: 'APPROVED', quantity: 3, fulfilled_quantity: 1, ...overrides });
const U1 = '00000000-0000-4000-8000-0000000000c1';
const U2 = '00000000-0000-4000-8000-0000000000c2';

test('BB16 approved rows show progress and an issue control; others do not', async () => {
  const h = await loaded([approved(A), item(B)]);
  assert.equal(actionCell(rows(h)[0]).children[0].textContent, 'Issued 1 of 3 units.');
  assert.ok(findButton(rows(h)[0], 'Issue units'));
  assert.equal(findButton(rows(h)[1], 'Issue units'), undefined);
  const full = await loaded([approved(A, { fulfilled_quantity: 3, status: 'ISSUED' })]);
  assert.equal(findButton(rows(full)[0], 'Issue units'), undefined);
});

test('BB16 issue sends exactly {unit_ids} by POST and reloads after the server confirms', async () => {
  const h = await loaded([approved(A)]);
  issueInput(rows(h)[0]).value = `${U2.toUpperCase()}\n ${U1} \n`;
  findButton(rows(h)[0], 'Issue units').events.click();
  const call = h.calls[1];
  assert.equal(call.path, `/api/v1/requests/${A}/issues`);
  assert.equal(call.options.method, 'POST');
  assert.deepEqual(JSON.parse(JSON.stringify(call.options.body)), { unit_ids: [U2, U1] });
  call.resolve({ issues: [{}, {}], fulfilled_quantity: 3, request_status: 'ISSUED' });
  await tick();
  assert.match(h.status.at(-1), /Issued 2 units/);
  assert.equal(h.calls.length, 3);
});

test('BB16 client checks unit ids, duplicates and remaining count before sending', async () => {
  const h = await loaded([approved(A)]);
  const row = rows(h)[0];
  for (const [value, message] of [['', /one or more unit IDs/], ['not-a-uuid', /one or more unit IDs/],
    [`${U1}\n${U1.toUpperCase()}`, /only once/], [`${U1}\n${U2}\n${B}`, /needs only 2 more units/]]) {
    issueInput(row).value = value;
    findButton(row, 'Issue units').events.click();
    assert.equal(h.calls.length, 1, value);
    assert.match(rowError(row).textContent, message);
  }
});

test('BB16 unavailable, unsafe and unknown units are reported honestly and nothing is claimed', async () => {
  for (const [status, code, message] of [
    [503, 'inventory_unavailable', /Inventory is unavailable right now\. Nothing was issued/],
    [422, 'unsafe_unit', /cannot be issued for this request .*Nothing was issued/],
    [404, 'not_found', /was not found\. Nothing was issued/]]) {
    const h = await loaded([approved(A)]);
    issueInput(rows(h)[0]).value = U1;
    findButton(rows(h)[0], 'Issue units').events.click();
    h.calls[1].reject(Object.assign(new Error(HOSTILE), { status, code, fields: {} }));
    await tick();
    assert.match(h.status.at(-1), message, code);
    assert.ok(!h.status.some(text => text.includes(HOSTILE)), code);
    assert.equal(findButton(rows(h)[0], 'Issue units').disabled, false, code);
    assert.equal(h.calls.length, 2, code);
  }
});

test('BB16 unit conflict and stale state reload; field errors render as text', async () => {
  for (const code of ['unit_conflict', 'invalid_transition']) {
    const h = await loaded([approved(A)]);
    issueInput(rows(h)[0]).value = U1;
    findButton(rows(h)[0], 'Issue units').events.click();
    h.calls[1].reject(Object.assign(new Error('x'), { code, fields: {} }));
    await tick();
    assert.equal(h.calls.length, 3, code);
  }
  const h = await loaded([approved(A)]);
  const row = rows(h)[0];
  issueInput(row).value = U1;
  findButton(row, 'Issue units').events.click();
  h.calls[1].reject(Object.assign(new Error('x'), { status: 400, code: 'validation_error', fields: { unit_ids: [HOSTILE] } }));
  await tick();
  assert.equal(rowError(row).textContent, HOSTILE);
});
