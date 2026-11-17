// BB-20, Ankitha. Camp list, create and update page. Cancel is NOT built (waits on S2-05/S2-06).
// Page access grants nothing: the server decides every action by role.
import { apiFetch, showStatus } from '../api/client.js';

const filterForm = document.querySelector('#camp-filter-form');
const createForm = document.querySelector('#camp-create-form');
const updateForm = document.querySelector('#camp-update-form');
const resultsSection = document.querySelector('#camp-results');
const resultsBody = document.querySelector('#camp-results-body');
const resultCount = document.querySelector('#camp-count');
const pageIndicator = document.querySelector('#page-indicator');
const previousButton = document.querySelector('#previous-page');
const nextButton = document.querySelector('#next-page');

const MAX_DB_INTEGER = 2147483647;
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const CAMP_STATES = ['ACTIVE', 'CANCELLED'];

let currentPage = 1;
let totalPages = 1;
let latestRequestId = 0;
let appliedFilters = Object.freeze({ status: '', pageSize: 20 });

function clearResults() {
  resultsSection.hidden = true;
  resultsBody.replaceChildren();
  resultCount.textContent = '';
  pageIndicator.textContent = '';
  previousButton.disabled = true;
  nextButton.disabled = true;
}

function addCell(row, value) {
  const cell = document.createElement('td');
  cell.textContent = String(value ?? 'Not provided');
  row.appendChild(cell);
}

function isValidCamp(camp) {
  return Boolean(camp) && typeof camp === 'object' &&
    typeof camp.id === 'string' && typeof camp.name === 'string' &&
    typeof camp.location === 'string' && typeof camp.starts_at === 'string' &&
    typeof camp.ends_at === 'string' && Number.isInteger(camp.capacity) &&
    CAMP_STATES.includes(camp.status);
}

function renderResults(data) {
  if (!data || typeof data !== 'object' || !Number.isInteger(data.count) || data.count < 0 ||
      !Number.isInteger(data.page) || data.page < 1 || !Number.isInteger(data.page_size) ||
      data.page_size < 1 || data.page_size > 100 || !Array.isArray(data.results)) {
    throw new Error('The server returned an unexpected camp list.');
  }
  if (!data.results.every(isValidCamp)) throw new Error('The server returned an invalid camp.');

  resultsBody.replaceChildren();
  for (const camp of data.results) {
    const row = document.createElement('tr');
    addCell(row, camp.id);
    addCell(row, camp.name);
    addCell(row, camp.location);
    addCell(row, camp.starts_at);
    addCell(row, camp.ends_at);
    addCell(row, camp.capacity);
    addCell(row, camp.status);
    resultsBody.appendChild(row);
  }
  currentPage = data.page;
  totalPages = Math.max(1, Math.ceil(data.count / data.page_size));
  resultCount.textContent = data.count === 0 ? 'No camps to show.' : `Camps: ${data.count}`;
  pageIndicator.textContent = `Page ${currentPage} of ${totalPages}`;
  previousButton.disabled = currentPage <= 1;
  nextButton.disabled = currentPage >= totalPages;
  resultsSection.hidden = false;
}

function fieldMessages(fields) {
  return Object.entries(fields || {})
    .map(([name, messages]) => `${name}: ${Array.isArray(messages) ? messages.join(' ') : ''}`)
    .join(' ');
}

function describeError(error, fallback) {
  if (error.status === 400 || error.status === 422) {
    const detail = fieldMessages(error.fields);
    return detail ? `${error.message} ${detail}` : error.message;
  }
  if (error.status === 403) return 'Access denied. Your account is not allowed to do this.';
  if (error.status === 404) return 'Camp not found.';
  if (error.status === 503) return 'The service is temporarily unavailable. Try again later.';
  return error.message || fallback;
}

function readFilters() {
  const formData = new FormData(filterForm);
  const status = String(formData.get('status') ?? '');
  const rawPageSize = String(formData.get('page_size') ?? '');
  const pageSize = Number(rawPageSize);
  if (status && !CAMP_STATES.includes(status)) throw new Error('Choose a valid status.');
  if (!/^\d+$/.test(rawPageSize) || pageSize < 1 || pageSize > 100) {
    throw new Error('Choose a page size between 1 and 100.');
  }
  return Object.freeze({ status, pageSize });
}

