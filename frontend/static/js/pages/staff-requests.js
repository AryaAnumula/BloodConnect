// BB-18 staff review queue. Shows only what GET /api/v1/requests returns (real saved data)
// and refreshes from the server after every decision; nothing is shown as saved before the
// server confirms it. All values are rendered with textContent.
import { apiFetch, showStatus } from '../api/client.js';

const PAGE_SIZE = 20;
const REASON_MAX = 240;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const STATUSES = ['SUBMITTED', 'APPROVED', 'REJECTED', 'ISSUED', 'CLOSED'];
const LABELS = {
  CRITICAL: 'Critical', URGENT: 'Urgent', ROUTINE: 'Routine',
  WHOLE_BLOOD: 'Whole blood', RBC: 'Red blood cells (RBC)', PLASMA: 'Plasma', PLATELETS: 'Platelets',
  SUBMITTED: 'Submitted', APPROVED: 'Approved', REJECTED: 'Rejected', ISSUED: 'Issued', CLOSED: 'Closed',
};
const DENIED = {
  authentication_required: 'Sign in with a staff account to review requests.',
  forbidden: 'Your account is not permitted to review blood requests.',
  csrf_failed: 'The security check failed. Reload the page and try again.',
  storage_unavailable: 'The decision could not be saved right now. Nothing was changed; please try again.',
};

const filter = document.querySelector('#queue-filter');
const statusSelect = document.querySelector('#queue-status');
const body = document.querySelector('#queue-body');
const summary = document.querySelector('#queue-summary');
const pageLabel = document.querySelector('#queue-page');
const prev = document.querySelector('#queue-prev');
const next = document.querySelector('#queue-next');
const state = { status: 'SUBMITTED', page: 1, count: 0, loadId: 0 };

const text = value => (typeof value === 'string' || typeof value === 'number' ? String(value) : '');
const label = value => (typeof value === 'string' && Object.hasOwn(LABELS, value) ? LABELS[value] : text(value));

function cell(row, value) {
  const td = document.createElement('td');
  td.textContent = value;
  row.appendChild(td);
  return td;
}

function isPage(data) {
  return data !== null && typeof data === 'object' && Array.isArray(data.results)
    && Number.isInteger(data.count) && data.count >= 0;
}

function failureMessage(error, fallback) {
  if (typeof error?.code === 'string' && Object.hasOwn(DENIED, error.code)) return DENIED[error.code];
  return fallback;
}

async function load() {
  const loadId = ++state.loadId;
  prev.disabled = true;
  next.disabled = true;
  const query = new URLSearchParams({ status: state.status, page: String(state.page), page_size: String(PAGE_SIZE) });
  try {
    const data = await apiFetch(`/api/v1/requests?${query}`);
    if (loadId !== state.loadId) return; // a newer load replaced this one
    if (!isPage(data)) throw new Error('Unexpected response.');
    render(data);
  } catch (error) {
    if (loadId !== state.loadId) return;
    body.replaceChildren();
    summary.textContent = '';
    pageLabel.textContent = '';
    showStatus(failureMessage(error, 'Could not load the request queue. Please try again.'));
  }
}

function render(data) {
  state.count = data.count;
  const pages = Math.max(1, Math.ceil(data.count / PAGE_SIZE));
  summary.textContent = `${data.count} ${label(state.status).toLowerCase()} request${data.count === 1 ? '' : 's'}.`;
  pageLabel.textContent = `Page ${state.page} of ${pages}`;
  prev.disabled = state.page <= 1;
  next.disabled = state.page >= pages;
  body.replaceChildren(...data.results.map(renderRow));
  if (!data.results.length) showStatus(data.count ? 'No requests on this page.' : 'No requests to show.');
}

function renderRow(item) {
  const row = document.createElement('tr');
  cell(row, label(item?.urgency_level));
  cell(row, text(item?.blood_group));
  cell(row, label(item?.component_type));
  cell(row, text(item?.quantity));
  cell(row, label(item?.status));
  cell(row, text(item?.created_at));
  cell(row, text(item?.id));
  const actions = cell(row, '');
  if (item?.status === 'REJECTED') {
    const reason = document.createElement('p');
    reason.textContent = `Reason: ${text(item.rejection_reason)}`;
    actions.appendChild(reason);
  }
  if (item?.status === 'SUBMITTED' && typeof item.id === 'string' && UUID.test(item.id)) {
    addDecisionControls(actions, item.id);
  }
  if (item?.status === 'APPROVED' && typeof item.id === 'string' && UUID.test(item.id)
      && Number.isInteger(item.quantity) && Number.isInteger(item.fulfilled_quantity)) {
    addIssueControls(actions, item.id, item.quantity, item.fulfilled_quantity);
  }
  return row;
}

// BB-16: issue matching units against an APPROVED request. The server (and inventory) decide
// which units are usable; nothing is shown as issued until the server confirms it.
const ISSUE_MESSAGES = {
  inventory_unavailable: 'Inventory is unavailable right now. Nothing was issued.',
  unsafe_unit: 'A selected unit cannot be issued for this request (expired, quarantined, discarded or not matching). Nothing was issued.',
  not_found: 'A selected unit was not found. Nothing was issued.',
  unit_conflict: 'A selected unit has already been issued. Nothing was issued; the queue has been refreshed.',
  oversupply: 'More units were selected than the request still needs. Nothing was issued.',
  invalid_transition: 'This request can no longer be issued. The queue has been refreshed.',
};

