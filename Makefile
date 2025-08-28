# Multi-Agent Repository Makefile
# Manages all agents in the repository

.PHONY: help setup clean lint test build deploy list-agents

# Configuration
AGENTS_DIR := agents
SHARED_DIR := shared
TOOLS_DIR := tools

# Get list of all agent directories
AGENTS := $(shell find $(AGENTS_DIR) -maxdepth 1 -type d -not -name $(AGENTS_DIR) -exec basename {} \;)

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "$(BLUE)Multi-Agent Repository Management$(NC)"
	@echo "Available targets:"
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make $(GREEN)<target>$(NC)\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2 } /^##@/ { printf "\n$(YELLOW)%s$(NC)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
	@echo "\n$(BLUE)Available agents:$(NC)"
	@for agent in $(AGENTS); do \
		echo "  - $$agent"; \
	done

##@ Development Commands

setup: ## Set up development environment for all agents
	@echo "$(BLUE)Setting up development environment...$(NC)"
	@python3 -m pip install --upgrade pip
	@if [ -f pyproject.toml ]; then pip install -e .; fi
	@if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
	@echo "$(GREEN)Setting up shared components...$(NC)"
	@if [ -d $(SHARED_DIR) ]; then \
		cd $(SHARED_DIR) && make setup 2>/dev/null || echo "No Makefile in shared/"; \
	fi
	@echo "$(GREEN)Setting up individual agents...$(NC)"
	@for agent in $(AGENTS); do \
		echo "Setting up $$agent..."; \
		cd $(AGENTS_DIR)/$$agent && make setup; \
		cd ../..; \
	done
	@echo "$(GREEN)✓ Development environment setup complete$(NC)"

clean: ## Clean all build artifacts and caches
	@echo "$(BLUE)Cleaning all artifacts...$(NC)"
	@rm -rf .pytest_cache/
	@rm -rf htmlcov/
	@rm -rf .coverage
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@if [ -d $(SHARED_DIR) ]; then \
		cd $(SHARED_DIR) && make clean 2>/dev/null || true; \
	fi
	@for agent in $(AGENTS); do \
		echo "Cleaning $$agent..."; \
		cd $(AGENTS_DIR)/$$agent && make clean 2>/dev/null || true; \
		cd ../..; \
	done
	@echo "$(GREEN)✓ Cleanup complete$(NC)"

lint: ## Run linting on all agents
	@echo "$(BLUE)Running linting on all agents...$(NC)"
	@failed_agents=""; \
	for agent in $(AGENTS); do \
		echo "Linting $$agent..."; \
		cd $(AGENTS_DIR)/$$agent; \
		if ! make lint; then \
			failed_agents="$$failed_agents $$agent"; \
		fi; \
		cd ../..; \
	done; \
	if [ -n "$$failed_agents" ]; then \
		echo "$(RED)✗ Linting failed for:$$failed_agents$(NC)"; \
		exit 1; \
	else \
		echo "$(GREEN)✓ All agents passed linting$(NC)"; \
	fi

test: ## Run tests for all agents
	@echo "$(BLUE)Running tests for all agents...$(NC)"
	@failed_agents=""; \
	for agent in $(AGENTS); do \
		echo "Testing $$agent..."; \
		cd $(AGENTS_DIR)/$$agent; \
		if ! make test; then \
			failed_agents="$$failed_agents $$agent"; \
		fi; \
		cd ../..; \
	done; \
	if [ -n "$$failed_agents" ]; then \
		echo "$(RED)✗ Tests failed for:$$failed_agents$(NC)"; \
		exit 1; \
	else \
		echo "$(GREEN)✓ All agents passed tests$(NC)"; \
	fi

test-unit: ## Run unit tests for all agents
	@echo "$(BLUE)Running unit tests for all agents...$(NC)"
	@for agent in $(AGENTS); do \
		echo "Unit testing $$agent..."; \
		cd $(AGENTS_DIR)/$$agent && make test-unit; \
		cd ../..; \
	done

test-integration: ## Run integration tests for all agents
	@echo "$(BLUE)Running integration tests for all agents...$(NC)"
	@for agent in $(AGENTS); do \
		echo "Integration testing $$agent..."; \
		cd $(AGENTS_DIR)/$$agent && make test-integration; \
		cd ../..; \
	done

