// ADMIN-only APIs remain authoritative. An unavailable provider never becomes a zero total.
import { apiFetch, showStatus } from '../api/client.js';

const output = document.querySelector('#reporting-results');
const summary = document.querySelector('#reporting-summary');
const trigger = document.querySelector('#reporting-refresh');
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
      if (!number(data.pending_requests) || !number(data.upcoming_camps) || !Array.isArray(data.stock)
          || typeof data.as_of !== 'string') throw new Error('Unexpected summary.');
      nodes.push(line('Pending requests', data.pending_requests), line('Upcoming camps', data.upcoming_camps));
      for (const row of data.stock) {
        if (!row || typeof row.blood_group !== 'string' || typeof row.component_type !== 'string'
            || !number(row.available_quantity)) throw new Error('Unexpected stock.');
        nodes.push(line(`${row.blood_group} ${row.component_type}`, `${row.available_quantity} available units`));
      }
      if (!data.stock.length) nodes.push(line('Stock', 'No available stock rows.'));
      summary.textContent = `As of ${data.as_of}. Refresh to check for changes.`;

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
  trigger.addEventListener('click', () => load('/api/v1/dashboard'));
  load('/api/v1/dashboard');
