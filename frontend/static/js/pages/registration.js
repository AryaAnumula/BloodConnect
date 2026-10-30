import { apiFetch, showStatus } from '../api/client.js';
const form = document.querySelector('#registration-form');
const errors = document.querySelector('#registration-errors');
const submitButton = form.querySelector('button');
const labels = {full_name: 'Full name', email: 'Email', mobile: 'Mobile', password: 'Password', blood_group: 'Blood group', location: 'Location'};
let submitting = false;
form.addEventListener('submit', async event => {
  event.preventDefault();
  if (submitting) return;
  submitting = true;
  submitButton.disabled = true;
  errors.replaceChildren();
  showStatus('Creating account…');
  try {
    await apiFetch('/api/v1/auth/register', { method: 'POST', body: Object.fromEntries(new FormData(form)) });
    form.reset();
    showStatus('Account created. You can now sign in.');
  } catch (error) {
    showStatus(error.message || 'Could not create account.');
    for (const [name, messages] of Object.entries(error.fields || {})) {
      if (!Object.hasOwn(labels, name) && name !== 'non_field_errors') continue;
      const item = document.createElement('li');
      const text = (Array.isArray(messages) ? messages : [messages]).filter(x => typeof x === 'string').join(' ');
      if (!text) continue;
      item.textContent = `${labels[name] || 'Registration'}: ${text}`;
      errors.appendChild(item);
    }
  } finally {
    submitting = false;
    submitButton.disabled = false;
  }
});
