import { apiFetch, showStatus } from '../api/client.js';
document.querySelector('#registration-form').addEventListener('submit', async event => {
  event.preventDefault();
  try { await apiFetch('/api/v1/auth/register', { method: 'POST', body: Object.fromEntries(new FormData(event.currentTarget)) }); showStatus('Integrate and verify BB-06 before claiming registration works.'); }
  catch (error) { showStatus(`${error.status || ''} ${error.message}`); }
});
