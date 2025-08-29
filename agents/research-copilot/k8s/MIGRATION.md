# Migration Guide: Legacy Manifests to Kustomize

This guide helps you migrate from the legacy Kubernetes manifests to the new Kustomize-based deployment structure.

## Overview

The new deployment structure provides:
- **Environment-specific configurations** using Kustomize overlays
- **Improved security** with proper RBAC and security contexts
- **Better resource management** optimized for Raspberry Pi 5
- **Standardized deployment process** following architecture rules
- **Enhanced monitoring** with proper health checks and metrics

## Changes Summary

### Architecture Improvements

| Component | Legacy | New Kustomize | Improvements |
|-----------|---------|---------------|--------------|
| **Namespace** | `agents` | `research-copilot` | Dedicated namespace per agent |
| **Health Checks** | Exec-based | HTTP-based | Proper `/health` and `/ready` endpoints |
| **Resource Limits** | High (2Gi/1000m) | Optimized (1Gi/500m) | Pi 5 optimized |
| **Security Context** | Basic | Enhanced | Read-only filesystem, seccomp profile |
| **Image Management** | Fixed tags | Kustomize managed | Environment-specific tags |
| **Configuration** | Single ConfigMap | Environment overlays | Dev/staging/prod variants |

### File Structure Changes

```
OLD STRUCTURE:
k8s/
├── deployment.yaml
├── deployment-simplified.yaml
├── service.yaml
├── configmap.yaml
├── secrets.yaml
├── namespace.yaml
├── rbac.yaml
├── service-account.yaml
├── cronjob.yaml
└── configmaps/
    ├── llm-research-template.yaml
    ├── market-research-template.yaml
    └── tech-research-template.yaml

NEW STRUCTURE:
k8s/
├── base/                    # Base configuration
│   ├── kustomization.yaml
│   ├── namespace.yaml
│   ├── service-account.yaml
│   ├── rbac.yaml
│   ├── configmap.yaml
│   ├── secrets.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── cronjob.yaml
│   └── configmaps/
│       ├── llm-research-template.yaml
│       ├── market-research-template.yaml
│       └── tech-research-template.yaml
├── overlays/               # Environment-specific
│   ├── development/
│   ├── staging/
│   └── production/
├── README.md
├── MIGRATION.md
└── ARCHITECTURE_SUMMARY.md
```

## Migration Steps

### Step 1: Backup Current Deployment

```bash
# Create backup directory
mkdir -p backups/pre-migration-$(date +%Y%m%d)

# Backup current resources
kubectl get all -n research-copilot -o yaml > backups/pre-migration-$(date +%Y%m%d)/resources.yaml
kubectl get configmaps -n research-copilot -o yaml > backups/pre-migration-$(date +%Y%m%d)/configmaps.yaml
kubectl get secrets -n research-copilot -o yaml > backups/pre-migration-$(date +%Y%m%d)/secrets.yaml
```

### Step 2: Undeploy Legacy Resources

```bash
# If using old namespace 'agents'
kubectl delete namespace agents

# If using 'research-copilot' namespace
kubectl delete -f k8s/deployment.yaml
kubectl delete -f k8s/service.yaml
kubectl delete -f k8s/cronjob.yaml
kubectl delete -f k8s/rbac.yaml
kubectl delete -f k8s/service-account.yaml
kubectl delete -f k8s/configmap.yaml
kubectl delete -f k8s/secrets.yaml
```

### Step 3: Prepare Environment

```bash
# Set required environment variables
export NOTION_TOKEN="your_notion_integration_token"
export NOTION_DATABASE_ID="your_notion_database_id"
export SERPAPI_KEY="your_serpapi_key"  # Optional
export BING_API_KEY="your_bing_api_key"  # Optional
export BING_ENDPOINT="https://api.bing.microsoft.com/v7.0/search"  # Optional
```

### Step 4: Deploy Using New Structure

```bash
# Option 1: Using the deployment script (recommended)
./scripts/deploy.sh production

# Option 2: Using Makefile
make deploy-prod

# Option 3: Manual Kustomize deployment
kubectl create namespace research-copilot
kustomize build k8s/overlays/production | kubectl apply -f -
```

### Step 5: Verify Migration

```bash
# Check deployment status
make status

# Verify health endpoints
make health

# Check logs
make logs

# Test functionality
make port-forward
# In another terminal:
curl http://localhost:8081/health
curl http://localhost:8080/metrics
```

