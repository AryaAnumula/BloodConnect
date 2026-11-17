// BB-21 appointments page behaviour. Mock DOM and API only: not a real backend or browser.
import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const ROOT = process.env.BLOODCONNECT_REVIEW_REPO || process.cwd();
const SLOT_ID = '00000000-0000-4000-8000-000000000011';
const APPT_ID = '00000000-0000-4000-8000-000000000021';
const CAMP_ID = '00000000-0000-4000-8000-000000000001';
const FUTURE = '2099-01-01T10:00:00+00:00';
const PAST = '2001-01-01T10:00:00+00:00';

function element() {
  return {
    disabled: false, textContent: '', children: [], events: {}, values: {}, type: '',
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
  const code = readFileSync(join(ROOT, 'frontend/static/js/pages/appointments.js'), 'utf8')
    .replace(/^\s*import\s+\{[^}]+\}\s+from\s+['"][^'"]+['"];\s*/m, '');
  vm.runInNewContext(code, {
    document, apiFetch, showStatus: message => { status.value = message; }, console, Date, Number, JSON,
    FormData: class { constructor(form) { this.data = { ...form.values }; } get(name) { return this.data[name] ?? null; } },
  });
  return {
    nodes, calls, status,
    slotBody: document.querySelector('#slot-results-body'),
    apptBody: document.querySelector('#appointment-results-body'),
    form: document.querySelector('#slot-create-form'),
    submit() { return this.form.events.submit({ preventDefault() {} }); },
  };
}

const slot = (o = {}) => ({
  id: SLOT_ID, camp_id: CAMP_ID, location: 'Chennai', starts_at: FUTURE, ends_at: '2099-01-01T12:00:00+00:00',
  capacity: 5, remaining_capacity: 3, status: 'OPEN', ...o,
});
const appt = (o = {}) => ({
  id: APPT_ID, donor_id: 'd', slot_id: SLOT_ID, scheduled_time: FUTURE, status: 'CONFIRMED',
  reminder_state: 'PENDING', cancelled_at: null, ...o,
});
const page = results => ({ count: results.length, page: 1, page_size: 100, results });
const tick = () => new Promise(resolve => setImmediate(resolve));
const err = (status, message, code, fields = {}) => Object.assign(new Error(message), { status, code, fields });
const plain = value => JSON.parse(JSON.stringify(value));
const pathOf = call => new URL(call.path, 'http://synthetic.test').pathname;

async function loaded(slots, appts) {
  const h = setup();
  const s = h.calls.find(c => pathOf(c) === '/api/v1/appointment-slots');
  const a = h.calls.find(c => pathOf(c) === '/api/v1/appointments');
  s.resolve(page(slots)); a.resolve(page(appts));
  await tick();
  return h;
}

test('BB21 page loads open slots and own appointments on open', async () => {
  const h = setup();
  assert.deepEqual(h.calls.map(pathOf).sort(), ['/api/v1/appointment-slots', '/api/v1/appointments']);
  for (const c of h.calls) {
    const q = new URL(c.path, 'http://synthetic.test').searchParams;
    assert.equal(q.get('page'), '1');
    assert.equal(q.get('page_size'), '100');
  }
});

test('BB21 only open, future, non-full slots can be booked; hostile text stays literal', async () => {
  const h = await loaded([
    slot({ location: '<img src=x onerror=alert(1)>' }),
    slot({ id: 'full', remaining_capacity: 0 }),
    slot({ id: 'started', starts_at: PAST }),
    slot({ id: 'closed', status: 'CLOSED' }),
    slot({ id: 'walkin', camp_id: null, location: 'Clinic' }),
  ], []);
  const rows = h.slotBody.children;
  assert.equal(rows.length, 5);
  assert.equal(rows[0].children[0].textContent, '<img src=x onerror=alert(1)>');
  const states = rows.map(r => r.children[4].textContent);
  assert.deepEqual(states, ['Open', 'Full', 'Started', 'Closed', 'Open']);
  assert.deepEqual(rows.map(r => r.children[5].children[0].disabled), [false, true, true, true, false]);
  assert.equal(rows[4].children[0].textContent, 'Clinic (walk-in)');
});

