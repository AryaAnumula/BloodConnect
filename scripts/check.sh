
#!/usr/bin/env sh
set -eu
python scripts/validate_repository.py
python backend/manage.py check
python backend/manage.py makemigrations --check --dry-run
python backend/manage.py test core.tests accounts.tests audit.tests donors.tests --verbosity 2
node --test notification-service/tests/*.test.mjs tests/frontend-api.test.mjs tests/frontend-input-safety.test.mjs tests/frontend-registration.test.mjs tests/frontend-registration-behavior.test.mjs tests/frontend-eligibility.test.mjs tests/frontend-search.test.mjs tests/frontend-search-behavior.test.mjs
python -m unittest discover -s tests -p "test_availability.py" -v
