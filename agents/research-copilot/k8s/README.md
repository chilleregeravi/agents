# Research Copilot Kubernetes Deployment

This directory contains Kubernetes manifests for deploying the Research Copilot agent using Kustomize. The deployment follows the multi-agent architecture standards and is optimized for Raspberry Pi 5 deployment.

## Architecture Overview

The Research Copilot agent is deployed with the following components:

- **Deployment**: Main agent application with health checks and monitoring
- **Service**: ClusterIP service for internal communication
- **ConfigMap**: Configuration settings for the agent
- **Secret**: API credentials and sensitive configuration
- **ServiceAccount & RBAC**: Security permissions following least privilege principle
- **CronJob**: Scheduled research tasks (weekly LLM research, monthly tech research)

## Directory Structure

```
k8s/
├── base/                          # Base Kustomize configuration
│   ├── kustomization.yaml         # Base Kustomize file
│   ├── namespace.yaml             # Namespace definition
│   ├── service-account.yaml       # Service account
│   ├── rbac.yaml                  # RBAC permissions
│   ├── configmap.yaml             # Base configuration
│   ├── secrets.yaml               # Secret templates
│   ├── deployment.yaml            # Main deployment
│   ├── service.yaml               # Service definition
│   ├── cronjob.yaml               # Scheduled jobs
│   └── configmaps/                # Research template ConfigMaps
│       ├── llm-research-template.yaml
│       ├── market-research-template.yaml
│       └── tech-research-template.yaml
├── overlays/                      # Environment-specific overlays
│   ├── development/               # Development environment
│   │   ├── kustomization.yaml
│   │   ├── deployment-patch.yaml
│   │   └── configmap-patch.yaml
│   ├── staging/                   # Staging environment
│   │   ├── kustomization.yaml
│   │   ├── deployment-patch.yaml
│   │   └── configmap-patch.yaml
│   └── production/                # Production environment
│       ├── kustomization.yaml
│       ├── deployment-patch.yaml
│       ├── configmap-patch.yaml
│       └── cronjob-patch.yaml
├── README.md                      # This file
├── MIGRATION.md                   # Migration guide
└── ARCHITECTURE_SUMMARY.md        # Architecture overview
```

## Prerequisites

1. **Kubernetes Cluster**: Running Kubernetes cluster (k3s, minikube, or full cluster)
2. **Kustomize**: Install Kustomize v5.0.0 or later
3. **kubectl**: Configured to access your cluster
4. **Docker Registry**: Local registry at `localhost:5000` for images
5. **Ollama Service**: LLM service running in the cluster

### Installing Prerequisites

```bash
# Install Kustomize (automated via Makefile)
make install-kustomize

# Verify kubectl access
kubectl cluster-info

# Check if local registry is running
curl -X GET http://localhost:5000/v2/_catalog
```

## Configuration

### Environment Variables

Before deployment, set the following environment variables:

```bash
# Required secrets
export NOTION_TOKEN="your_notion_integration_token"
export NOTION_DATABASE_ID="your_notion_database_id"

# Optional API keys
export SERPAPI_KEY="your_serpapi_key"
export BING_API_KEY="your_bing_api_key"
export BING_ENDPOINT="https://api.bing.microsoft.com/v7.0/search"
```

### Customizing Configuration

Each environment has its own configuration overlay:

#### Development Environment
- Reduced resource limits (256Mi/100m requests, 512Mi/250m limits)
- Debug logging enabled
- Caching disabled
- Faster health check intervals

#### Staging Environment
- Moderate resource limits (512Mi/250m requests, 1Gi/500m limits)
- Info logging
- Caching enabled
- Production-like configuration

#### Production Environment
- Full resource limits (512Mi/250m requests, 1Gi/500m limits)
- Optimized for Raspberry Pi 5
- Monitoring enabled
- Scheduled jobs active

## Deployment

### Quick Start

1. **Build and push the Docker image**:
   ```bash
   make build push
   ```

2. **Create secrets**:
   ```bash
   make create-secrets
   ```

3. **Deploy to production**:
   ```bash
   make deploy-prod
   ```

### Environment-Specific Deployment

```bash
# Development environment
make deploy-dev

# Staging environment
make deploy-staging

# Production environment
make deploy-prod
```

### Manual Deployment with Kustomize

```bash
# Validate configuration
make validate-kustomize

# Deploy to production
kubectl create namespace research-copilot
kustomize build k8s/overlays/production | kubectl apply -f -

# Deploy to development
kustomize build k8s/overlays/development | kubectl apply -f -
```

## Operations

### Monitoring Deployment

```bash
# Check deployment status
make status

# View logs
make logs

# Check health endpoints
make health

# View metrics
make metrics
```

