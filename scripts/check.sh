#!/usr/bin/env sh
set -eu
python scripts/validate_repository.py
python backend/manage.py check
python backend/manage.py makemigrations --check --dry-run
python backend/manage.py test core.tests accounts.tests --verbosity 2
node --test notification-service/tests/*.test.mjs tests/frontend-api.test.mjs tests/frontend-input-safety.test.mjs
