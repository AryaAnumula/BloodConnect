import { apiFetch, showStatus } from '../api/client.js';

const form = document.querySelector('#eligibility-form');
const resultSection = document.querySelector('#eligibility-result');

const fields = {
  id: document.querySelector('#result-id'),
  donor_id: document.querySelector('#result-donor-id'),
  status: document.querySelector('#result-status'),
  reason_codes: document.querySelector('#result-reason-codes'),
  reasons: document.querySelector('#result-reasons'),
  assessed_at: document.querySelector('#result-assessed-at'),
  rules_version: document.querySelector('#result-rules-version'),
  is_stale: document.querySelector('#result-stale')
};

function clearResult() {
  resultSection.hidden = true;

  for (const element of Object.values(fields)) {
    element.textContent = '';
  }
}

function displayValue(value) {
  if (value === null || value === undefined || value === '') {
    return 'Not provided';
  }

  if (Array.isArray(value)) {
    return value.length ? value.map(String).join(', ') : 'None recorded';
  }

  if (typeof value === 'boolean') {
    return value ? 'Yes' : 'No';
  }

  return String(value);
}

function renderResult(result) {
  if (
    !result ||
    typeof result !== 'object' ||
    !['ELIGIBLE', 'INELIGIBLE'].includes(result.status) ||
    typeof result.is_stale !== 'boolean' ||
    !Array.isArray(result.reason_codes) ||
    !Array.isArray(result.reasons)
  ) {
    throw new Error('The server returned an unexpected eligibility result.');
  }

  for (const key of Object.keys(fields)) {
    fields[key].textContent = displayValue(result[key]);
  }

  resultSection.hidden = false;
}

form.addEventListener('submit', async event => {
  event.preventDefault();
  clearResult();

  const donorId = new FormData(form).get('donor_id').trim();

  if (
    !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(donorId)
  ) {
    showStatus('Enter a valid donor profile UUID.');
    return;
  }

  showStatus('Loading saved eligibility result…');

  try {
    const result = await apiFetch(
      `/api/v1/donors/${encodeURIComponent(donorId)}/eligibility/result`
    );

    renderResult(result);
    showStatus('Saved eligibility result loaded.');
  } catch (error) {
    if (error.status === 403) {
      showStatus('Access denied. Sign in with an account authorized to view this result.');
    } else if (error.status === 404) {
      showStatus('No saved eligibility result was found, or the donor is unavailable.');
    } else if (error.status === 409) {
      showStatus('Eligibility policy is not finalized. The result cannot be provided.');
    } else if (error.status === 501) {
      showStatus('This feature is not implemented by the backend yet. No result was loaded.');
    } else if (error.status === 503) {
      showStatus('The service is temporarily unavailable. Try again later.');
    } else {
      showStatus(error.message || 'Could not load the eligibility result.');
    }
  }
});