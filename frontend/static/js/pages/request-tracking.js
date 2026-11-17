// BB19: authoritative saved data; safe text rendering; no polling, mock totals or issue writer.
import { apiFetch, showStatus } from '../api/client.js';

const page = document.querySelector('#tracking-page');
const detail = page.dataset.view === 'detail';
const requestId = page.dataset.requestId;
const records = document.querySelector('#tracking-records');
const refresh = document.querySelector('#tracking-refresh');
const close = document.querySelector('#tracking-close');
const prev = document.querySelector('#tracking-prev');
const next = document.querySelector('#tracking-next');
const statuses = ['SUBMITTED', 'APPROVED', 'REJECTED', 'ISSUED', 'CLOSED'];
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const labels = {
  SUBMITTED: 'Submitted', APPROVED: 'Approved', REJECTED: 'Rejected', ISSUED: 'Issued', CLOSED: 'Closed',
  CRITICAL: 'Critical', URGENT: 'Urgent', ROUTINE: 'Routine', WHOLE_BLOOD: 'Whole blood',
  RBC: 'Red blood cells', PLASMA: 'Plasma', PLATELETS: 'Platelets',
};
const failures = {
  authentication_required: 'Sign in to view your requests.',
  forbidden: 'Your account is not permitted to view these requests.',
  not_found: 'Request not found.',
  csrf_failed: 'The security check failed. Reload the page and try again.',
  storage_unavailable: 'The request could not be closed right now. Please refresh before retrying.',
};
const state = { status: '', page: 1, count: 0, loadId: 0, closing: false, current: null, user: null };
const label = value => Object.hasOwn(labels, value) ? labels[value] : String(value ?? '');
function valid(item) {
  return item && typeof item === 'object' && typeof item.id === 'string' && uuid.test(item.id)
    && typeof item.requester_id === 'string' && uuid.test(item.requester_id)
    && statuses.includes(item.status) && Number.isInteger(item.quantity) && item.quantity >= 1 && item.quantity <= 100
    && Number.isInteger(item.fulfilled_quantity) && item.fulfilled_quantity >= 0 && item.fulfilled_quantity <= item.quantity;
}
function clear() {
  records.replaceChildren();
  state.current = null;
  if (close) close.hidden = true;
  if (prev) prev.disabled = true;
  if (next) next.disabled = true;
  const summary = document.querySelector('#tracking-summary');
  const pageLabel = document.querySelector('#tracking-page-label');
  if (summary) summary.textContent = '';
  if (pageLabel) pageLabel.textContent = '';
}
function message(error, fallback) {
  return typeof error?.code === 'string' && Object.hasOwn(failures, error.code) ? failures[error.code] : fallback;
}
function paragraph(parent, text) {
  const line = document.createElement('p');
  line.textContent = text;
  parent.appendChild(line);
}
function renderRecord(item, link) {
  const card = document.createElement('article');
  card.className = 'tracking-record';
  const heading = document.createElement('h2');
  heading.textContent = `${label(item.status)} · ${label(item.urgency_level)}`;
  card.appendChild(heading);
  paragraph(card, `${item.blood_group} · ${label(item.component_type)}`);
  paragraph(card, `Fulfilled: ${item.fulfilled_quantity} / ${item.quantity} units. Remaining: ${item.quantity - item.fulfilled_quantity}.`);
  if (item.status === 'APPROVED' && item.fulfilled_quantity > 0) paragraph(card, 'Partially fulfilled; awaiting the remaining units.');
  if (item.status === 'SUBMITTED') paragraph(card, 'Awaiting staff review.');
  if (item.status === 'REJECTED' && typeof item.rejection_reason === 'string') paragraph(card, `Rejection reason: ${item.rejection_reason}`);
  paragraph(card, `Submitted: ${String(item.created_at ?? '')}`);
  paragraph(card, `Request ID: ${item.id}`);
  if (link) {
    const anchor = document.createElement('a');
    anchor.href = `/requests/${item.id}`;
    anchor.textContent = 'View request status';
    card.appendChild(anchor);
  }
  return card;
}
function canClose(item, user) {
  return valid(item) && user?.role === 'REQUESTER' && user.id === item.requester_id
    && item.status === 'ISSUED' && item.fulfilled_quantity === item.quantity;
}
async function load() {
  const loadId = ++state.loadId;
  clear(); // private data must not remain visible after a failed refresh/session change
  showStatus('Loading requests…');
  let path;
  if (detail) {
    if (typeof requestId !== 'string' || !uuid.test(requestId)) {
      showStatus('Request not found.');
      return;
    }
    path = `/api/v1/requests/${requestId}`;
  } else {
    const query = new URLSearchParams({ page: String(state.page), page_size: '20' });
    if (state.status) query.set('status', state.status);
    path = `/api/v1/requests?${query}`;
  }
  try {
    const [identity, data] = await Promise.all([apiFetch('/api/v1/auth/me'), apiFetch(path)]);
    if (loadId !== state.loadId) return;
    const user = identity;
    if (!user || (!detail && user.role !== 'REQUESTER')) {
      throw Object.assign(new Error('Wrong account.'), { code: 'forbidden' });
    }
    state.user = user;
    if (detail) {
      if (!valid(data) || data.id !== requestId || (user.role !== 'STAFF' && data.requester_id !== user.id)) throw new Error('Unexpected detail.');
      state.current = data;
      records.replaceChildren(renderRecord(data, false));
      close.hidden = !canClose(data, user);
      close.disabled = state.closing;
    } else {
      if (!data || !Array.isArray(data.results) || !Number.isInteger(data.count) || data.count < 0
          || data.page !== state.page || data.page_size !== 20
          || !data.results.every(item => valid(item) && item.requester_id === user.id)) throw new Error('Unexpected page.');
      state.count = data.count;
      records.replaceChildren(...data.results.map(item => renderRecord(item, true)));
      document.querySelector('#tracking-summary').textContent = `${data.count} matching request${data.count === 1 ? '' : 's'}.`;
      document.querySelector('#tracking-page-label').textContent = `Page ${state.page} of ${Math.max(1, Math.ceil(data.count / 20))}`;
      prev.disabled = state.page <= 1;
      next.disabled = state.page * 20 >= data.count;
    }
    showStatus(!detail && !data.results.length ? 'No requests to show on this page.' : 'Showing the latest saved status. Refresh to check for updates.');
  } catch (error) {
    if (loadId !== state.loadId) return;
    clear();
    showStatus(message(error, 'Could not load requests. Please refresh and try again.'));
  }
}
if (detail) {
  close.addEventListener('click', async () => {
    if (state.closing || !canClose(state.current, state.user)) return;
    state.closing = true;
    close.disabled = true;
    refresh.disabled = true;
    showStatus('Closing request…');
    try {
      const saved = await apiFetch(`/api/v1/requests/${requestId}/close`, { method: 'POST' });
      if (!valid(saved) || saved.id !== requestId || saved.status !== 'CLOSED') throw new Error('Unexpected close response.');
      await load();
    } catch (error) {
      if (error?.code === 'invalid_transition') {
        await load();
        showStatus('The request cannot be closed in its current state. Status refreshed.');
      } else {
        if (['authentication_required', 'forbidden', 'not_found'].includes(error?.code)) clear();
        showStatus(message(error, 'Could not confirm closure. Refresh the request before retrying.'));
      }
    } finally {
      state.closing = false;
      refresh.disabled = false;
      close.disabled = false;
    }
  });
} else {
  document.querySelector('#tracking-filter').addEventListener('submit', event => {
    event.preventDefault();
    const value = document.querySelector('#tracking-status').value;
    state.status = statuses.includes(value) ? value : '';
    state.page = 1;
    load();
  });
  prev.addEventListener('click', () => { if (state.page > 1) { state.page -= 1; load(); } });
  next.addEventListener('click', () => { if (state.page * 20 < state.count) { state.page += 1; load(); } });
}
refresh.addEventListener('click', () => { if (!state.closing) load(); });
load();
