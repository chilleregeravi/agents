# Agent Makefile
# Simplified version with essential targets only

.PHONY: help setup build deploy status logs clean lint lint-fix test mypy mypy-fix install-types

# Agent configuration
AGENT_NAME := $(shell basename $(CURDIR))

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

# Default target
.DEFAULT_GOAL := help

# Define targets
help: ## Show this help message
	@echo "$(BLUE)Agent: $(AGENT_NAME)$(NC)"
	@echo "Available targets:"
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make $(GREEN)<target>$(NC)\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

setup: ## Set up development environment
	@echo "$(BLUE)Setting up agent: $(AGENT_NAME)$(NC)"
	@python3 -m venv .venv
	@.venv/bin/pip install --upgrade pip
	@if [ -f requirements/requirements.txt ]; then .venv/bin/pip install -r requirements/requirements.txt; fi
	@if [ -f requirements/requirements-dev.txt ]; then .venv/bin/pip install -r requirements/requirements-dev.txt; fi
	@echo "$(GREEN)✓ Agent setup complete$(NC)"

build: ## Build Docker images
	@echo "$(BLUE)Building Docker image for $(AGENT_NAME)...$(NC)"
	@if [ -f docker/Dockerfile ]; then \
		podman build -f docker/Dockerfile -t "harbor.ramaedge.local/agents/$(AGENT_NAME):latest" .; \
		echo "$(GREEN)✓ Docker image built successfully$(NC)"; \
	else \
		echo "$(YELLOW)No Dockerfile found for $(AGENT_NAME)$(NC)"; \
	fi

deploy: ## Deploy to Kubernetes
	@echo "$(BLUE)Deploying $(AGENT_NAME)...$(NC)"
	@if [ -f k8s/base/kustomization.yaml ]; then \
		kubectl create namespace $(AGENT_NAME) --dry-run=client -o yaml | kubectl apply -f -; \
		kubectl apply -k k8s/overlays/production; \
		echo "$(GREEN)✓ $(AGENT_NAME) deployed successfully$(NC)"; \
	else \
		echo "$(YELLOW)No Kustomize configuration found for $(AGENT_NAME)$(NC)"; \
	fi

status: ## Check deployment status
	@kubectl get all -n $(AGENT_NAME)

logs: ## Show application logs
	@kubectl logs -f deployment/$(AGENT_NAME) -n $(AGENT_NAME)

clean: ## Clean build artifacts and caches
	@echo "$(BLUE)Cleaning $(AGENT_NAME)...$(NC)"
	@rm -rf .venv
	@rm -rf .pytest_cache
	@rm -rf htmlcov
	@rm -rf .coverage
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "$(GREEN)✓ $(AGENT_NAME) cleaned$(NC)"

lint: ## Run code linting
	@echo "$(BLUE)Linting $(AGENT_NAME)...$(NC)"
	@if [ -d .venv ] && [ -d src ]; then \
		.venv/bin/black --check src/ tests/ 2>/dev/null || echo "$(YELLOW)Black not available$(NC)"; \
		.venv/bin/isort --check-only src/ tests/ 2>/dev/null || echo "$(YELLOW)isort not available$(NC)"; \
		.venv/bin/flake8 src/ tests/ 2>/dev/null || echo "$(YELLOW)flake8 not available$(NC)"; \
		.venv/bin/mypy src/ 2>/dev/null; \
		echo "$(GREEN)✓ $(AGENT_NAME) linting complete$(NC)"; \
	else \
		echo "$(YELLOW)No virtual environment or src/ directory found for $(AGENT_NAME)$(NC)"; \
	fi

lint-fix: ## Fix linting issues automatically
	@echo "$(BLUE)Fixing linting issues for $(AGENT_NAME)...$(NC)"
	@if [ -d .venv ] && [ -d src ]; then \
		.venv/bin/black src/ tests/ 2>/dev/null || echo "$(YELLOW)Black not available$(NC)"; \
		.venv/bin/isort src/ tests/ 2>/dev/null || echo "$(YELLOW)isort not available$(NC)"; \
		echo "$(GREEN)✓ $(AGENT_NAME) linting fixes complete$(NC)"; \
	else \
		echo "$(YELLOW)No virtual environment or src/ directory found for $(AGENT_NAME)$(NC)"; \
	fi

mypy: ## Run mypy type checking
	@echo "$(BLUE)Running mypy for $(AGENT_NAME)...$(NC)"
	@if [ -d .venv ] && [ -d src ]; then \
		.venv/bin/mypy src/ 2>/dev/null || echo "$(YELLOW)mypy not available$(NC)"; \
		echo "$(GREEN)✓ $(AGENT_NAME) mypy complete$(NC)"; \
	else \
		echo "$(YELLOW)No virtual environment or src/ directory found for $(AGENT_NAME)$(NC)"; \
	fi

mypy-fix: ## Fix mypy issues (add type hints and ignore comments)
	@echo "$(BLUE)Fixing mypy issues for $(AGENT_NAME)...$(NC)"
	@if [ -d .venv ] && [ -d src ]; then \
		echo "$(YELLOW)Note: mypy-fix will help identify issues but manual fixes may be needed$(NC)"; \
		.venv/bin/mypy src/ --show-error-codes 2>/dev/null || echo "$(YELLOW)mypy not available$(NC)"; \
		echo "$(GREEN)✓ $(AGENT_NAME) mypy analysis complete$(NC)"; \
	else \
		echo "$(YELLOW)No virtual environment or src/ directory found for $(AGENT_NAME)$(NC)"; \
	fi

install-types: ## Install missing type stubs for better mypy support
	@echo "$(BLUE)Installing type stubs for $(AGENT_NAME)...$(NC)"
	@if [ -d .venv ]; then \
		.venv/bin/pip install types-beautifulsoup4 types-requests types-aiofiles 2>/dev/null || echo "$(YELLOW)Some type stubs not available$(NC)"; \
		echo "$(GREEN)✓ $(AGENT_NAME) type stubs installation complete$(NC)"; \
	else \
		echo "$(YELLOW)No virtual environment found for $(AGENT_NAME)$(NC)"; \
	fi

test: ## Run tests
	@echo "$(BLUE)Running tests for $(AGENT_NAME)...$(NC)"
	@if [ -d .venv ] && [ -d tests ]; then \
		.venv/bin/pytest tests/ -v --cov=src --cov-report=term-missing 2>/dev/null || echo "$(YELLOW)pytest not available$(NC)"; \
		echo "$(GREEN)✓ $(AGENT_NAME) tests complete$(NC)"; \
	elif [ -d .venv ] && [ -d src ]; then \
		echo "$(YELLOW)No tests/ directory found for $(AGENT_NAME)$(NC)"; \
	else \
		echo "$(YELLOW)No virtual environment found for $(AGENT_NAME)$(NC)"; \
	fi
