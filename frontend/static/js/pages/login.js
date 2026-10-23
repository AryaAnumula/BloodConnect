import { apiFetch, resetCsrfToken, showStatus } from '../api/client.js';
document.querySelector('#login-form').addEventListener('submit', async event => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  try {
    await apiFetch('/api/v1/auth/login', { method: 'POST', body: { email: form.get('email'), password: form.get('password') } });
    resetCsrfToken();
    showStatus('Login endpoint responded. Complete BB-01 integration before claiming success.');
  } catch (error) { showStatus(`${error.status || ''} ${error.message}`); }
});