test('BB21 booking posts only the slot id, blocks double click, then reloads real state', async () => {
  const h = await loaded([slot()], []);
  const button = h.slotBody.children[0].children[5].children[0];
  button.events.click(); button.events.click();
  const posts = h.calls.filter(c => c.options?.method === 'POST');
  assert.equal(posts.length, 1);
  assert.equal(pathOf(posts[0]), '/api/v1/appointments');
  assert.deepEqual(plain(posts[0].options.body), { slot_id: SLOT_ID });
  assert.equal(button.disabled, true);
  const before = h.calls.length;
  posts[0].resolve(appt());
  await tick();
  assert.equal(h.calls.length, before + 2);  // slots and appointments both re-fetched
  h.calls.slice(before).forEach(c => c.resolve(page([])));
  await tick();
  assert.match(h.status.value, /Appointment booked/);
  assert.match(h.status.value, /mock delivery only/);
});

test('BB21 booking refusals show the specific reason, never "booked", and refresh', async () => {
  const cases = [
    ['ineligible_donor', 409, /eligible screening/],
    ['capacity_conflict', 409, /full/],
    ['duplicate_booking', 409, /already have an active booking/],
    ['appointment_conflict', 409, /overlapping/],
    ['slot_unavailable', 409, /no longer available/],
    ['reminder_unavailable', 503, /Nothing was changed/],
  ];
  for (const [code, status, pattern] of cases) {
    const h = await loaded([slot()], []);
    const button = h.slotBody.children[0].children[5].children[0];
    button.events.click();
    const post = h.calls.find(c => c.options?.method === 'POST');
    const before = h.calls.length;
    post.reject(err(status, 'x', code));
    await tick();
    assert.match(h.status.value, pattern, code);
    assert.doesNotMatch(h.status.value, /booked/i, code);
    assert.equal(h.calls.length, before + 2, code);
  }
});

test('BB21 only own future CONFIRMED appointments offer cancel; cancel posts an empty body', async () => {
  const h = await loaded([], [
    appt(),
    appt({ id: 'c', status: 'CANCELLED', reminder_state: 'CANCELLED', cancelled_at: PAST }),
    appt({ id: 's', scheduled_time: PAST }),
  ]);
  const rows = h.apptBody.children;
  assert.deepEqual(rows.map(r => r.children[4].children.length), [1, 0, 0]);
  assert.equal(rows[1].children[3].textContent, PAST);
  const cancel = rows[0].children[4].children[0];
  cancel.events.click();
  const post = h.calls.find(c => c.options?.method === 'POST');
  assert.equal(pathOf(post), `/api/v1/appointments/${APPT_ID}/cancel`);
  assert.deepEqual(plain(post.options.body), {});
  assert.equal(cancel.disabled, true);
  const before = h.calls.length;
  post.resolve(appt({ status: 'CANCELLED' }));
  await tick();
  assert.equal(h.calls.length, before + 2);
  h.calls.slice(before).forEach(c => c.resolve(page([])));
  await tick();
  assert.equal(h.status.value, 'Appointment cancelled.');
});

test('BB21 cancel after start is reported from the server and the list refreshes', async () => {
  const h = await loaded([], [appt()]);
  h.apptBody.children[0].children[4].children[0].events.click();
  const post = h.calls.find(c => c.options?.method === 'POST');
  const before = h.calls.length;
  post.reject(err(409, 'x', 'invalid_transition'));
  await tick();
  assert.match(h.status.value, /can no longer be cancelled/);
  assert.equal(h.calls.length, before + 2);
});

