.PHONY: help db-init db-reset db-psql db-status redis-up redis-cli

# Local Postgres is the Homebrew instance (postgresql@17) on localhost:5432.
# Redis still comes from Docker.
PSQL := /opt/homebrew/opt/postgresql@17/bin/psql
DB_URL := postgres://postgres@localhost:5432/gatekeeper

help:
	@echo "Local DB targets (Homebrew Postgres on localhost:5432/gatekeeper):"
	@echo "  make db-init     Apply all migrations to the local DB"
	@echo "  make db-reset    Drop & recreate the schema, re-apply migrations"
	@echo "  make db-psql     Open an interactive psql shell"
	@echo "  make db-status   Show the DB the app connects to"
	@echo "  make redis-up    Start the Redis container (Docker)"
	@echo "  make redis-cli   Open redis-cli"

db-init:
	@for f in migrations/*.sql; do \
		echo "Applying $$f..."; \
		$(PSQL) "$(DB_URL)" -v ON_ERROR_STOP=1 -f "$$f"; \
	done
	@echo "Migrations applied."

db-reset:
	$(PSQL) "$(DB_URL)" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
	@$(MAKE) db-init

db-psql:
	$(PSQL) "$(DB_URL)"

db-status:
	@$(PSQL) "$(DB_URL)" -c "SELECT current_database(), current_user, inet_server_addr() AS host, inet_server_port() AS port;"

redis-up:
	docker compose up -d redis

redis-cli:
	docker compose exec redis redis-cli
