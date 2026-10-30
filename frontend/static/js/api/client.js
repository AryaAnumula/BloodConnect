// Shared client. Yashwitha owns; Arnav reviews auth/CSRF changes.
let csrfToken;
export function resetCsrfToken() { csrfToken = undefined; }
async function getCsrfToken() {
  if (!csrfToken) {
    const response = await fetch('/api/v1/auth/csrf', { credentials: 'same-origin' });
    if (!response.ok) throw new Error('Could not initialize CSRF protection.');
    csrfToken = (await response.json()).csrf_token;
  }
  return csrfToken;
}
export async function apiFetch(path, { method = 'GET', body } = {}) {
  if (!path.startsWith('/api/v1/')) throw new Error('Only agreed same-origin API paths are allowed.');
  const headers = { Accept: 'application/json' };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) headers['X-CSRFToken'] = await getCsrfToken();
  const response = await fetch(path, { method, headers, credentials: 'same-origin', body: body === undefined ? undefined : JSON.stringify(body) });
  const payload = response.status === 204 ? null : await response.json();
  if (!response.ok) {
    const error = new Error(payload.error?.message || 'Request failed.');
    error.status = response.status; error.code = payload.error?.code;
    error.fields = payload.error?.fields && typeof payload.error.fields === 'object' && !Array.isArray(payload.error.fields) ? payload.error.fields : {};
    throw error;
  }
  return payload;
}
export function showStatus(message) { document.querySelector('#status').textContent = message; }
