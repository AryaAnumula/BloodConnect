// BB-21, Ankitha. Donor booking page: open slots -> book -> own appointments -> cancel.
// Page access grants nothing: the server decides every action by role, eligibility and time.
import { apiFetch, showStatus } from '../api/client.js';

const slotBody = document.querySelector('#slot-results-body');
const slotCount = document.querySelector('#slot-count');
const appointmentBody = document.querySelector('#appointment-results-body');
const appointmentCount = document.querySelector('#appointment-count');
const reloadSlots = document.querySelector('#reload-slots');
const reloadAppointments = document.querySelector('#reload-appointments');
const slotForm = document.querySelector('#slot-create-form');

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const MAX_DB_INTEGER = 2147483647;
const REMINDER_STATES = ['PENDING', 'DELIVERED', 'FAILED', 'CANCELLED'];

let latestSlotRequest = 0;
let latestAppointmentRequest = 0;

const ERROR_TEXT = {
  slot_unavailable: 'This slot is no longer available (it may have started or been closed).',
  capacity_conflict: 'This slot or camp is full.',
  duplicate_booking: 'You already have an active booking for this slot.',
  appointment_conflict: 'You already have a confirmed appointment at an overlapping time.',
  ineligible_donor: 'You need a current eligible screening result before booking. Complete screening first.',
  invalid_transition: 'This appointment can no longer be cancelled (it has started).',
  policy_unresolved: 'Booking is not available until required settings are configured.',
  reminder_unavailable: 'The reminder service is unavailable. Nothing was changed. Try again later.',
  slot_conflict: 'The slot does not fit inside its camp times.',
};

function describeError(error, fallback) {
  if (error.code && ERROR_TEXT[error.code]) return ERROR_TEXT[error.code];
  if (error.status === 400 || error.status === 422) return fieldMessages(error.fields) || error.message || fallback;
  if (error.status === 403) return 'Access denied. Your account is not allowed to do this.';
  if (error.status === 404) return 'Not found.';
  if (error.status === 503) return 'The service is temporarily unavailable. Try again later.';
  return fallback;
}

function fieldMessages(fields) {
  return Object.entries(fields || {})
    .map(([name, messages]) => `${name}: ${Array.isArray(messages) ? messages.join(' ') : ''}`)
    .join(' ');
}

function addCell(row, value) {
  const cell = document.createElement('td');
  cell.textContent = String(value ?? 'Not provided');
  row.appendChild(cell);
  return cell;
}

function hasStarted(isoTime) {
  const time = Date.parse(isoTime);
  return Number.isNaN(time) || time <= Date.now();
}

function validSlot(slot) {
  return Boolean(slot) && typeof slot === 'object' && typeof slot.id === 'string' &&
    typeof slot.location === 'string' && typeof slot.starts_at === 'string' &&
    typeof slot.ends_at === 'string' && Number.isInteger(slot.remaining_capacity) &&
    typeof slot.status === 'string';
}

function validAppointment(item) {
  return Boolean(item) && typeof item === 'object' && typeof item.id === 'string' &&
    typeof item.scheduled_time === 'string' && ['CONFIRMED', 'CANCELLED'].includes(item.status) &&
    REMINDER_STATES.includes(item.reminder_state);
}

function checkPage(data, check, label) {
  if (!data || typeof data !== 'object' || !Number.isInteger(data.count) || data.count < 0 ||
      !Array.isArray(data.results) || !data.results.every(check)) {
    throw new Error(`The server returned an unexpected ${label} list.`);
  }
}

function availability(slot) {
  if (slot.status !== 'OPEN') return 'Closed';
  if (hasStarted(slot.starts_at)) return 'Started';
  if (slot.remaining_capacity < 1) return 'Full';
  return 'Open';
}

function renderSlots(data) {
  checkPage(data, validSlot, 'slot');
  slotBody.replaceChildren();
  for (const slot of data.results) {
    const row = document.createElement('tr');
    addCell(row, slot.camp_id ? slot.location : `${slot.location} (walk-in)`);
    addCell(row, slot.starts_at);
    addCell(row, slot.ends_at);
    addCell(row, slot.remaining_capacity);
    const state = availability(slot);
    addCell(row, state);
    const actionCell = addCell(row, '');
    actionCell.textContent = '';
    const book = document.createElement('button');
    book.type = 'button';
    book.textContent = 'Book';
    book.disabled = state !== 'Open';
    book.addEventListener('click', () => bookSlot(slot.id, book));
    actionCell.appendChild(book);
    slotBody.appendChild(row);
  }
  slotCount.textContent = data.count === 0 ? 'No open slots right now.'
    : `Slots: ${data.count}${data.count > data.results.length ? ` (showing ${data.results.length})` : ''}`;
}

