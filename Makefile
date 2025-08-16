.PHONY: help install install-dev test test-cov run clean lint format check build publish

# Default target
help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
	poetry install --only main

install-dev: ## Install all dependencies (including dev)
	poetry install

test: ## Run tests
	export PATH="$$HOME/Library/Python/3.9/bin:$$PATH" && poetry run pytest

test-cov: ## Run tests with coverage
	export PATH="$$HOME/Library/Python/3.9/bin:$$PATH" && poetry run pytest --cov=yova_core --cov-report=term-missing --cov-report=html

test-watch: ## Run tests in watch mode
	poetry run pytest-watch

run: ## Run the application
	poetry run voice-command-station

run-with-name: ## Run the application with a custom name (usage: make run-with-name NAME=Alice)
	poetry run voice-command-station $(NAME)

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

format: ## Format code with black and isort
	poetry run black yova_core tests
	poetry run isort yova_core tests

check: ## Run all checks (lint, test, format)
	$(MAKE) lint
	$(MAKE) test

build: ## Build the package
	poetry build

publish: ## Publish to PyPI (use with caution)
	poetry publish

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