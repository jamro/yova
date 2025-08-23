.PHONY: help install install-dev test test-cov run clean lint format check build publish supervisor-start supervisor-stop supervisor-restart supervisor-status supervisor-logs supervisor-follow supervisor-dev

# Default target
help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$1, $$2}'

install: ## Install production dependencies
	poetry install --with rpi -vvv

install-dev: ## Install all dependencies (including dev)
	poetry install -vvv

test: ## Run tests
	export PATH="$$HOME/Library/Python/3.9/bin:$$PATH" && poetry run pytest

test-cov: ## Run tests with coverage
	export PATH="$$HOME/Library/Python/3.9/bin:$$PATH" && poetry run pytest --cov=yova_core --cov-report=term-missing --cov-report=html

test-watch: ## Run tests in watch mode
	poetry run pytest-watch

run: ## Run the application
	poetry run python scripts/supervisor_dev.py

dev-tools: ## Run dev tools
	poetry run yova-client-dev-tools

supervisor-start: ## Start supervisor and yova_core process
	poetry run supervisord -c configs/supervisord.conf

supervisor-stop: ## Stop supervisor and all processes
	poetry run supervisorctl -c configs/supervisord.conf shutdown

supervisor-restart: ## Restart yova_core process
	poetry run supervisorctl -c configs/supervisord.conf restart yova_core

supervisor-status: ## Show status of all supervised processes
	poetry run supervisorctl -c configs/supervisord.conf status

supervisor-logs: ## Show yova_core logs
	poetry run supervisorctl -c configs/supervisord.conf tail yova_core

supervisor-follow: ## Follow yova_core logs in real-time
	poetry run supervisorctl -c configs/supervisord.conf tail -f yova_core

supervisor-dev: ## Start development supervisor with auto-restart and log streaming
	poetry run python scripts/supervisor_dev.py

dev-pi-sync: ## Sync dev changes to Raspberry Pi
	fswatch -o ./ | while read f; do \
		rsync -az --delete ./ pi@yova.local:/home/pi/yova/; \
	done

clean: ## Clean up generated files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf dist
	rm -rf build

lint: ## Run linting checks
	poetry run flake8 yova_core tests
	poetry run black --check yova_core tests
	poetry run isort --check-only yova_core tests

format: ## Format code with black and isortsupervisor
	poetry run black yova_core tests
	poetry run isort yova_core tests

check: ## Run all checks (lint, test, format)
	$(MAKE) lint
	$(MAKE) test

build: ## Build the package
	poetry build

shell: ## Open Poetry shell
	poetry shell

add-deps: ## Add a new dependency (usage: make add-deps PACKAGE=requests)
	poetry add $(PACKAGE)

add-dev-deps: ## Add a new dev dependency (usage: make add-dev-deps PACKAGE=pytest-mock)
	poetry add --group dev $(PACKAGE)

update: ## Update all dependencies
	poetry update

lock: ## Update poetry.lock file
	poetry lock

show-deps: ## Show current dependencies
	poetry show

show-tree: ## Show dependency tree
	poetry show --tree 