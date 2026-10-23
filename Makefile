.PHONY: env up down test check
env:
	python scripts/bootstrap_env.py
up:
	docker compose up --build
down:
	docker compose down
test:
	docker compose run --rm web python backend/manage.py test core.tests accounts.tests
check:
	sh scripts/check.sh