async function loadCamps(page, filters, doneMessage = 'Camps loaded.') {
  const requestId = ++latestRequestId;
  clearResults();
  try {
    if (!filters) {
      filters = readFilters();
      appliedFilters = filters;
    }
    if (!Number.isSafeInteger(page) || page < 1) throw new Error('Choose a valid page.');
  } catch (error) {
    showStatus(error.message);
    return;
  }
  const params = new URLSearchParams();
  if (filters.status) params.set('status', filters.status);
  params.set('page', String(page));
  params.set('page_size', String(filters.pageSize));
  showStatus('Loading camps…');
  try {
    const data = await apiFetch(`/api/v1/camps?${params.toString()}`);
    if (requestId !== latestRequestId) return;
    renderResults(data);
    showStatus(doneMessage);
  } catch (error) {
    if (requestId !== latestRequestId) return;
    clearResults();
    showStatus(describeError(error, 'Could not load camps.'));
  }
}

function requiredText(formData, name, label) {
  const value = String(formData.get(name) ?? '').trim();
  if (!value) throw new Error(`${label} is required.`);
  if (value.length > 120) throw new Error(`${label} must be 120 characters or fewer.`);
  return value;
}

function toUtcIso(raw, label) {
  const text = String(raw ?? '').trim();
  if (!text) throw new Error(`${label} is required.`);
  const date = new Date(text);
  if (Number.isNaN(date.getTime())) throw new Error(`${label} is not a valid date and time.`);
  return date.toISOString();
}

function toCapacity(raw) {
  const text = String(raw ?? '').trim();
  const value = Number(text);
  if (!/^\d+$/.test(text) || value < 1 || value > MAX_DB_INTEGER) {
    throw new Error('Capacity must be a whole number of 1 or more.');
  }
  return value;
}

function readCreate() {
  const formData = new FormData(createForm);
  const body = {
    name: requiredText(formData, 'name', 'Name'),
    location: requiredText(formData, 'location', 'Location'),
    starts_at: toUtcIso(formData.get('starts_at'), 'Start'),
    ends_at: toUtcIso(formData.get('ends_at'), 'End'),
    capacity: toCapacity(formData.get('capacity')),
  };
  if (Date.parse(body.starts_at) >= Date.parse(body.ends_at)) throw new Error('End must be after start.');
  return body;
}

function readUpdate() {
  const formData = new FormData(updateForm);
  const campId = String(formData.get('camp_id') ?? '').trim();
  if (!UUID_PATTERN.test(campId)) throw new Error('Enter a valid camp ID.');
  const body = {};
  if (String(formData.get('name') ?? '').trim()) body.name = requiredText(formData, 'name', 'Name');
  if (String(formData.get('location') ?? '').trim()) body.location = requiredText(formData, 'location', 'Location');
  if (String(formData.get('starts_at') ?? '').trim()) body.starts_at = toUtcIso(formData.get('starts_at'), 'Start');
  if (String(formData.get('ends_at') ?? '').trim()) body.ends_at = toUtcIso(formData.get('ends_at'), 'End');
  if (String(formData.get('capacity') ?? '').trim()) body.capacity = toCapacity(formData.get('capacity'));
  if (Object.keys(body).length === 0) throw new Error('Change at least one field.');
  if (body.starts_at && body.ends_at && Date.parse(body.starts_at) >= Date.parse(body.ends_at)) {
    throw new Error('End must be after start.');
  }
  return { campId, body };
}

filterForm.addEventListener('submit', event => {
  event.preventDefault();
  loadCamps(1);
});

createForm.addEventListener('submit', async event => {
  event.preventDefault();
  let body;
  try {
    body = readCreate();
  } catch (error) {
    showStatus(error.message);
    return;
  }
  showStatus('Creating camp…');
  try {
    await apiFetch('/api/v1/camps', { method: 'POST', body });
  } catch (error) {
    showStatus(describeError(error, 'Could not create the camp.'));
    return;
  }
  loadCamps(1, appliedFilters, 'Camp created.');
});

updateForm.addEventListener('submit', async event => {
  event.preventDefault();
  let request;
  try {
    request = readUpdate();
  } catch (error) {
    showStatus(error.message);
    return;
  }
  showStatus('Updating camp…');
  try {
    await apiFetch(`/api/v1/camps/${request.campId}`, { method: 'PATCH', body: request.body });
  } catch (error) {
    showStatus(describeError(error, 'Could not update the camp.'));
    return;
  }
  loadCamps(currentPage, appliedFilters, 'Camp updated.');
});

previousButton.addEventListener('click', () => {
  if (!previousButton.disabled && currentPage > 1) loadCamps(currentPage - 1, appliedFilters);
});

nextButton.addEventListener('click', () => {
  if (!nextButton.disabled && currentPage < totalPages) loadCamps(currentPage + 1, appliedFilters);
});

loadCamps(1, appliedFilters);
