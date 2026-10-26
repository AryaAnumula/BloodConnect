import { apiFetch, resetCsrfToken, showStatus } from '../api/client.js';
document.querySelector('#login-form').addEventListener('submit', async event => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  try {
    await apiFetch('/api/v1/auth/login', { method: 'POST', body: { email: form.get('email'), password: form.get('password') } });
    resetCsrfToken(); // the session rotates on login, so fetch a fresh CSRF token next time
    showStatus('Signed in successfully.');
  } catch (error) { showStatus(error.message); }
});