### Scaling

```bash
# Scale to 2 replicas
make scale REPLICAS=2

# Scale back to 1 replica
make scale REPLICAS=1
```

### Troubleshooting

```bash
# Describe resources
make describe

# View recent events
make events

# Get shell access
make shell

# Port forward for local access
make port-forward
```

### Managing Secrets

```bash
# Create new secrets
make create-secrets

# Update existing secrets
make update-secrets
```

## Security Features

### Pod Security
- Runs as non-root user (UID 1000)
- Read-only root filesystem
- No privileged escalation
- Drops all capabilities
- Security context with seccomp profile

### RBAC Permissions
- Minimal required permissions
- Namespace-scoped access to ConfigMaps and Secrets
- Limited cluster-level access for node information
- Event creation for logging

### Network Security
- ClusterIP service (no external exposure)
- Internal service discovery
- TLS-ready configuration

## Resource Optimization

### Raspberry Pi 5 Specific Optimizations
- ARM64 compatible images
- Memory limits designed for 8GB RAM constraint
- CPU limits optimized for ARM Cortex-A76
- Reduced async pool sizes
- Efficient caching configuration

### Resource Limits by Environment

| Environment | Memory Request | Memory Limit | CPU Request | CPU Limit |
|-------------|----------------|--------------|-------------|-----------|
| Development | 256Mi          | 512Mi        | 100m        | 250m      |
| Staging     | 512Mi          | 1Gi          | 250m        | 500m      |
| Production  | 512Mi          | 1Gi          | 250m        | 500m      |

## Health Checks

### Endpoints
- **Liveness Probe**: `GET /health` on port 8081
- **Readiness Probe**: `GET /ready` on port 8081
- **Startup Probe**: `GET /health` on port 8081

### Monitoring
- **Metrics**: Available at `/metrics` on port 8080
- **Prometheus**: Automatic scraping configured
- **Health Status**: Real-time health monitoring

## Scheduled Jobs

### Research Scheduler
- **Schedule**: Weekly on Sundays at 6:00 AM UTC
- **Purpose**: Run general LLM research
- **Timeout**: 2 hours
- **Retry**: 2 attempts

### Tech Research Scheduler
- **Schedule**: Monthly on the 1st at 8:00 AM UTC
- **Purpose**: Run technology-focused research
- **Timeout**: 2 hours
- **Retry**: 2 attempts

## Backup and Recovery

### Configuration Backup
```bash
# Backup current configuration
make backup-config
```

### Recovery Process
1. Restore from backup files
2. Apply configuration: `kubectl apply -f backups/TIMESTAMP/`
3. Verify deployment: `make status`

## Troubleshooting Guide

### Common Issues

1. **Pod CrashLoopBackOff**
   ```bash
   # Check logs
   make logs
   
   # Check events
   make events
   
   # Verify secrets
   kubectl get secrets -n research-copilot
   ```

2. **Health Check Failures**
   ```bash
   # Check health endpoints
   make health
   
   # Port forward and test locally
   make port-forward
   curl http://localhost:8081/health
   ```

3. **Resource Issues**
   ```bash
   # Check resource usage
   make top
   
   # Check node resources
   kubectl describe nodes
   ```

4. **Image Pull Issues**
   ```bash
   # Verify registry access
   curl -X GET http://localhost:5000/v2/_catalog
   
   # Check image tags
   docker images | grep research-copilot
   ```

### Debugging Commands

```bash
# Get detailed pod information
kubectl describe pod -l app=research-copilot -n research-copilot

# Check service endpoints
kubectl get endpoints -n research-copilot

# View resource quotas
kubectl describe resourcequotas -n research-copilot

# Check network policies
kubectl get networkpolicies -n research-copilot
```

## Maintenance

### Regular Tasks
1. **Update secrets** when API keys rotate
2. **Monitor resource usage** to optimize limits
3. **Review logs** for errors and performance issues
4. **Update configurations** as requirements change
5. **Backup configurations** before major changes

### Upgrade Process
1. Build new image version
2. Update image tag in Kustomize overlay
3. Validate configuration
4. Deploy with rolling update
5. Verify deployment health

## Integration with CI/CD

The Makefile provides targets that integrate with CI/CD pipelines:

```bash
# In CI/CD pipeline
make lint test build push validate-kustomize deploy-prod
```

## Support and Documentation

- **Architecture Rules**: See `/.cursor/rules` for development standards
- **Agent Documentation**: See `/docs` directory for agent-specific docs
- **Kubernetes Documentation**: https://kubernetes.io/docs/
- **Kustomize Documentation**: https://kustomize.io/
