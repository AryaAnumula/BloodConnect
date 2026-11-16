// Real dashboard/report UI with explicit boundary doubles, not actual source reconciliation.
import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { readFileSync } from 'node:fs';

function node() {
  return { dataset: {}, value: '', textContent: '', children: [], events: {}, disabled: false,
    addEventListener(name, callback) { this.events[name] = callback; },
    replaceChildren(...children) { this.children = children; },
    set innerHTML(_) { throw new Error('Unsafe HTML sink'); } };
}
function setup(dashboard = true) {
  const nodes = new Map();
  const get = key => { if (!nodes.has(key)) nodes.set(key, node()); return nodes.get(key); };
  get('#reporting-page').dataset.view = dashboard ? 'dashboard' : 'activity';
  const calls = [], status = [];
  const code = readFileSync('frontend/static/js/pages/reporting.js', 'utf8').replace(/^import[^;]+;\s*/m, '');
  vm.runInNewContext(code, { document: { querySelector: get, createElement: node }, URLSearchParams,
    apiFetch: path => new Promise((resolve, reject) => calls.push({ path, resolve, reject })),
    showStatus: text => status.push(text) });
  return { get, calls, status, refresh: () => get('#reporting-refresh').events.click(),
    submit(from, to) { get('#reporting-from').value = from; get('#reporting-to').value = to;
      get('#reporting-form').events.submit({ preventDefault() {} }); } };
}
const tick = () => new Promise(resolve => setImmediate(resolve));
const dashboard = changes => ({ as_of: '2026-11-16T09:00:00Z', pending_requests: 2, upcoming_camps: 1,
  stock: [{ blood_group: 'A+', component_type: 'RBC', available_quantity: 3 }], ...changes });
const report = changes => ({ from: '2026-11-15', to: '2026-11-16', timezone: 'Asia/Kolkata',
  donation_event_count: 2, collected_unit_count: 4, issued_unit_count: 3, wasted_unit_count: 1,
  definitions_version: 'college-demo-events-v1', ...changes });
const output = h => h.get('#reporting-results').children.map(n => n.textContent).join('\n');

test('dashboard requests only the approved admin endpoint and renders actual totals', async () => {
  const h = setup(); assert.equal(h.calls[0].path, '/api/v1/dashboard');
  h.calls[0].resolve(dashboard()); await tick();
  assert.match(output(h), /Pending requests: 2/); assert.match(output(h), /A\+ RBC: 3/);
});
test('missing source and denied role never render fabricated zeroes', async () => {
  for (const code of ['reporting_unavailable', 'forbidden', 'authentication_required']) {
    const h = setup(); h.calls[0].reject({ code, message: '<script>bad</script>' }); await tick();
    assert.equal(output(h), ''); assert.doesNotMatch(h.status.at(-1), /<script>/);
    assert.equal(h.get('#reporting-refresh').disabled, false);
  }
});
test('dashboard empty source response is distinct from unavailable provider', async () => {
  const h = setup(); h.calls[0].resolve(dashboard({ pending_requests: 0, upcoming_camps: 0, stock: [] })); await tick();
  assert.match(output(h), /Pending requests: 0/); assert.match(output(h), /No available stock/);
});
test('dashboard invalid totals are not rendered', async () => {
  const h = setup(); h.calls[0].resolve(dashboard({ pending_requests: '2' })); await tick();
  assert.equal(output(h), ''); assert.match(h.status.at(-1), /Could not load/);
});
test('refresh clears stale private data and slower response cannot overwrite newer data', async () => {
  const h = setup(); h.refresh();
  h.calls[1].resolve(dashboard({ pending_requests: 7 })); await tick();
  h.calls[0].resolve(dashboard({ pending_requests: 2 })); await tick();
  assert.match(output(h), /Pending requests: 7/);
  h.refresh(); assert.equal(output(h), '');
  h.calls[2].reject({ code: 'forbidden' }); await tick(); assert.equal(output(h), '');
});
test('report does not fetch before valid date selection', async () => {
  const h = setup(false); assert.equal(h.calls.length, 0);
  h.submit('', ''); h.submit('2026-11-16', '2026-11-15');
  assert.equal(h.calls.length, 0); assert.match(h.status.at(-1), /Choose valid dates/);
});
test('report uses exact inclusive date parameters and distinct event/unit labels', async () => {
  const h = setup(false); h.submit('2026-11-15', '2026-11-16');
  assert.equal(h.calls[0].path, '/api/v1/reports?from=2026-11-15&to=2026-11-16');
  h.calls[0].resolve(report()); await tick();
  assert.match(output(h), /Donation events: 2/); assert.match(output(h), /Collected units: 4/);
  assert.match(output(h), /Discarded units: 1/); assert.match(h.get('#reporting-summary').textContent, /inclusive/);
});
test('report wrong date/unknown source output rejected without displaying counts', async () => {
  const h = setup(false); h.submit('2026-11-15', '2026-11-16');
  h.calls[0].resolve(report({ from: '2026-11-01' })); await tick(); assert.equal(output(h), '');
});
test('report validation errors have clear fixed feedback and restore generate control', async () => {
  const h = setup(false); h.submit('2026-11-15', '2026-11-16');
  h.calls[0].reject({ code: 'validation_error' }); await tick();
  assert.match(h.status.at(-1), /Check the date range/); assert.equal(h.get('#reporting-generate').disabled, false);
});