test('BB21 malformed lists are not displayed', async () => {
  for (const bad of [null, { count: -1, results: [] }, page([slot({ remaining_capacity: '3' })]), page([slot({ id: 5 })])]) {
    const h = setup();
    h.calls.find(c => pathOf(c) === '/api/v1/appointment-slots').resolve(bad);
    h.calls.find(c => pathOf(c) === '/api/v1/appointments').resolve(page([]));
    await tick();
    assert.equal(h.slotBody.children.length, 0);
    assert.match(h.status.value, /unexpected slot list|Could not load slots/);
  }
  for (const bad of [page([appt({ status: 'INVENTED' })]), page([appt({ reminder_state: 'SENT' })])]) {
    const h = setup();
    h.calls.find(c => pathOf(c) === '/api/v1/appointment-slots').resolve(page([]));
    h.calls.find(c => pathOf(c) === '/api/v1/appointments').resolve(bad);
    await tick();
    assert.equal(h.apptBody.children.length, 0);
  }
});

test('BB21 non-donor accounts get a clear message instead of an error banner for appointments', async () => {
  const h = setup();
  h.calls.find(c => pathOf(c) === '/api/v1/appointment-slots').resolve(page([]));
  h.calls.find(c => pathOf(c) === '/api/v1/appointments').reject(err(403, 'no', 'permission_denied'));
  await tick();
  assert.equal(h.nodes.get('#appointment-count').textContent, 'Only donor accounts have appointments.');
});

test('BB21 slot form: invalid input never reaches the API', async () => {
  const good = { camp_id: '', location: 'Clinic', starts_at: '2099-01-01T10:00', ends_at: '2099-01-01T12:00', capacity: '3' };
  const bad = [
    { camp_id: 'not-a-uuid' }, { location: '   ' }, { location: 'x'.repeat(121) },
    { capacity: '0' }, { capacity: '1.5' }, { capacity: '9999999999' },
    { starts_at: '' }, { ends_at: '2099-01-01T09:00' }, { starts_at: 'garbage' },
  ];
  for (const change of bad) {
    const h = setup();
    const before = h.calls.length;
    h.form.values = { ...good, ...change };
    await h.submit();
    assert.equal(h.calls.length, before, JSON.stringify(change));
    assert.ok(h.status.value.length > 0);
  }
});

test('BB21 slot form: valid walk-in and camp slots post UTC times and refresh', async () => {
  for (const [camp, expected] of [['', null], [CAMP_ID, CAMP_ID]]) {
    const h = setup();
    h.form.values = { camp_id: camp, location: ' Clinic ', starts_at: '2099-01-01T10:00', ends_at: '2099-01-01T12:00', capacity: '3' };
    const done = h.submit();
    await tick();
    const post = h.calls.find(c => c.options?.method === 'POST');
    assert.equal(pathOf(post), '/api/v1/appointment-slots');
    const body = plain(post.options.body);
    assert.equal(body.camp_id, expected);
    assert.equal(body.location, 'Clinic');
    assert.equal(body.capacity, 3);
    assert.match(body.starts_at, /Z$/);
    assert.ok(Date.parse(body.starts_at) < Date.parse(body.ends_at));
    post.resolve({});
    await tick();
    h.calls.filter(c => pathOf(c) === '/api/v1/appointment-slots' && !c.options).slice(-1)[0].resolve(page([]));
    await done;
    assert.equal(h.status.value, 'Slot added.');
  }
});

test('BB21 slot create refusal (donor 403) is reported and no success is shown', async () => {
  const h = setup();
  h.form.values = { camp_id: '', location: 'Clinic', starts_at: '2099-01-01T10:00', ends_at: '2099-01-01T12:00', capacity: '3' };
  const done = h.submit();
  await tick();
  h.calls.find(c => c.options?.method === 'POST').reject(err(403, 'no', 'permission_denied'));
  await done;
  assert.match(h.status.value, /Access denied/);
});
