import { apiFetch, showStatus } from '../api/client.js';

const form = document.querySelector('#screening-form');
const resultSection = document.querySelector('#screening-result');
const out = {
  status: document.querySelector('#out-status'),
  reasons: document.querySelector('#out-reasons'),
  assessed_at: document.querySelector('#out-assessed-at'),
  rules_version: document.querySelector('#out-rules-version'),
  is_stale: document.querySelector('#out-stale')
};

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const WEIGHT = /^[0-9]+(\.[0-9]{1,2})?$/;
const DATE = /^[0-9]{4}-[0-9]{2}-[0-9]{2}$/;

let latestRequestId = 0;

function clearResult() {
  resultSection.hidden = true;
  for (const element of Object.values(out)) element.textContent = '';
}

function renderResult(result) {
  if (
    !result ||
    typeof result !== 'object' ||
    !['ELIGIBLE', 'INELIGIBLE'].includes(result.status) ||
    typeof result.is_stale !== 'boolean' ||
    !Array.isArray(result.reasons)
  ) {
    throw new Error('The server returned an unexpected screening result.');
  }
  // textContent only: server values are never inserted as HTML.
  out.status.textContent = result.status;
  out.reasons.textContent = result.reasons.length ? result.reasons.map(String).join(' ') : 'None';
  out.assessed_at.textContent = String(result.assessed_at);
  out.rules_version.textContent = String(result.rules_version);
  out.is_stale.textContent = result.is_stale ? 'Yes, please screen again' : 'No';
  resultSection.hidden = false;
}

form.addEventListener('submit', async event => {
  event.preventDefault();
  const requestId = ++latestRequestId;
  clearResult();

  const data = new FormData(form);
  const donorId = String(data.get('donor_id') || '').trim();
  const ageText = String(data.get('age_years') || '').trim();
  const weight = String(data.get('weight_kg') || '').trim();
  const lastDonation = String(data.get('last_donation_date') || '').trim();

  if (!UUID.test(donorId)) { showStatus('Enter a valid donor profile UUID.'); return; }
  if (!/^[0-9]+$/.test(ageText)) { showStatus('Enter age as a whole number.'); return; }
  if (!WEIGHT.test(weight)) { showStatus('Enter weight with up to two decimal places.'); return; }
  if (lastDonation !== '' && !DATE.test(lastDonation)) { showStatus('Enter a valid date.'); return; }

  // Server-side validation remains authoritative; these checks only avoid pointless requests.
  const body = {
    age_years: Number(ageText),
    weight_kg: weight,
    last_donation_date: lastDonation === '' ? null : lastDonation
  };

  showStatus('Checking eligibility…');
  try {
    const result = await apiFetch(
      `/api/v1/donors/${encodeURIComponent(donorId)}/eligibility`,
      { method: 'POST', body }
    );
    if (requestId !== latestRequestId) return;
    renderResult(result);
    showStatus('Screening result saved.');
  } catch (error) {
    if (requestId !== latestRequestId) return;
    if (error.status === 400) {
      showStatus('Some answers were not accepted. Check them and try again. No result was saved.');
    } else if (error.status === 403) {
      showStatus('Access denied. Sign in as this donor to screen this profile.');
    } else if (error.status === 404) {
      showStatus('That donor profile was not found.');
    } else if (error.status === 409) {
      showStatus('Screening rules are not available right now. No result was saved.');
    } else if (error.status === 503) {
      showStatus('The service is temporarily unavailable. Try again later.');
    } else {
      showStatus(error.message || 'Screening failed. No result was saved.');
    }
  }
});