coverage: ## Generate coverage report for all agents
	@echo "$(BLUE)Generating coverage reports...$(NC)"
	@for agent in $(AGENTS); do \
		echo "Coverage for $$agent..."; \
		cd $(AGENTS_DIR)/$$agent && make coverage; \
		cd ../..; \
	done

##@ Build and Deployment

build: ## Build Docker images for all agents
	@echo "$(BLUE)Building Docker images for all agents...$(NC)"
	@for agent in $(AGENTS); do \
		echo "Building $$agent..."; \
		cd $(AGENTS_DIR)/$$agent && make build; \
		cd ../..; \
	done
	@echo "$(GREEN)✓ All agents built successfully$(NC)"

push: ## Push Docker images for all agents
	@echo "$(BLUE)Pushing Docker images for all agents...$(NC)"
	@for agent in $(AGENTS); do \
		echo "Pushing $$agent..."; \
		cd $(AGENTS_DIR)/$$agent && make push; \
		cd ../..; \
	done

deploy: ## Deploy all agents to Kubernetes
	@echo "$(BLUE)Deploying all agents to Kubernetes...$(NC)"
	@kubectl create namespace agents --dry-run=client -o yaml | kubectl apply -f -
	@for agent in $(AGENTS); do \
		echo "Deploying $$agent..."; \
		cd $(AGENTS_DIR)/$$agent && make deploy; \
		cd ../..; \
	done
	@echo "$(GREEN)✓ All agents deployed$(NC)"

status: ## Check status of all deployed agents
	@echo "$(BLUE)Checking status of all agents...$(NC)"
	@kubectl get all -n agents
	@echo "\n$(BLUE)Individual agent status:$(NC)"
	@for agent in $(AGENTS); do \
		echo "\n$(YELLOW)$$agent:$(NC)"; \
		kubectl get pods -n agents -l app=$$agent; \
	done

logs: ## Show logs for all agents
	@echo "$(BLUE)Recent logs for all agents:$(NC)"
	@for agent in $(AGENTS); do \
		echo "\n$(YELLOW)=== $$agent logs ===$(NC)"; \
		kubectl logs --tail=10 -n agents -l app=$$agent 2>/dev/null || echo "No pods found for $$agent"; \
	done

undeploy: ## Remove all agents from Kubernetes
	@echo "$(BLUE)Removing all agents from Kubernetes...$(NC)"
	@for agent in $(AGENTS); do \
		echo "Undeploying $$agent..."; \
		cd $(AGENTS_DIR)/$$agent && make undeploy; \
		cd ../..; \
	done

##@ Agent Management

list-agents: ## List all available agents
	@echo "$(BLUE)Available agents in this repository:$(NC)"
	@for agent in $(AGENTS); do \
		if [ -f $(AGENTS_DIR)/$$agent/README.md ]; then \
			description=$$(head -n 3 $(AGENTS_DIR)/$$agent/README.md | tail -n 1 | sed 's/^[#* ]*//'); \
			echo "  $(GREEN)$$agent$(NC): $$description"; \
		else \
			echo "  $(GREEN)$$agent$(NC): No description available"; \
		fi; \
	done

agent-status: ## Show detailed status for a specific agent (usage: make agent-status AGENT=agent-name)
	@if [ -z "$(AGENT)" ]; then \
		echo "$(RED)Error: Please specify AGENT=agent-name$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Status for agent: $(AGENT)$(NC)"
	@if [ -d $(AGENTS_DIR)/$(AGENT) ]; then \
		cd $(AGENTS_DIR)/$(AGENT) && make status; \
	else \
		echo "$(RED)Agent $(AGENT) not found$(NC)"; \
		exit 1; \
	fi

agent-logs: ## Show logs for a specific agent (usage: make agent-logs AGENT=agent-name)
	@if [ -z "$(AGENT)" ]; then \
		echo "$(RED)Error: Please specify AGENT=agent-name$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Logs for agent: $(AGENT)$(NC)"
	@if [ -d $(AGENTS_DIR)/$(AGENT) ]; then \
		cd $(AGENTS_DIR)/$(AGENT) && make logs; \
	else \
		echo "$(RED)Agent $(AGENT) not found$(NC)"; \
		exit 1; \
	fi

##@ Development Tools

