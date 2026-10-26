
import { apiFetch, showStatus } from '../api/client.js';

const form = document.querySelector('#donor-search-form');
const resultsSection = document.querySelector('#donor-results');
const resultsBody = document.querySelector('#donor-results-body');
const resultCount = document.querySelector('#result-count');
const pageIndicator = document.querySelector('#page-indicator');
const previousButton = document.querySelector('#previous-page');
const nextButton = document.querySelector('#next-page');

let currentPage = 1;
let totalPages = 1;

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

function renderResults(data) {
  if (
    !data ||
    typeof data !== 'object' ||
    !Number.isInteger(data.count) ||
    data.count < 0 ||
    !Number.isInteger(data.page) ||
    data.page < 1 ||
    !Number.isInteger(data.page_size) ||
    data.page_size < 1 ||
    data.page_size > 100 ||
    !Array.isArray(data.results)
  ) {
    throw new Error('The server returned an unexpected search response.');
  }

  for (const donor of data.results) {
    if (
      !donor ||
      typeof donor !== 'object' ||
      typeof donor.id !== 'string' ||
      !['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'].includes(donor.blood_group) ||
      typeof donor.location !== 'string' ||
      !['ELIGIBLE', 'INELIGIBLE', 'NOT_SCREENED', 'STALE'].includes(donor.eligibility_status)
    ) {
      throw new Error('The server returned an invalid donor summary.');
    }
  }

  resultsBody.replaceChildren();

  for (const donor of data.results) {
    const row = document.createElement('tr');
    addCell(row, donor.id);
    addCell(row, donor.blood_group);
    addCell(row, donor.location);
    addCell(row, donor.eligibility_status);
    resultsBody.appendChild(row);
  }

  currentPage = data.page;
  totalPages = Math.max(1, Math.ceil(data.count / data.page_size));

  resultCount.textContent = `Matching donors: ${data.count}`;
  pageIndicator.textContent = `Page ${currentPage} of ${totalPages}`;
  previousButton.disabled = currentPage <= 1;
  nextButton.disabled = currentPage >= totalPages;
  resultsSection.hidden = false;
}

async function searchDonors(page) {
  clearResults();

  const formData = new FormData(form);
  const params = new URLSearchParams();

  const bloodGroup = formData.get('blood_group');
  const location = formData.get('location').trim();
  const eligibilityStatus = formData.get('eligibility_status');
  const pageSize = Number(formData.get('page_size'));

  if (location.length > 120) {
    showStatus('Location must be 120 characters or fewer.');
    return;
  }

  if (!Number.isInteger(pageSize) || pageSize < 1 || pageSize > 100) {
    showStatus('Choose a page size between 1 and 100.');
    return;
  }

  if (bloodGroup) params.set('blood_group', bloodGroup);
  if (location) params.set('location', location);
  if (eligibilityStatus) params.set('eligibility_status', eligibilityStatus);

  params.set('page', String(page));
  params.set('page_size', String(pageSize));

  showStatus('Searching donors…');

  try {
    const data = await apiFetch(`/api/v1/donors?${params.toString()}`);
    renderResults(data);
    showStatus('Search completed.');
  } catch (error) {
    if (error.status === 400) {
      showStatus('Some search filters are invalid. Check your selections.');
    } else if (error.status === 403) {
      showStatus('Access denied. An authorized staff account is required.');
    } else if (error.status === 501) {
      showStatus('Staff donor search is not implemented by the backend yet. No results were loaded.');
    } else if (error.status === 503) {
      showStatus('The service is temporarily unavailable. Try again later.');
    } else {
      showStatus(error.message || 'Could not search donors.');
    }
  }
}

form.addEventListener('submit', event => {
  event.preventDefault();
  searchDonors(1);
});

previousButton.addEventListener('click', () => {
  if (currentPage > 1) searchDonors(currentPage - 1);
});

nextButton.addEventListener('click', () => {
  if (currentPage < totalPages) searchDonors(currentPage + 1);
});
