import { apiFetch, resetCsrfToken } from '../api/client.js';

const button = document.querySelector('#session-logout');
const status = document.querySelector('#session-logout-status');
button.addEventListener('click', async () => {
  button.disabled = true;
  status.textContent = '';
  try {
    await apiFetch('/api/v1/auth/logout', { method: 'POST' });
    resetCsrfToken();
    window.location.assign('/login');
  } catch (error) {
    status.textContent = 'Could not log out. Please refresh the page and try again.';
    button.disabled = false;
  }
});