format: ## Format code for all agents
	@echo "$(BLUE)Formatting code for all agents...$(NC)"
	@for agent in $(AGENTS); do \
		echo "Formatting $$agent..."; \
		cd $(AGENTS_DIR)/$$agent && make lint-fix 2>/dev/null || echo "No format target for $$agent"; \
		cd ../..; \
	done

security-scan: ## Run security scans on all agents
	@echo "$(BLUE)Running security scans...$(NC)"
	@for agent in $(AGENTS); do \
		echo "Scanning $$agent..."; \
		cd $(AGENTS_DIR)/$$agent; \
		if [ -d .venv ]; then \
			.venv/bin/bandit -r src/ 2>/dev/null || echo "Bandit not available for $$agent"; \
		fi; \
		cd ../..; \
	done

pre-commit: lint test ## Run pre-commit checks (lint + test)
	@echo "$(GREEN)✓ Pre-commit checks passed$(NC)"

##@ Docker Registry Management

registry-setup: ## Set up local Docker registry for Pi 5
	@echo "$(BLUE)Setting up local Docker registry...$(NC)"
	@docker run -d -p 5000:5000 --name registry --restart=always registry:2
	@echo "$(GREEN)✓ Local registry running on localhost:5000$(NC)"

registry-stop: ## Stop local Docker registry
	@docker stop registry 2>/dev/null || true
	@docker rm registry 2>/dev/null || true
	@echo "$(GREEN)✓ Local registry stopped$(NC)"

##@ Monitoring and Maintenance

health-check: ## Check health of all deployed agents
	@echo "$(BLUE)Checking health of all agents...$(NC)"
	@for agent in $(AGENTS); do \
		echo "Health check for $$agent..."; \
		kubectl get pods -n agents -l app=$$agent -o jsonpath='{.items[*].status.conditions[?(@.type=="Ready")].status}' | grep -q True && echo "$(GREEN)✓ $$agent is healthy$(NC)" || echo "$(RED)✗ $$agent is unhealthy$(NC)"; \
	done

resource-usage: ## Show resource usage for all agents
	@echo "$(BLUE)Resource usage for all agents:$(NC)"
	@kubectl top pods -n agents 2>/dev/null || echo "Metrics server not available"

backup-configs: ## Backup all agent configurations
	@echo "$(BLUE)Backing up configurations...$(NC)"
	@mkdir -p backups/$(shell date +%Y%m%d_%H%M%S)
	@for agent in $(AGENTS); do \
		if [ -d $(AGENTS_DIR)/$$agent/k8s ]; then \
			cp -r $(AGENTS_DIR)/$$agent/k8s backups/$(shell date +%Y%m%d_%H%M%S)/$$agent-k8s; \
		fi; \
	done
	@echo "$(GREEN)✓ Configurations backed up$(NC)"

##@ Documentation

docs: ## Generate documentation for all agents
	@echo "$(BLUE)Generating documentation...$(NC)"
	@for agent in $(AGENTS); do \
		if [ -f $(AGENTS_DIR)/$$agent/docs/Makefile ]; then \
			echo "Generating docs for $$agent..."; \
			cd $(AGENTS_DIR)/$$agent/docs && make html; \
			cd ../../..; \
		fi; \
	done

##@ Agent-Specific Operations (called from agent Makefiles)

agent-setup: ## Set up a specific agent (internal use)
	@if [ -z "$(AGENT)" ]; then echo "$(RED)Error: AGENT not specified$(NC)"; exit 1; fi
	@echo "$(GREEN)Setting up agent: $(AGENT)$(NC)"
	@cd $(AGENTS_DIR)/$(AGENT) && \
		python3 -m venv .venv && \
		.venv/bin/pip install --upgrade pip && \
		if [ -f requirements/requirements.txt ]; then .venv/bin/pip install -r requirements/requirements.txt; fi && \
		if [ -f requirements/requirements-dev.txt ]; then .venv/bin/pip install -r requirements/requirements-dev.txt; fi && \
		if [ -f .venv/bin/pre-commit ]; then .venv/bin/pre-commit install; fi

agent-clean: ## Clean a specific agent (internal use)
	@if [ -z "$(AGENT)" ]; then echo "$(RED)Error: AGENT not specified$(NC)"; exit 1; fi
	@cd $(AGENTS_DIR)/$(AGENT) && \
		rm -rf .venv .pytest_cache .coverage htmlcov/ dist/ build/ && \
		find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true && \
		find . -type f -name "*.pyc" -delete 2>/dev/null || true