function renderAppointments(data) {
  checkPage(data, validAppointment, 'appointment');
  appointmentBody.replaceChildren();
  for (const item of data.results) {
    const row = document.createElement('tr');
    addCell(row, item.scheduled_time);
    addCell(row, item.status);
    addCell(row, item.reminder_state);
    addCell(row, item.cancelled_at || '—');
    const actionCell = addCell(row, '');
    actionCell.textContent = '';
    if (item.status === 'CONFIRMED' && !hasStarted(item.scheduled_time)) {
      const cancel = document.createElement('button');
      cancel.type = 'button';
      cancel.textContent = 'Cancel appointment';
      cancel.addEventListener('click', () => cancelAppointment(item.id, cancel));
      actionCell.appendChild(cancel);
    }
    appointmentBody.appendChild(row);
  }
  appointmentCount.textContent = data.count === 0 ? 'You have no appointments.'
    : `Appointments: ${data.count}${data.count > data.results.length ? ` (showing ${data.results.length})` : ''}`;
}

async function loadSlots() {
  const id = ++latestSlotRequest;
  try {
    const data = await apiFetch('/api/v1/appointment-slots?page=1&page_size=100');
    if (id !== latestSlotRequest) return;
    renderSlots(data);
  } catch (error) {
    if (id !== latestSlotRequest) return;
    slotBody.replaceChildren();
    slotCount.textContent = '';
    showStatus(describeError(error, 'Could not load slots.'));
    throw error;
  }
}

async function loadAppointments() {
  const id = ++latestAppointmentRequest;
  try {
    const data = await apiFetch('/api/v1/appointments?page=1&page_size=100');
    if (id !== latestAppointmentRequest) return;
    renderAppointments(data);
  } catch (error) {
    if (id !== latestAppointmentRequest) return;
    appointmentBody.replaceChildren();
    appointmentCount.textContent = error.status === 403
      ? 'Only donor accounts have appointments.' : '';
    if (error.status !== 403) showStatus(describeError(error, 'Could not load your appointments.'));
    throw error;
  }
}

async function refreshAll(message) {
  const results = await Promise.allSettled([loadSlots(), loadAppointments()]);
  if (message && results.every(r => r.status === 'fulfilled')) showStatus(message);
}

async function bookSlot(slotId, button) {
  if (button.disabled) return;
  button.disabled = true;  // blocks double-click; the server also refuses duplicates
  showStatus('Booking…');
  try {
    await apiFetch('/api/v1/appointments', { method: 'POST', body: { slot_id: slotId } });
  } catch (error) {
    showStatus(describeError(error, 'Could not book this slot.'));
    refreshAll();  // real server state, not a guess
    return;
  }
  await refreshAll('Appointment booked. A reminder is queued (mock delivery only).');
}

async function cancelAppointment(appointmentId, button) {
  if (button.disabled) return;
  button.disabled = true;
  showStatus('Cancelling…');
  try {
    await apiFetch(`/api/v1/appointments/${appointmentId}/cancel`, { method: 'POST', body: {} });
  } catch (error) {
    showStatus(describeError(error, 'Could not cancel this appointment.'));
    refreshAll();
    return;
  }
  await refreshAll('Appointment cancelled.');
}

function toUtcIso(raw, label) {
  const text = String(raw ?? '').trim();
  if (!text) throw new Error(`${label} is required.`);
  const date = new Date(text);
  if (Number.isNaN(date.getTime())) throw new Error(`${label} is not a valid date and time.`);
  return date.toISOString();
}

function readSlot() {
  const formData = new FormData(slotForm);
  const campRaw = String(formData.get('camp_id') ?? '').trim();
  if (campRaw && !UUID_PATTERN.test(campRaw)) throw new Error('Camp ID must be a valid ID or empty.');
  const location = String(formData.get('location') ?? '').trim();
  if (!location) throw new Error('Location is required.');
  if (location.length > 120) throw new Error('Location must be 120 characters or fewer.');
  const capacityText = String(formData.get('capacity') ?? '').trim();
  const capacity = Number(capacityText);
  if (!/^\d+$/.test(capacityText) || capacity < 1 || capacity > MAX_DB_INTEGER) {
    throw new Error('Capacity must be a whole number of 1 or more.');
  }
  const body = {
    camp_id: campRaw || null, location,
    starts_at: toUtcIso(formData.get('starts_at'), 'Start'),
    ends_at: toUtcIso(formData.get('ends_at'), 'End'),
    capacity,
  };
  if (Date.parse(body.starts_at) >= Date.parse(body.ends_at)) throw new Error('End must be after start.');
  return body;
}

slotForm.addEventListener('submit', async event => {
  event.preventDefault();
  let body;
  try {
    body = readSlot();
  } catch (error) {
    showStatus(error.message);
    return;
  }
  showStatus('Adding slot…');
  try {
    await apiFetch('/api/v1/appointment-slots', { method: 'POST', body });
  } catch (error) {
    showStatus(describeError(error, 'Could not add the slot.'));
    return;
  }
  await loadSlots().catch(() => {});
  showStatus('Slot added.');
});

reloadSlots.addEventListener('click', () => { loadSlots().then(() => showStatus('Slots refreshed.')).catch(() => {}); });
reloadAppointments.addEventListener('click', () => { loadAppointments().then(() => showStatus('Appointments refreshed.')).catch(() => {}); });

refreshAll();