## Configuration Migration

### Environment Variables

| Legacy Variable | New Variable | Notes |
|----------------|--------------|-------|
| `LLM_URL` | `LLM_URL` | Updated to use FQDN |
| `NOTION_TOKEN` | `NOTION_TOKEN` | Same |
| `NOTION_DATABASE_ID` | `NOTION_DATABASE_ID` | Same |
| `LOG_LEVEL` | `LOG_LEVEL` | Environment-specific |
| `ENVIRONMENT` | `ENVIRONMENT` | Environment-specific |

### Resource Limits Migration

| Environment | Legacy | New | Change |
|-------------|---------|-----|--------|
| **Memory Request** | 1Gi | 512Mi | -50% (Pi 5 optimized) |
| **Memory Limit** | 2Gi | 1Gi | -50% (Pi 5 optimized) |
| **CPU Request** | 500m | 250m | -50% (Pi 5 optimized) |
| **CPU Limit** | 1000m | 500m | -50% (Pi 5 optimized) |

### Health Check Migration

```yaml
# Legacy (exec-based)
livenessProbe:
  exec:
    command:
    - python
    - -c
    - |
      # Complex Python health check

# New (HTTP-based)
livenessProbe:
  httpGet:
    path: /health
    port: health
  initialDelaySeconds: 60
  periodSeconds: 30
```

## Troubleshooting Migration Issues

### Common Issues

1. **Namespace Conflicts**
   ```bash
   # If old namespace still exists
   kubectl delete namespace agents
   kubectl delete namespace research-copilot
   # Then redeploy
   ```

2. **Secret Migration**
   ```bash
   # Extract secrets from old deployment
   kubectl get secret api-credentials -n agents -o yaml > old-secrets.yaml
   # Edit and apply to new namespace
   ```

3. **ConfigMap Migration**
   ```bash
   # Compare old and new configurations
   kubectl get configmap research-copilot-config -n agents -o yaml
   # Adjust overlay configurations as needed
   ```

4. **Image Issues**
   ```bash
   # Rebuild and push image
   make build push
   ```

5. **Health Check Failures**
   ```bash
   # Check if application provides /health endpoint
   kubectl port-forward svc/research-copilot-service -n research-copilot 8081:8081
   curl http://localhost:8081/health
   ```

### Rollback Procedure

If migration fails, rollback to legacy deployment:

```bash
# Remove new deployment
make undeploy

# Restore from backup
kubectl apply -f backups/pre-migration-$(date +%Y%m%d)/

# Or redeploy legacy manifests
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/rbac.yaml
kubectl apply -f k8s/service-account.yaml
kubectl apply -f k8s/cronjob.yaml
```

## Validation Checklist

After migration, verify:

- [ ] All pods are running and ready
- [ ] Health endpoints respond correctly
- [ ] Metrics are available
- [ ] Scheduled jobs are created
- [ ] RBAC permissions are working
- [ ] Secrets are properly mounted
- [ ] ConfigMaps are applied correctly
- [ ] Service discovery works
- [ ] Resource limits are appropriate
- [ ] Security context is applied

## Benefits of New Structure

### Development Workflow
- **Environment Parity**: Consistent deployment across dev/staging/prod
- **Easy Testing**: Quick deployment to development environment
- **Configuration Management**: Clear separation of environment-specific settings

### Operations
- **Monitoring**: Built-in Prometheus metrics and health checks
- **Scaling**: Easy replica management
- **Debugging**: Better logging and debugging capabilities
- **Security**: Enhanced security context and RBAC

### Maintenance
- **Updates**: Rolling updates with zero downtime
- **Backup**: Automated configuration backup
- **Rollback**: Easy rollback to previous versions
- **Documentation**: Comprehensive deployment documentation

## Next Steps

After successful migration:

1. **Set up monitoring** for the new deployment
2. **Configure alerts** for health check failures
3. **Schedule regular backups** using `make backup-config`
4. **Review resource usage** and adjust limits if needed
5. **Update CI/CD pipelines** to use new deployment structure
6. **Train team members** on new deployment procedures

## Support

For issues during migration:

1. Check the troubleshooting section above
2. Review logs: `make logs`
3. Check events: `make events`
4. Validate configuration: `make validate-kustomize`
5. Use dry-run: `make dry-run`

Remember to test the migration in a development environment first before applying to production!