function addIssueControls(container, id, quantity, fulfilled) {
  const remaining = quantity - fulfilled;
  const progress = document.createElement('p');
  progress.textContent = `Issued ${fulfilled} of ${quantity} unit${quantity === 1 ? '' : 's'}.`;
  const unitsLabel = document.createElement('label');
  unitsLabel.htmlFor = `units-${id}`;
  unitsLabel.textContent = `Unit IDs to issue (one per line, up to ${remaining})`;
  const units = document.createElement('textarea');
  units.id = `units-${id}`;
  const issue = document.createElement('button');
  issue.type = 'button';
  issue.textContent = 'Issue units';
  issue.setAttribute('aria-label', `Issue units for request ${id}`);
  const error = document.createElement('p');
  error.setAttribute('role', 'alert');
  issue.addEventListener('click', () => {
    const raw = typeof units.value === 'string' ? units.value : '';
    const ids = raw.split(/[\s,]+/).filter(Boolean).map(value => value.toLowerCase());
    if (!ids.length || ids.some(value => !UUID.test(value))) {
      error.textContent = 'Enter one or more unit IDs (UUIDs), one per line.';
      return;
    }
    if (new Set(ids).size !== ids.length) {
      error.textContent = 'Each unit may be listed only once.';
      return;
    }
    if (ids.length > remaining) {
      error.textContent = `This request needs only ${remaining} more unit${remaining === 1 ? '' : 's'}.`;
      return;
    }
    issueUnits(id, ids, { issue, error });
  });
  for (const node of [progress, unitsLabel, units, issue, error]) container.appendChild(node);
}

async function issueUnits(id, ids, controls) {
  if (controls.issue.disabled) return;
  controls.error.textContent = '';
  controls.issue.disabled = true;
  showStatus('Issuing units…');
  try {
    const saved = await apiFetch(`/api/v1/requests/${id}/issues`, { method: 'POST', body: { unit_ids: ids } });
    const count = Array.isArray(saved?.issues) ? saved.issues.length : 0;
    showStatus(`Issued ${count} unit${count === 1 ? '' : 's'}. Request ${id} is now ${label(saved?.request_status).toLowerCase()} (${text(saved?.fulfilled_quantity)} issued).`);
    await load();
  } catch (error) {
    const code = typeof error?.code === 'string' ? error.code : '';
    if (code === 'unit_conflict' || code === 'invalid_transition') {
      showStatus(ISSUE_MESSAGES[code]);
      await load();
      return;
    }
    const fields = error?.fields && typeof error.fields === 'object' ? error.fields : {};
    const messages = [fields.unit_ids, fields.non_field_errors].flat().filter(message => typeof message === 'string');
    if (messages.length) controls.error.textContent = messages.join(' ');
    showStatus(Object.hasOwn(ISSUE_MESSAGES, code) ? ISSUE_MESSAGES[code]
      : failureMessage(error, messages.length ? 'Please correct the unit list.' : 'Could not issue the units. Nothing was issued.'));
    controls.issue.disabled = false;
  }
}

function addDecisionControls(container, id) {
  const approve = document.createElement('button');
  approve.type = 'button';
  approve.textContent = 'Approve';
  approve.setAttribute('aria-label', `Approve request ${id}`);
  const reasonLabel = document.createElement('label');
  reasonLabel.htmlFor = `reason-${id}`;
  reasonLabel.textContent = 'Rejection reason';
  const reason = document.createElement('input');
  reason.id = `reason-${id}`;
  reason.type = 'text';
  reason.maxLength = REASON_MAX;
  const reject = document.createElement('button');
  reject.type = 'button';
  reject.textContent = 'Reject';
  reject.setAttribute('aria-label', `Reject request ${id}`);
  const error = document.createElement('p');
  error.setAttribute('role', 'alert');
  const controls = { approve, reject, reason, error };
  approve.addEventListener('click', () => decide(id, { status: 'APPROVED' }, controls));
  reject.addEventListener('click', () => {
    const value = typeof reason.value === 'string' ? reason.value.trim() : '';
    if (!value || value.length > REASON_MAX) {
      error.textContent = `Enter a rejection reason of 1 to ${REASON_MAX} characters.`;
      return;
    }
    decide(id, { status: 'REJECTED', rejection_reason: value }, controls);
  });
  for (const node of [approve, reasonLabel, reason, reject, error]) container.appendChild(node);
}

async function decide(id, decision, controls) {
  if (controls.approve.disabled) return; // one decision at a time per row
  controls.error.textContent = '';
  controls.approve.disabled = true;
  controls.reject.disabled = true;
  showStatus('Saving decision…');
  try {
    const saved = await apiFetch(`/api/v1/requests/${id}/status`, { method: 'PATCH', body: decision });
    const done = saved?.status === decision.status && saved?.id === id;
    showStatus(done ? `Request ${id} ${label(saved.status).toLowerCase()}.` : 'Decision sent; refreshing the queue.');
    await load();
  } catch (error) {
    if (error?.code === 'invalid_transition') {
      showStatus('This request has already been decided. The queue has been refreshed.');
      await load();
      return;
    }
    const fields = error?.fields && typeof error.fields === 'object' ? error.fields : {};
    const messages = [fields.rejection_reason, fields.status, fields.non_field_errors]
      .flat().filter(message => typeof message === 'string');
    if (messages.length) controls.error.textContent = messages.join(' ');
    showStatus(failureMessage(error, messages.length ? 'Please correct the decision.' : 'Could not save the decision. Please try again.'));
    controls.approve.disabled = false;
    controls.reject.disabled = false;
  }
}

filter.addEventListener('submit', event => {
  event.preventDefault();
  const chosen = statusSelect.value;
  state.status = STATUSES.includes(chosen) ? chosen : 'SUBMITTED';
  state.page = 1;
  load();
});
prev.addEventListener('click', () => { if (state.page > 1) { state.page -= 1; load(); } });
next.addEventListener('click', () => { state.page += 1; load(); });
load();
