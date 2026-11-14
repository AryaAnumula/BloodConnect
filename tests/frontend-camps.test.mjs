// BB-20 camp page behaviour. Mock DOM and API only: not a real backend or browser.
import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const ROOT = process.env.BLOODCONNECT_REVIEW_REPO || process.cwd();
const CAMP_ID = '00000000-0000-4000-8000-000000000001';

function element() {
  return {
    hidden: true, disabled: false, textContent: '', children: [], events: {}, values: {},
    addEventListener(name, fn) { this.events[name] = fn; },
    appendChild(child) { this.children.push(child); },
    replaceChildren(...children) { this.children = children; },
  };
}

function setup() {
  const nodes = new Map();
  const calls = [];
  const status = { value: '' };
  const document = {
    querySelector(id) { if (!nodes.has(id)) nodes.set(id, element()); return nodes.get(id); },
    createElement() { return element(); },
  };
  const apiFetch = (path, options) => new Promise((resolve, reject) => calls.push({ path, options, resolve, reject }));
  const code = readFileSync(join(ROOT, 'frontend/static/js/pages/camps.js'), 'utf8')
    .replace(/^\s*import\s+\{[^}]+\}\s+from\s+['"][^'"]+['"];\s*/m, '');
  vm.runInNewContext(code, {
    document, apiFetch, showStatus: message => { status.value = message; }, URLSearchParams, console,
    FormData: class { constructor(form) { this.data = { ...form.values }; } get(name) { return this.data[name] ?? null; } },
  });
  const form = id => document.querySelector(id);
  form('#camp-filter-form').values = { status: '', page_size: '20' };
  return {
    nodes, calls, status,
    filter: form('#camp-filter-form'), create: form('#camp-create-form'), update: form('#camp-update-form'),
    submit(f) { return f.events.submit({ preventDefault() {} }); },
    click(id) { form(id).events.click(); },
  };
}

const camp = (overrides = {}) => ({
  id: CAMP_ID, name: 'City Hall Camp', location: 'Chennai', starts_at: '2030-01-01T10:00:00Z',
  ends_at: '2030-01-01T16:00:00Z', capacity: 40, status: 'ACTIVE', ...overrides,
});
const page = (results, extra = {}) => ({ count: results.length, page: 1, page_size: 20, results, ...extra });
// Objects built inside vm have another Object prototype; compare plain JSON copies.
const plain = value => JSON.parse(JSON.stringify(value));
const tick = () => new Promise(resolve => setImmediate(resolve));
const err = (status, message, fields = {}) => Object.assign(new Error(message), { status, fields });
const validCreate = (extra = {}) => ({
  name: ' Camp ', location: 'Chennai', starts_at: '2030-01-01T10:00', ends_at: '2030-01-01T16:00',
  capacity: '40', ...extra,
});

test('BB20 page loads page one of the default list on open', async () => {
  const h = setup();
  assert.equal(h.calls.length, 1);
  const q = new URL(h.calls[0].path, 'http://synthetic.test').searchParams;
  assert.equal(new URL(h.calls[0].path, 'http://synthetic.test').pathname, '/api/v1/camps');
  assert.equal(q.get('page'), '1');
  assert.equal(q.get('page_size'), '20');
  assert.equal(q.get('status'), null);
  h.calls[0].resolve(page([camp()]));
  await tick();
  assert.equal(h.nodes.get('#camp-results').hidden, false);
  assert.equal(h.nodes.get('#camp-results-body').children[0].children[1].textContent, 'City Hall Camp');
  assert.equal(h.status.value, 'Camps loaded.');
});

test('BB20 renders hostile text literally and empty list clearly', async () => {
  const h = setup();
  h.calls[0].resolve(page([camp({ name: '<img src=x onerror=alert(1)>' })]));
  await tick();
  assert.equal(h.nodes.get('#camp-results-body').children[0].children[1].textContent, '<img src=x onerror=alert(1)>');
  h.submit(h.filter);
  h.calls[1].resolve(page([]));
  await tick();
  assert.equal(h.nodes.get('#camp-count').textContent, 'No camps to show.');
});

test('BB20 malformed list responses are not displayed', async () => {
  for (const bad of [{ ...page([camp()]), count: -1 }, page([camp({ status: 'INVENTED' })]), page([camp({ capacity: '5' })]), null]) {
    const h = setup();
    h.calls[0].resolve(bad);
    await tick();
    assert.equal(h.nodes.get('#camp-results').hidden, true);
    assert.notEqual(h.status.value, 'Camps loaded.');
  }
});

test('BB20 filter sends status and size; invalid filter is blocked', async () => {
  const h = setup();
  h.calls[0].resolve(page([camp()]));
  await tick();
  h.filter.values = { status: 'CANCELLED', page_size: '10' };
  h.submit(h.filter);
  const q = new URL(h.calls[1].path, 'http://synthetic.test').searchParams;
  assert.equal(q.get('status'), 'CANCELLED');
  assert.equal(q.get('page_size'), '10');
  h.calls[1].resolve(page([camp({ status: 'CANCELLED' })], { page_size: 10 }));
  await tick();
  for (const values of [{ status: 'OPEN', page_size: '20' }, { status: '', page_size: '0' }, { status: '', page_size: '101' }]) {
    h.filter.values = values;
    h.submit(h.filter);
    await tick();
  }
  assert.equal(h.calls.length, 2);
});

