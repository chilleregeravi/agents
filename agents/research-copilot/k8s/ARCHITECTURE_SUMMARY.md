# Research Copilot Kubernetes Architecture Summary

## Overview

This document provides a comprehensive overview of the Research Copilot agent's Kubernetes deployment architecture, which follows the multi-agent development standards and is optimized for Raspberry Pi 5 deployment.

## Architecture Compliance

✅ **Standards Followed:**
- Multi-agent repository structure with centralized Makefile
- Kustomize-based deployment with environment overlays
- Security-first approach with least privilege RBAC
- Raspberry Pi 5 optimized resource limits
- HTTP-based health checks with proper endpoints
- Comprehensive monitoring and observability

## Makefile Structure

### Root Makefile (`/agents/Makefile`)
Contains all common targets that can be used across all agents:

```makefile
# Common development targets
setup, clean, lint, test, build, push, deploy

# Agent-specific internal targets (called by agent Makefiles)
agent-setup, agent-clean, agent-lint, agent-build, etc.

# Kustomize operations
install-kustomize, validate-kustomize, deploy-env

# Multi-agent operations
health-check, resource-usage, backup-configs
```

### Agent Makefile (`/agents/research-copilot/Makefile`)
Contains only agent-specific configuration and calls root Makefile:

```makefile
# Agent configuration
AGENT_NAME := research-copilot
K8S_NAMESPACE := research-copilot
ENVIRONMENT ?= production

# Agent-specific targets that call root Makefile
setup: @$(MAKE) -C ../.. agent-setup AGENT=$(AGENT_NAME)
build: @$(MAKE) -C ../.. agent-build AGENT=$(AGENT_NAME)

# Kustomize-specific operations
deploy-dev, deploy-staging, deploy-prod
validate-kustomize, dry-run, diff
```

## Kustomize Structure

### Base Configuration (`k8s/base/`)
```
base/
├── kustomization.yaml     # Base Kustomize configuration
├── namespace.yaml         # research-copilot namespace
├── service-account.yaml   # Service account with automount
├── rbac.yaml             # Role, RoleBinding, ClusterRole, ClusterRoleBinding
├── configmap.yaml        # Base application configuration
├── secrets.yaml          # Secret templates (update before deployment)
├── deployment.yaml       # Main application deployment
├── service.yaml          # ClusterIP service
└── cronjob.yaml          # Scheduled research jobs
```

### Environment Overlays (`k8s/overlays/`)
```
overlays/
├── development/          # Development environment
│   ├── kustomization.yaml
│   ├── deployment-patch.yaml    # Reduced resources, faster probes
│   └── configmap-patch.yaml     # Debug logging, no caching
├── staging/             # Staging environment  
│   ├── kustomization.yaml
│   ├── deployment-patch.yaml    # Moderate resources
│   └── configmap-patch.yaml     # Info logging, caching enabled
└── production/          # Production environment
    ├── kustomization.yaml
    ├── deployment-patch.yaml    # Full resources, monitoring
    ├── configmap-patch.yaml     # Optimized configuration
    └── cronjob-patch.yaml       # Production schedules
```

## Resource Specifications

### Development Environment
- **Memory**: 256Mi requests, 512Mi limits
- **CPU**: 100m requests, 250m limits
- **Features**: Debug logging, no caching, faster health checks
- **Prefix**: `dev-`

### Staging Environment  
- **Memory**: 512Mi requests, 1Gi limits
- **CPU**: 250m requests, 500m limits
- **Features**: Info logging, caching enabled
- **Prefix**: `staging-`

### Production Environment
- **Memory**: 512Mi requests, 1Gi limits  
- **CPU**: 250m requests, 500m limits
- **Features**: Optimized for Pi 5, monitoring enabled, scheduled jobs active
- **Prefix**: None

## Security Features

### Pod Security Context
```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  runAsGroup: 1000
  fsGroup: 1000
  seccompProfile:
    type: RuntimeDefault

# Container security
securityContext:
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    drop: [ALL]
```

### RBAC Permissions
- **Namespace-scoped**: ConfigMaps, Secrets, Pods, Services (read-only)
- **Event creation**: For logging purposes
- **Cluster-scoped**: Nodes, Namespaces (read-only for monitoring)

## Health Checks

### HTTP Endpoints
- **Liveness**: `GET /health` on port 8081
- **Readiness**: `GET /ready` on port 8081  
- **Startup**: `GET /health` on port 8081
- **Metrics**: `GET /metrics` on port 8080

