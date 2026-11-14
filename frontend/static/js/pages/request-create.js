// BB-17 requester form. Sends only the four RequestCreate fields; owner and status are
// decided by the server. Every server or user value is rendered with textContent.
// Confirmation is shown only for a real response carrying a UUID id and SUBMITTED status.
import { apiFetch, showStatus } from '../api/client.js';

const FIELDS = {
  blood_group: { label: 'Blood group', error: '#request-blood-group-error' },
  component_type: { label: 'Component', error: '#request-component-error' },
  quantity: { label: 'Quantity', error: '#request-quantity-error' },
  urgency_level: { label: 'Urgency', error: '#request-urgency-error' },
};
const CHOICE_FIELDS = ['blood_group', 'component_type', 'urgency_level'];
const OUTPUTS = {
  id: '#out-request-id', status: '#out-request-status', blood_group: '#out-request-blood-group',
  component_type: '#out-request-component', quantity: '#out-request-quantity',
  urgency_level: '#out-request-urgency', created_at: '#out-request-created-at',
};
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const DENIED = {
  authentication_required: 'Sign in with a requester account to submit a request.',
  forbidden: 'Your account is not permitted to submit blood requests.',
  csrf_failed: 'The security check failed. Reload the page and try again.',
  policy_unresolved: 'Requests cannot be accepted until the request policy is configured.',
};

const form = document.querySelector('#request-form');
const errors = document.querySelector('#request-errors');
const confirmation = document.querySelector('#request-confirmation');
const submitButton = form.querySelector('button');
let submitting = false;

function clearErrors() {
  errors.replaceChildren();
  for (const field of Object.values(FIELDS)) document.querySelector(field.error).textContent = '';
}

function addError(name, text) {
  const item = document.createElement('li');
  if (Object.hasOwn(FIELDS, name)) {
    document.querySelector(FIELDS[name].error).textContent = text;
    item.textContent = `${FIELDS[name].label}: ${text}`;
  } else {
    item.textContent = text;
  }
  errors.appendChild(item);
}

function readInput() {
  const data = new FormData(form);
  const body = {};
  const problems = {};
  for (const name of CHOICE_FIELDS) {
    const value = data.get(name);
    if (typeof value === 'string' && value !== '') body[name] = value;
    else problems[name] = 'Choose a value.';
  }
  const raw = data.get('quantity');
  const text = typeof raw === 'string' ? raw.trim() : '';
  const number = Number(text);
  if (/^[0-9]+$/.test(text) && Number.isSafeInteger(number) && number >= 1) body.quantity = number;
  else problems.quantity = 'Enter a whole number of units, at least 1.';
  return { body, problems };
}

function isSavedRequest(payload) {
  return payload !== null && typeof payload === 'object' && typeof payload.id === 'string'
    && UUID.test(payload.id) && payload.status === 'SUBMITTED';
}

function showConfirmation(saved) {
  for (const [key, selector] of Object.entries(OUTPUTS)) {
    const value = saved[key];
    document.querySelector(selector).textContent =
      typeof value === 'string' || typeof value === 'number' ? String(value) : '';
  }
  confirmation.hidden = false;
  if (typeof confirmation.focus === 'function') confirmation.focus();
}

function showFailure(error) {
  const known = typeof error?.code === 'string' && Object.hasOwn(DENIED, error.code);
  if (known) {
    showStatus(DENIED[error.code]);
    return;
  }
  let shown = 0;
  for (const [name, messages] of Object.entries(error?.fields || {})) {
    if (!Object.hasOwn(FIELDS, name) && name !== 'non_field_errors') continue;
    const text = (Array.isArray(messages) ? messages : [messages])
      .filter(message => typeof message === 'string').join(' ');
    if (!text) continue;
    addError(name, text);
    shown += 1;
  }
  showStatus(shown ? 'Please correct the highlighted fields.' : 'Could not submit the request. Please try again.');
}

form.addEventListener('submit', async event => {
  event.preventDefault();
  if (submitting) return;
  clearErrors();
  confirmation.hidden = true;
  const { body, problems } = readInput();
  const invalid = Object.entries(problems);
  if (invalid.length) {
    for (const [name, text] of invalid) addError(name, text);
    showStatus('Please correct the highlighted fields.');
    return;
  }
  submitting = true;
  submitButton.disabled = true;
  showStatus('Submitting request…');
  try {
    const saved = await apiFetch('/api/v1/requests', { method: 'POST', body });
    if (!isSavedRequest(saved)) {
      showStatus('The request could not be confirmed. Check your requests before submitting again.');
      return;
    }
    form.reset();
    showConfirmation(saved);
    showStatus('Request submitted. Keep the request ID shown below.');
  } catch (error) {
    showFailure(error);
  } finally {
    submitting = false;
    submitButton.disabled = false;
  }
});
