ENV_FILE ?=
COMPOSE = docker compose --env-file "$(ENV_FILE)" -f docker-compose.environment.yml

# ENV_FILE must identify a generated private development configuration.
up:
	$(COMPOSE) up -d --build backend frontend

stop:
	$(COMPOSE) stop

# Compatibility alias: stop services while preserving containers and volumes.
down: stop

build:
	$(COMPOSE) build

migrate:
	$(COMPOSE) run -T migrate

seed:
	$(COMPOSE) run -T seed

logs:
	$(COMPOSE) logs -f

backend-test:
	python -m unittest discover -s scripts -p "test_*.py"
	docker compose --env-file .env.test.example -p paideia-synthetic-tests -f docker-compose.tests.yml build
	docker compose --env-file .env.test.example -p paideia-synthetic-tests -f docker-compose.tests.yml run -T migrate
	docker compose --env-file .env.test.example -p paideia-synthetic-tests -f docker-compose.tests.yml run -T tests

frontend-test:
	cd frontend && npm test -- --run

lint:
	cd backend && ruff check .
	cd frontend && npm run lint

format:
	cd backend && ruff format .
	cd frontend && npm run format
