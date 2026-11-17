// ADMIN-only APIs remain authoritative. An unavailable provider never becomes a zero total.
import { apiFetch, showStatus } from '../api/client.js';

const output = document.querySelector('#reporting-results');
const summary = document.querySelector('#reporting-summary');
const trigger = document.querySelector('#reporting-generate');
let sequence = 0;
const number = value => Number.isInteger(value) && value >= 0;
const known = {
  authentication_required: 'Sign in with an administrator account.',
  forbidden: 'Your account is not permitted to view administrator reports.',
  reporting_unavailable: 'Report data is currently unavailable. Please try again later.',
};
function line(title, value) {
  const p = document.createElement('p');
  p.textContent = `${title}: ${value}`;
  return p;
}
async function load(path, range) {
  const current = ++sequence;
  output.replaceChildren(); summary.textContent = '';
  trigger.disabled = true;
  showStatus('Loading report data…');
  try {
    const data = await apiFetch(path);
    if (current !== sequence) return;
    if (!data || typeof data !== 'object') throw new Error('Unexpected response.');
    const nodes = [];
      const fields = [['donation_event_count', 'Donation events'], ['collected_unit_count', 'Collected units'],
        ['issued_unit_count', 'Issued units'], ['wasted_unit_count', 'Discarded units']];
      if (data.from !== range.from || data.to !== range.to || data.timezone !== 'Asia/Kolkata'
          || typeof data.definitions_version !== 'string') throw new Error('Unexpected report range.');
      for (const [field, title] of fields) {
        if (!number(data[field])) throw new Error('Unexpected total.');
        nodes.push(line(title, data[field]));
      }
      summary.textContent = `${data.from} through ${data.to}, inclusive (${data.timezone}).`;

    output.replaceChildren(...nodes);
    showStatus('Report data loaded.');
  } catch (error) {
    if (current !== sequence) return;
    output.replaceChildren(); summary.textContent = '';
    let text = typeof error?.code === 'string' && Object.hasOwn(known, error.code) ? known[error.code] : 'Could not load report data. Please try again.';
    if (error?.code === 'validation_error') text = 'Check the date range and try again.';
    showStatus(text);
  } finally {
    if (current === sequence) trigger.disabled = false;
  }
}
  document.querySelector('#reporting-form').addEventListener('submit', event => {
    event.preventDefault();
    const from = document.querySelector('#reporting-from').value;
    const to = document.querySelector('#reporting-to').value;
    const date = /^\d{4}-\d{2}-\d{2}$/;
    if (!date.test(from) || !date.test(to) || from > to) {
      ++sequence; output.replaceChildren(); summary.textContent = ''; trigger.disabled = false;
      showStatus('Choose valid dates with From no later than To.');
      return;
    }
    load(`/api/v1/reports?${new URLSearchParams({ from, to })}`, { from, to });
  });
