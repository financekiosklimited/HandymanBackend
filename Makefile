# Makefile for sb Django project
#
# This project uses PostgreSQL as the database backend.
# Prerequisites: PostgreSQL, uv package manager, Python 3.13+
#
# Quick start: make setup

# Variables
UV := uv
MANAGE := $(UV) run python manage.py

# Colors for output
BLUE := \033[34m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
NC := \033[0m # No Color

# Default target
.PHONY: help
help: ## Show available commands
	@echo "$(BLUE)Available commands:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)  %-15s$(NC) %s\n", $$1, $$2}'

# Environment setup
.PHONY: install
install: ## Install dependencies
	@echo "$(BLUE)Installing dependencies...$(NC)"
	$(UV) sync

.PHONY: venv
venv: ## Create virtual environment
	@echo "$(BLUE)Creating virtual environment...$(NC)"
	$(UV) venv

# Development
.PHONY: run
run: ## Run development server
	@echo "$(BLUE)Starting development server...$(NC)"
	$(MANAGE) runserver

.PHONY: shell
shell: ## Start Django shell
	@echo "$(BLUE)Starting Django shell...$(NC)"
	$(MANAGE) shell

# Database
.PHONY: check-postgres
check-postgres: ## Check PostgreSQL connection
	@$(UV) run python -c "import psycopg; import os; from django.conf import settings; import django; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev'); django.setup(); db_config = settings.DATABASES['default']; conn = psycopg.connect(host=db_config['HOST'], port=db_config['PORT'], user=db_config['USER'], password=db_config['PASSWORD'] or None); print('✅ PostgreSQL connection successful'); conn.close()" 2>/dev/null || (echo "$(RED)❌ PostgreSQL connection failed$(NC)"; exit 1)

.PHONY: create-db
create-db: ## Create PostgreSQL database
	@echo "$(BLUE)Creating PostgreSQL database...$(NC)"
	@DB_NAME=$$(grep DB_NAME .env | cut -d= -f2); \
	DB_USER=$$(grep DB_USER .env | cut -d= -f2); \
	DB_HOST=$$(grep DB_HOST .env | cut -d= -f2); \
	DB_PORT=$$(grep DB_PORT .env | cut -d= -f2); \
	$(UV) run python -c "import psycopg; conn = psycopg.connect(host='$$DB_HOST', port='$$DB_PORT', user='$$DB_USER', dbname='postgres'); conn.autocommit = True; cur = conn.cursor(); cur.execute('CREATE DATABASE $$DB_NAME'); conn.close(); print('✅ Database created')" 2>/dev/null || echo "$(YELLOW)⚠️ Database may already exist$(NC)"

.PHONY: migrate
migrate: check-postgres ## Run database migrations
	@echo "$(BLUE)Running migrations...$(NC)"
	$(MANAGE) migrate

.PHONY: makemigrations
makemigrations: check-postgres ## Create new migrations
	@echo "$(BLUE)Creating migrations...$(NC)"
	$(MANAGE) makemigrations

# Django management
.PHONY: createsuperuser
createsuperuser: ## Create superuser
	@echo "$(BLUE)Creating superuser...$(NC)"
	$(MANAGE) createsuperuser

# Testing
.PHONY: test
test: ## Run tests
	@echo "$(BLUE)Running tests...$(NC)"
	$(MANAGE) test

# Utilities
.PHONY: clean
clean: ## Clean temporary files
	@echo "$(BLUE)Cleaning temporary files...$(NC)"
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -delete
	@rm -rf .pytest_cache/ .coverage htmlcov/

# Setup commands
.PHONY: setup
setup: venv install create-db migrate ## Complete project setup
	@echo "$(GREEN)✅ Setup complete! Run 'make run' to start the server.$(NC)"

.PHONY: fresh-setup
fresh-setup: clean setup ## Clean setup from scratch
	@echo "$(GREEN)✅ Fresh setup complete!$(NC)"