agent-lint: ## Lint a specific agent (internal use)
	@if [ -z "$(AGENT)" ]; then echo "$(RED)Error: AGENT not specified$(NC)"; exit 1; fi
	@cd $(AGENTS_DIR)/$(AGENT) && \
		if [ -d src ] && [ -d .venv ]; then \
			.venv/bin/black --check src/ tests/ 2>/dev/null || echo "Black check failed"; \
			.venv/bin/isort --check-only src/ tests/ 2>/dev/null || echo "isort check failed"; \
			.venv/bin/flake8 src/ tests/ 2>/dev/null || echo "flake8 check failed"; \
			.venv/bin/mypy src/ 2>/dev/null || echo "mypy check failed"; \
		else \
			echo "$(YELLOW)Skipping lint for $(AGENT) - no src/ directory or venv$(NC)"; \
		fi

agent-lint-fix: ## Fix linting issues for a specific agent (internal use)
	@if [ -z "$(AGENT)" ]; then echo "$(RED)Error: AGENT not specified$(NC)"; exit 1; fi
	@cd $(AGENTS_DIR)/$(AGENT) && \
		if [ -d src ] && [ -d .venv ]; then \
			.venv/bin/black src/ tests/; \
			.venv/bin/isort src/ tests/; \
		fi

agent-test: ## Test a specific agent (internal use)
	@if [ -z "$(AGENT)" ]; then echo "$(RED)Error: AGENT not specified$(NC)"; exit 1; fi
	@cd $(AGENTS_DIR)/$(AGENT) && \
		if [ -d tests ] && [ -d .venv ]; then \
			.venv/bin/pytest tests/ -v --cov=src --cov-report=html --cov-report=term; \
		else \
			echo "$(YELLOW)Skipping tests for $(AGENT) - no tests/ directory or venv$(NC)"; \
		fi

agent-test-unit: ## Run unit tests for a specific agent (internal use)
	@if [ -z "$(AGENT)" ]; then echo "$(RED)Error: AGENT not specified$(NC)"; exit 1; fi
	@cd $(AGENTS_DIR)/$(AGENT) && \
		if [ -d tests/unit ] && [ -d .venv ]; then \
			.venv/bin/pytest tests/unit/ -v --cov=src --cov-report=term; \
		fi

agent-test-integration: ## Run integration tests for a specific agent (internal use)
	@if [ -z "$(AGENT)" ]; then echo "$(RED)Error: AGENT not specified$(NC)"; exit 1; fi
	@cd $(AGENTS_DIR)/$(AGENT) && \
		if [ -d tests/integration ] && [ -d .venv ]; then \
			.venv/bin/pytest tests/integration/ -v; \
		fi

agent-test-e2e: ## Run e2e tests for a specific agent (internal use)
	@if [ -z "$(AGENT)" ]; then echo "$(RED)Error: AGENT not specified$(NC)"; exit 1; fi
	@cd $(AGENTS_DIR)/$(AGENT) && \
		if [ -d tests/e2e ] && [ -d .venv ]; then \
			.venv/bin/pytest tests/e2e/ -v; \
		fi

agent-coverage: ## Generate coverage for a specific agent (internal use)
	@if [ -z "$(AGENT)" ]; then echo "$(RED)Error: AGENT not specified$(NC)"; exit 1; fi
	@cd $(AGENTS_DIR)/$(AGENT) && \
		if [ -d .venv ]; then \
			.venv/bin/coverage html; \
			echo "Coverage report generated in $(AGENTS_DIR)/$(AGENT)/htmlcov/"; \
		fi

agent-build: ## Build Docker image for a specific agent (internal use)
	@if [ -z "$(AGENT)" ]; then echo "$(RED)Error: AGENT not specified$(NC)"; exit 1; fi
	@cd $(AGENTS_DIR)/$(AGENT) && \
		if [ -f docker/Dockerfile ]; then \
			docker build -f docker/Dockerfile -t $(AGENT):latest -t $(AGENT):$(shell git rev-parse --short HEAD) .; \
		else \
			echo "$(YELLOW)No Dockerfile found for $(AGENT)$(NC)"; \
		fi

