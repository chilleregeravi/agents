# LLM Release Radar Agent Makefile
# This Makefile delegates to the root Makefile for shared operations

# Agent configuration
AGENT_NAME := llm-release-radar
ROOT_DIR := $(shell cd ../.. && pwd)

# Include common variables and functions from root
include $(ROOT_DIR)/Makefile.common

# Default target
.DEFAULT_GOAL := help

# Colors for output
GREEN := \033[0;32m
BLUE := \033[0;34m
YELLOW := \033[1;33m
NC := \033[0m

help: ## Show agent-specific help
	@echo "$(BLUE)$(AGENT_NAME) Agent Commands$(NC)"
	@echo "Available targets:"
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make $(GREEN)<target>$(NC)\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2 } /^##@/ { printf "\n$(YELLOW)%s$(NC)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Development

setup: ## Install dependencies and set up environment
	@echo "$(BLUE)Setting up $(AGENT_NAME)...$(NC)"
	@cd $(ROOT_DIR) && $(MAKE) agent-setup AGENT=$(AGENT_NAME)

clean: ## Clean build artifacts and cache
	@echo "$(BLUE)Cleaning $(AGENT_NAME)...$(NC)"
	@cd $(ROOT_DIR) && $(MAKE) agent-clean AGENT=$(AGENT_NAME)

lint: ## Run code linting
	@echo "$(BLUE)Linting $(AGENT_NAME)...$(NC)"
	@cd $(ROOT_DIR) && $(MAKE) agent-lint AGENT=$(AGENT_NAME)

lint-fix: ## Fix linting issues
	@echo "$(BLUE)Fixing lint issues for $(AGENT_NAME)...$(NC)"
	@cd $(ROOT_DIR) && $(MAKE) agent-lint-fix AGENT=$(AGENT_NAME)

##@ Testing

test: ## Run all tests
	@echo "$(BLUE)Testing $(AGENT_NAME)...$(NC)"
	@cd $(ROOT_DIR) && $(MAKE) agent-test AGENT=$(AGENT_NAME)

test-unit: ## Run unit tests only
	@echo "$(BLUE)Running unit tests for $(AGENT_NAME)...$(NC)"
	@cd $(ROOT_DIR) && $(MAKE) agent-test-unit AGENT=$(AGENT_NAME)

test-integration: ## Run integration tests only
	@echo "$(BLUE)Running integration tests for $(AGENT_NAME)...$(NC)"
	@cd $(ROOT_DIR) && $(MAKE) agent-test-integration AGENT=$(AGENT_NAME)

test-e2e: ## Run end-to-end tests
	@echo "$(BLUE)Running e2e tests for $(AGENT_NAME)...$(NC)"
	@cd $(ROOT_DIR) && $(MAKE) agent-test-e2e AGENT=$(AGENT_NAME)

coverage: ## Generate test coverage report
	@echo "$(BLUE)Generating coverage for $(AGENT_NAME)...$(NC)"
	@cd $(ROOT_DIR) && $(MAKE) agent-coverage AGENT=$(AGENT_NAME)

##@ Build and Deploy

build: ## Build Docker image
	@echo "$(BLUE)Building $(AGENT_NAME)...$(NC)"
	@cd $(ROOT_DIR) && $(MAKE) agent-build AGENT=$(AGENT_NAME)

push: ## Push Docker image to registry
	@echo "$(BLUE)Pushing $(AGENT_NAME)...$(NC)"
	@cd $(ROOT_DIR) && $(MAKE) agent-push AGENT=$(AGENT_NAME)

deploy: ## Deploy to Kubernetes
	@echo "$(BLUE)Deploying $(AGENT_NAME)...$(NC)"
	@cd $(ROOT_DIR) && $(MAKE) agent-deploy AGENT=$(AGENT_NAME)

undeploy: ## Remove deployment from Kubernetes
	@echo "$(BLUE)Undeploying $(AGENT_NAME)...$(NC)"
	@cd $(ROOT_DIR) && $(MAKE) agent-undeploy AGENT=$(AGENT_NAME)

##@ Monitoring

status: ## Check deployment status
	@echo "$(BLUE)Status for $(AGENT_NAME)...$(NC)"
	@cd $(ROOT_DIR) && $(MAKE) agent-status AGENT=$(AGENT_NAME)

logs: ## Show application logs
	@echo "$(BLUE)Logs for $(AGENT_NAME)...$(NC)"
	@cd $(ROOT_DIR) && $(MAKE) agent-logs AGENT=$(AGENT_NAME)

shell: ## Open shell in running container
	@echo "$(BLUE)Opening shell for $(AGENT_NAME)...$(NC)"
	@cd $(ROOT_DIR) && $(MAKE) agent-shell AGENT=$(AGENT_NAME)

debug: ## Debug deployment issues
	@echo "$(BLUE)Debug info for $(AGENT_NAME)...$(NC)"
	@cd $(ROOT_DIR) && $(MAKE) debug-agent AGENT=$(AGENT_NAME)

restart: ## Restart the agent
	@echo "$(BLUE)Restarting $(AGENT_NAME)...$(NC)"
	@cd $(ROOT_DIR) && $(MAKE) restart-agent AGENT=$(AGENT_NAME)

##@ Development Tools

format: ## Format code
	@cd $(ROOT_DIR) && $(MAKE) agent-format AGENT=$(AGENT_NAME)

security-scan: ## Run security scan
	@cd $(ROOT_DIR) && $(MAKE) agent-security-scan AGENT=$(AGENT_NAME)

docs: ## Generate documentation
	@cd $(ROOT_DIR) && $(MAKE) agent-docs AGENT=$(AGENT_NAME)

##@ Local Development

dev-setup: setup ## Set up for local development
	@echo "$(GREEN)✓ Development environment ready for $(AGENT_NAME)$(NC)"
	@echo "Available commands:"
	@echo "  make lint     - Check code quality"
	@echo "  make test     - Run tests"
	@echo "  make build    - Build Docker image"
	@echo "  make deploy   - Deploy to Kubernetes"

dev-run: ## Run agent locally for development
	@echo "$(BLUE)Running $(AGENT_NAME) locally...$(NC)"
	@if [ -f .venv/bin/python ]; then \
		.venv/bin/python -m src.main; \
	else \
		echo "$(YELLOW)Virtual environment not found. Run 'make setup' first.$(NC)"; \
	fi

dev-test-watch: ## Run tests in watch mode
	@echo "$(BLUE)Running tests in watch mode for $(AGENT_NAME)...$(NC)"
	@if [ -f .venv/bin/pytest-watch ]; then \
		.venv/bin/ptw -- tests/; \
	else \
		echo "$(YELLOW)pytest-watch not installed. Install with: pip install pytest-watch$(NC)"; \
	fi

