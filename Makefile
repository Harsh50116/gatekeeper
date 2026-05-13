.PHONY: help db-up db-down db-init db-reset db-psql db-status

help:
	@echo "Local DB targets (Docker Postgres on localhost:5432/gatekeeper):"
	@echo "  make db-up       Start the local Postgres container"
	@echo "  make db-down     Stop the container (data persists in volume)"
	@echo "  make db-init     Apply all migrations to the local DB"
	@echo "  make db-reset    Wipe volume, restart, re-apply migrations"
	@echo "  make db-psql     Open an interactive psql shell"
	@echo "  make db-status   Show container status"

db-up:
	docker compose up -d
	@echo "Waiting for Postgres to accept connections..."
	@until docker compose exec -T db pg_isready -U postgres -d gatekeeper > /dev/null 2>&1; do sleep 1; done
	@echo "Postgres ready at localhost:5432 (db=gatekeeper, user=postgres)"

db-down:
	docker compose down

db-init:
	@for f in migrations/*.sql; do \
		echo "Applying $$f..."; \
		cat "$$f" | docker compose exec -T db psql -U postgres -d gatekeeper -v ON_ERROR_STOP=1; \
	done
	@echo "Migrations applied."

db-reset:
	docker compose down -v
	@$(MAKE) db-up
	@$(MAKE) db-init

db-psql:
	docker compose exec db psql -U postgres -d gatekeeper

db-status:
	docker compose ps
