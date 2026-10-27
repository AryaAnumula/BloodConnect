import { apiFetch, showStatus } from '../api/client.js';
const form = document.querySelector('#registration-form');
form.addEventListener('submit', async event => {
  event.preventDefault();
  try {
    await apiFetch('/api/v1/auth/register', { method: 'POST', body: Object.fromEntries(new FormData(form)) });
    form.reset();
    showStatus('Account created. You can now sign in.');
  } catch (error) { showStatus(error.message); }
});