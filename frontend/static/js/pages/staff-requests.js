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
  return row;
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