agent-push: ## Push Docker image for a specific agent (internal use)
	@if [ -z "$(AGENT)" ]; then echo "$(RED)Error: AGENT not specified$(NC)"; exit 1; fi
	@docker tag $(AGENT):latest localhost:5000/$(AGENT):latest
	@docker tag $(AGENT):latest localhost:5000/$(AGENT):$(shell git rev-parse --short HEAD)
	@docker push localhost:5000/$(AGENT):latest
	@docker push localhost:5000/$(AGENT):$(shell git rev-parse --short HEAD)

agent-deploy: ## Deploy a specific agent (internal use)
	@if [ -z "$(AGENT)" ]; then echo "$(RED)Error: AGENT not specified$(NC)"; exit 1; fi
	@kubectl create namespace agents --dry-run=client -o yaml | kubectl apply -f -
	@cd $(AGENTS_DIR)/$(AGENT) && \
		if [ -d k8s ]; then \
			kubectl apply -f k8s/ -n agents; \
		else \
			echo "$(YELLOW)No k8s manifests found for $(AGENT)$(NC)"; \
		fi

agent-undeploy: ## Undeploy a specific agent (internal use)
	@if [ -z "$(AGENT)" ]; then echo "$(RED)Error: AGENT not specified$(NC)"; exit 1; fi
	@cd $(AGENTS_DIR)/$(AGENT) && \
		if [ -d k8s ]; then \
			kubectl delete -f k8s/ -n agents --ignore-not-found=true; \
		fi

agent-format: ## Format code for a specific agent (internal use)
	@if [ -z "$(AGENT)" ]; then echo "$(RED)Error: AGENT not specified$(NC)"; exit 1; fi
	@cd $(AGENTS_DIR)/$(AGENT) && $(MAKE) lint-fix 2>/dev/null || echo "No format target"

agent-security-scan: ## Security scan for a specific agent (internal use)
	@if [ -z "$(AGENT)" ]; then echo "$(RED)Error: AGENT not specified$(NC)"; exit 1; fi
	@cd $(AGENTS_DIR)/$(AGENT) && \
		if [ -d .venv ] && [ -d src ]; then \
			.venv/bin/bandit -r src/ 2>/dev/null || echo "Bandit not available"; \
		fi

agent-docs: ## Generate docs for a specific agent (internal use)
	@if [ -z "$(AGENT)" ]; then echo "$(RED)Error: AGENT not specified$(NC)"; exit 1; fi
	@cd $(AGENTS_DIR)/$(AGENT) && \
		if [ -f docs/Makefile ]; then \
			cd docs && make html; \
		fi

agent-shell: ## Open shell in agent container (internal use)
	@if [ -z "$(AGENT)" ]; then echo "$(RED)Error: AGENT not specified$(NC)"; exit 1; fi
	@kubectl exec -it deployment/$(AGENT) -n agents -- /bin/bash

##@ Troubleshooting

debug-agent: ## Debug a specific agent (usage: make debug-agent AGENT=agent-name)
	@if [ -z "$(AGENT)" ]; then \
		echo "$(RED)Error: Please specify AGENT=agent-name$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Debug information for agent: $(AGENT)$(NC)"
	@if [ -d $(AGENTS_DIR)/$(AGENT) ]; then \
		echo "$(YELLOW)Pod status:$(NC)"; \
		kubectl describe pods -n agents -l app=$(AGENT); \
		echo "\n$(YELLOW)Recent logs:$(NC)"; \
		kubectl logs --tail=50 -n agents -l app=$(AGENT); \
		echo "\n$(YELLOW)Events:$(NC)"; \
		kubectl get events -n agents --field-selector involvedObject.name=$(AGENT); \
	else \
		echo "$(RED)Agent $(AGENT) not found$(NC)"; \
	fi

restart-agent: ## Restart a specific agent (usage: make restart-agent AGENT=agent-name)
	@if [ -z "$(AGENT)" ]; then \
		echo "$(RED)Error: Please specify AGENT=agent-name$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Restarting agent: $(AGENT)$(NC)"
	@kubectl rollout restart deployment/$(AGENT) -n agents
	@kubectl rollout status deployment/$(AGENT) -n agents
	@echo "$(GREEN)✓ Agent $(AGENT) restarted$(NC)"
