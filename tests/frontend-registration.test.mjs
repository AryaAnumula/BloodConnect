
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const registrationHtml = await readFile(
  new URL('../frontend/templates/register.html', import.meta.url),
  'utf8'
);

const registrationJs = await readFile(
  new URL('../frontend/static/js/pages/registration.js', import.meta.url),
  'utf8'
);
const baseHtml = await readFile(
  new URL('../frontend/templates/base.html', import.meta.url),
  'utf8'
);

const appCss = await readFile(
  new URL('../frontend/static/css/app.css', import.meta.url),
  'utf8'
);

test('registration page contains the expected form and fields', () => {
  assert.match(registrationHtml, /id="registration-form"/);
  assert.match(registrationHtml, /name="full_name"/);
  assert.match(registrationHtml, /name="email"/);
  assert.match(registrationHtml, /name="mobile"/);
  assert.match(registrationHtml, /name="password"/);
  assert.match(registrationHtml, /name="blood_group"/);
  assert.match(registrationHtml, /name="location"/);
});

test('registration page loads its JavaScript module', () => {
  assert.match(registrationHtml, /js\/pages\/registration\.js/);
});

test('registration submits through the shared API client', () => {
  assert.match(registrationJs, /apiFetch/);
  assert.match(registrationJs, /\/api\/v1\/auth\/register/);
  assert.match(registrationJs, /method:\s*'POST'/);
});

test('registration displays API errors instead of claiming success', () => {
  assert.match(registrationJs, /catch\s*\(/);
  assert.match(registrationJs, /showStatus/);
  assert.doesNotMatch(registrationJs, /Registration successful/);
});

test('registration form controls have visible labels', () => {
  assert.match(registrationHtml, /<label>Full name<input/);
  assert.match(registrationHtml, /<label>Email<input/);
  assert.match(registrationHtml, /<label>Mobile[^<]*<input/);
  assert.match(registrationHtml, /<label>Password<input/);
  assert.match(registrationHtml, /<label>Blood group<select/);
  assert.match(registrationHtml, /<label>Location<input/);
});

test('page provides an accessible status region', () => {
  assert.match(baseHtml, /role="status"/);
  assert.match(baseHtml, /aria-live="polite"/);
});

test('form controls have basic overflow protection', () => {
  assert.match(appCss, /max-width:\s*100%/);
  assert.match(appCss, /box-sizing:\s*border-box/);
});

test('registration styles include a mobile breakpoint', () => {
  assert.match(appCss, /@media\s*\(max-width:\s*600px\)/);
  assert.match(appCss, /form\s*\{[^}]*width:\s*100%/s);
});

test('keyboard users have a visible focus indicator', () => {
  assert.match(appCss, /:focus-visible\s*\{/);
  assert.match(appCss, /outline:\s*3px solid/);
});