test('BB20 Next keeps the applied filter and newest request wins', async () => {
  const h = setup();
  h.filter.values = { status: 'ACTIVE', page_size: '10' };
  h.submit(h.filter);
  h.calls[0].resolve(page([camp({ name: 'Old' })]));
  await tick();
  h.calls[1].resolve(page([camp({ name: 'New' })], { count: 25, page_size: 10 }));
  await tick();
  assert.equal(h.nodes.get('#camp-results-body').children[0].children[1].textContent, 'New');
  h.filter.values = { status: '', page_size: '50' };
  h.click('#next-page');
  const q = new URL(h.calls[2].path, 'http://synthetic.test').searchParams;
  assert.equal(q.get('page'), '2');
  assert.equal(q.get('status'), 'ACTIVE');
  assert.equal(q.get('page_size'), '10');
});

test('BB20 list errors clear results and show a clear message', async () => {
  for (const [status, pattern] of [[403, /Access denied/], [503, /unavailable/]]) {
    const h = setup();
    h.calls[0].reject(err(status, 'x'));
    await tick();
    assert.equal(h.nodes.get('#camp-results').hidden, true);
    assert.match(h.status.value, pattern);
  }
});

test('BB20 invalid create input is blocked before any request', async () => {
  const bad = [
    validCreate({ name: '' }), validCreate({ name: 'x'.repeat(121) }), validCreate({ location: '  ' }),
    validCreate({ starts_at: '' }), validCreate({ ends_at: 'not-a-date' }), validCreate({ capacity: '0' }),
    validCreate({ capacity: '5.5' }), validCreate({ capacity: '-3' }), validCreate({ capacity: '2147483648' }),
    validCreate({ ends_at: '2030-01-01T10:00' }), validCreate({ ends_at: '2029-12-31T10:00' }),
  ];
  for (const values of bad) {
    const h = setup();
    h.create.values = values;
    await h.submit(h.create);
    assert.equal(h.calls.length, 1, JSON.stringify(values));
  }
});

test('BB20 valid create posts UTC times and an integer capacity, then reloads', async () => {
  const h = setup();
  h.calls[0].resolve(page([]));
  await tick();
  h.create.values = validCreate();
  const pending = h.submit(h.create);
  const call = h.calls[1];
  assert.equal(call.path, '/api/v1/camps');
  assert.equal(call.options.method, 'POST');
  assert.deepEqual(plain(call.options.body), {
    name: 'Camp', location: 'Chennai',
    starts_at: new Date('2030-01-01T10:00').toISOString(), ends_at: new Date('2030-01-01T16:00').toISOString(),
    capacity: 40,
  });
  call.resolve(camp());
  await pending;
  assert.equal(h.calls.length, 3);
  assert.match(h.calls[2].path, /^\/api\/v1\/camps\?/);
  h.calls[2].resolve(page([camp()]));
  await tick();
  assert.equal(h.status.value, 'Camp created.');
});

test('BB20 create errors show server messages and do not reload', async () => {
  const cases = [
    [400, 'Check the camp details.', { starts_at: ['A new camp must start in the future.'] }, /starts_at: A new camp must start/],
    [403, 'Forbidden.', {}, /Access denied/],
    [503, 'Down.', {}, /unavailable/],
  ];
  for (const [status, message, fields, pattern] of cases) {
    const h = setup();
    h.create.values = validCreate();
    const pending = h.submit(h.create);
    h.calls[1].reject(err(status, message, fields));
    await pending;
    assert.match(h.status.value, pattern);
    assert.equal(h.calls.length, 2);
  }
});

test('BB20 update sends only the changed fields with PATCH', async () => {
  const h = setup();
  h.update.values = { camp_id: CAMP_ID, name: ' Renamed ', location: '', starts_at: '', ends_at: '', capacity: '55' };
  const pending = h.submit(h.update);
  const call = h.calls[1];
  assert.equal(call.path, `/api/v1/camps/${CAMP_ID}`);
  assert.equal(call.options.method, 'PATCH');
  assert.deepEqual(plain(call.options.body), { name: 'Renamed', capacity: 55 });
  call.resolve(camp());
  await pending;
  assert.equal(h.calls.length, 3);
});

test('BB20 invalid update input is blocked before any request', async () => {
  const base = { camp_id: CAMP_ID, name: '', location: '', starts_at: '', ends_at: '', capacity: '' };
  const bad = [
    { ...base }, { ...base, camp_id: 'nope', name: 'x' }, { ...base, camp_id: '', name: 'x' },
    { ...base, capacity: '0' }, { ...base, capacity: 'abc' }, { ...base, ends_at: 'bad' },
    { ...base, starts_at: '2030-01-02T10:00', ends_at: '2030-01-01T10:00' },
  ];
  for (const values of bad) {
    const h = setup();
    h.update.values = values;
    await h.submit(h.update);
    assert.equal(h.calls.length, 1, JSON.stringify(values));
  }
});

test('BB20 update errors: cancelled camp (422), unknown camp (404), denied (403)', async () => {
  const cases = [
    [422, 'A cancelled camp cannot be changed.', /cancelled camp cannot be changed/],
    [404, 'Not found.', /Camp not found/],
    [403, 'Forbidden.', /Access denied/],
  ];
  for (const [status, message, pattern] of cases) {
    const h = setup();
    h.update.values = { camp_id: CAMP_ID, name: 'x', location: '', starts_at: '', ends_at: '', capacity: '' };
    const pending = h.submit(h.update);
    h.calls[1].reject(err(status, message));
    await pending;
    assert.match(h.status.value, pattern);
    assert.equal(h.calls.length, 2);
  }
});
