.PHONY: help build up down logs restart clean test lint format

help:
	@echo "MCP Servers - Available Commands"
	@echo "=================================="
	@echo ""
	@echo "Setup:"
	@echo "  make setup          - Copy .env.example to .env and create secrets dir"
	@echo ""
	@echo "Docker Operations:"
	@echo "  make build          - Build all Docker images"
	@echo "  make up             - Start all services"
	@echo "  make down           - Stop all services"
	@echo "  make restart        - Restart all services"
	@echo "  make logs           - View all service logs"
	@echo "  make logs-sql       - View SQL server logs"
	@echo "  make logs-gd        - View Google Drive server logs"
	@echo "  make logs-sp        - View SharePoint server logs"
	@echo "  make logs-db        - View Dropbox server logs"
	@echo ""
	@echo "Development:"
	@echo "  make test           - Run tests"
	@echo "  make lint           - Run linting"
	@echo "  make format         - Format code with black"
	@echo "  make clean          - Remove Python cache and build artifacts"
	@echo ""
	@echo "Database:"
	@echo "  make db-init        - Initialize PostgreSQL database"
	@echo "  make db-shell       - Open PostgreSQL shell"
	@echo ""

setup:
	@echo "Setting up MCP Servers environment..."
	@cp -v .env.example .env
	@mkdir -p secrets logs
	@echo "✓ Environment configured. Please update .env with your credentials."

build:
	@echo "Building Docker images..."
	docker-compose build --no-cache
	@echo "✓ Build complete"

up:
	@echo "Starting MCP services..."
	docker-compose up -d
	@echo "✓ Services started"
	@docker-compose ps

down:
	@echo "Stopping MCP services..."
	docker-compose down
	@echo "✓ Services stopped"

restart:
	@echo "Restarting MCP services..."
	docker-compose restart
	@echo "✓ Services restarted"
	@docker-compose ps

logs:
	docker-compose logs -f

logs-sql:
	docker-compose logs -f sql-server

logs-gd:
	docker-compose logs -f google-drive-server

logs-sp:
	docker-compose logs -f sharepoint-server

logs-db:
	docker-compose logs -f dropbox-server

test:
	@echo "Running tests..."
	@python -m pytest tests/ -v

lint:
	@echo "Linting code..."
	@python -m flake8 sql-server google-drive-server sharepoint-server dropbox-server

format:
	@echo "Formatting code with black..."
	@python -m black sql-server google-drive-server sharepoint-server dropbox-server

clean:
	@echo "Cleaning up..."
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name ".DS_Store" -delete
	@rm -rf .pytest_cache .coverage htmlcov
	@echo "✓ Cleanup complete"

db-init:
	@echo "Initializing PostgreSQL database..."
	@docker-compose exec postgres psql -U postgres -c "CREATE DATABASE bugmentor;" || true
	@echo "✓ Database initialized"

db-shell:
	@docker-compose exec postgres psql -U postgres -d bugmentor

status:
	@echo "Service Status:"
	@docker-compose ps

prune:
	@echo "Pruning unused Docker resources..."
	@docker system prune -f
	@echo "✓ Prune complete"

pull:
	@echo "Pulling latest images..."
	@docker-compose pull

version:
	@echo "Checking versions..."
	@docker --version
	@docker-compose --version
	@python --version

.DEFAULT_GOAL := help