### Probe Configuration
```yaml
# Production settings
livenessProbe:
  initialDelaySeconds: 60
  periodSeconds: 30
  timeoutSeconds: 10

readinessProbe:
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5

startupProbe:
  initialDelaySeconds: 10
  periodSeconds: 10
  failureThreshold: 30
```

## Scheduled Jobs

### Research Scheduler
- **Schedule**: Weekly on Sundays at 6:00 AM UTC (`0 6 * * 0`)
- **Purpose**: General LLM research using `llm-research-template`
- **Timeout**: 2 hours
- **Retry**: 2 attempts

### Tech Research Scheduler  
- **Schedule**: Monthly on the 1st at 8:00 AM UTC (`0 8 1 * *`)
- **Purpose**: Technology-focused research using `tech-research-template`
- **Timeout**: 2 hours
- **Retry**: 2 attempts

## Deployment Workflow

### Using Makefile (Recommended)
```bash
# Development
make deploy-dev

# Staging  
make deploy-staging

# Production
make deploy-prod

# With custom environment
make deploy ENVIRONMENT=production
```

### Using Deployment Script
```bash
# Interactive deployment with validation
./scripts/deploy.sh production

# Build and deploy
./scripts/deploy.sh development --build

# Validate only
./scripts/deploy.sh staging --validate

# Dry run
./scripts/deploy.sh production --dry-run
```

### Manual Kustomize
```bash
# Validate configuration
make validate-kustomize

# Deploy
kubectl create namespace research-copilot
kustomize build k8s/overlays/production | kubectl apply -f -
```

## Monitoring and Observability

### Prometheus Integration
- **Metrics endpoint**: `/metrics` on port 8080
- **Automatic scraping**: Configured via annotations
- **Custom metrics**: Application-specific metrics

### Logging
- **Structured logging**: JSON format with context
- **Log levels**: DEBUG (dev), INFO (staging/prod)
- **Centralized**: Kubernetes logs via `kubectl logs`

### Health Monitoring
```bash
# Check health
make health

# View metrics  
make metrics

# Resource usage
make top

# Events
make events
```

## Operational Commands

### Development Operations
```bash
make setup          # Set up development environment
make lint           # Run code linting  
make test           # Run tests
make build          # Build Docker image
make push           # Push to registry
```

### Deployment Operations
```bash
make deploy-prod    # Deploy to production
make status         # Check deployment status
make logs           # View application logs
make restart        # Restart deployment
make scale REPLICAS=2  # Scale deployment
```

### Maintenance Operations
```bash
make backup-config  # Backup configurations
make create-secrets # Create secrets
make port-forward   # Port forward for debugging
make shell          # Open shell in container
```

## File Locations

### Key Files
- **Root Makefile**: `/agents/Makefile`
- **Agent Makefile**: `/agents/research-copilot/Makefile`
- **Base Kustomize**: `/agents/research-copilot/k8s/base/kustomization.yaml`
- **Deployment Script**: `/agents/research-copilot/scripts/deploy.sh`

### Configuration Files
- **Base Config**: `/agents/research-copilot/k8s/base/configmap.yaml`
- **Dev Config**: `/agents/research-copilot/k8s/overlays/development/configmap-patch.yaml`
- **Prod Config**: `/agents/research-copilot/k8s/overlays/production/configmap-patch.yaml`

### Documentation
- **Deployment Guide**: `/agents/research-copilot/k8s/README.md`
- **Migration Guide**: `/agents/research-copilot/k8s/MIGRATION.md`
- **This Summary**: `/agents/research-copilot/k8s/ARCHITECTURE_SUMMARY.md`

## Best Practices Implemented

### Development
- ✅ Centralized common targets in root Makefile
- ✅ Agent-specific configuration only in agent Makefile
- ✅ Environment-specific configurations via Kustomize overlays
- ✅ Comprehensive validation and testing targets

### Security
- ✅ Non-root containers with specific UID/GID
- ✅ Read-only root filesystem with temporary volumes
- ✅ Minimal RBAC permissions (least privilege)
- ✅ Security contexts with seccomp profiles

### Operations
- ✅ HTTP-based health checks with proper endpoints
- ✅ Prometheus metrics integration
- ✅ Rolling updates with zero downtime
- ✅ Comprehensive logging and monitoring

### Resource Management
- ✅ Raspberry Pi 5 optimized resource limits
- ✅ Environment-specific resource allocation
- ✅ Efficient caching and async pool configurations
- ✅ Proper volume management for temporary files

This architecture provides a production-ready, secure, and maintainable deployment solution that follows all multi-agent development standards while being optimized for Raspberry Pi 5 constraints.

