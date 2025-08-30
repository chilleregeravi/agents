# Data Scraper Agent - Deployment Guide

## Prerequisites

### System Requirements

- Kubernetes cluster (version 1.21+)
- Raspberry Pi 5 or equivalent ARM64 hardware
- 4GB RAM minimum, 8GB recommended
- 20GB storage for data and logs
- Docker registry access (local or remote)

### Required External Services

- Target APIs for data scraping
- Container registry for custom images
- Storage solution for output data (optional)

## Pre-Deployment Setup

### 1. API Configuration

1. Identify target APIs for data scraping
2. Obtain API credentials and access tokens
3. Understand API rate limits and usage policies
4. Design data transformation requirements

### 2. Container Registry Setup

#### Local Registry (Recommended for Pi)

```bash
# Install and run local registry
docker run -d -p 5000:5000 --restart=always --name registry registry:2

# Configure Docker daemon to use insecure registry
echo '{"insecure-registries": ["localhost:5000"]}' | sudo tee /etc/docker/daemon.json
sudo systemctl restart docker
```

#### Remote Registry

Configure access to Docker Hub, GitHub Container Registry, or private registry.

### 3. Storage Configuration

#### Local Storage

```bash
# Create persistent volume for data storage
mkdir -p /data/data-scraper/output
mkdir -p /data/data-scraper/logs
chmod 755 /data/data-scraper/output
chmod 755 /data/data-scraper/logs
```

#### Cloud Storage (Optional)

Configure access to S3, GCS, or Azure Blob Storage for output data.

## Build and Push Images

### 1. Build Data Scraper Image

```bash
cd agents/data-scraper
make build

# Tag and push to registry
docker tag data-scraper:latest localhost:5000/data-scraper:latest
docker push localhost:5000/data-scraper:latest
```

### 2. Verify Image

```bash
# Test the image locally
docker run --rm localhost:5000/data-scraper:latest --help
```

## Kubernetes Deployment

### 1. Create Namespace

```bash
kubectl create namespace data-scraper
```

### 2. Configure Secrets

```bash
# Create API credentials secret
kubectl create secret generic api-credentials \
  --from-literal=github-token="your_github_token" \
  --from-literal=weather-api-key="your_weather_api_key" \
  --from-literal=api-username="your_username" \
  --from-literal=api-password="your_password" \
  -n data-scraper
```

### 3. Create ConfigMaps

#### API Configuration ConfigMap

```bash
# Create ConfigMap for API configurations
kubectl create configmap api-configs \
  --from-file=examples/config/apis/github-api.yaml \
  --from-file=examples/config/apis/weather-api.yaml \
  -n data-scraper
```

#### Example ConfigMap YAML

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: api-configs
  namespace: data-scraper
data:
  github-api.yaml: |
    name: "GitHub API Scraper"
    description: "Scrape GitHub user and repository data"
    base_url: "https://api.github.com"
    authentication:
      type: "bearer_token"
      bearer_token: "$GITHUB_TOKEN"
    endpoints:
      - name: "user_info"
        url: "/user"
        method: "GET"
      - name: "user_repos"
        url: "/user/repos"
        method: "GET"
        params:
          per_page: 100
    rate_limit:
      requests_per_minute: 30
      requests_per_hour: 5000
      delay_between_requests: 2.0
    data_format: "json"
    transformation:
      field_mapping:
        id: "user_id"
        name: "user_name"
      field_filters:
        user_name:
          type: "string"
          lowercase: true
      data_validation:
        user_id:
          required: true
          type: "number"
    output_config:
      format: "json"
      filename: "github_data"
    enabled: true
```

### 4. Deploy the Application

```bash
# Deploy using Kustomize
kubectl apply -k k8s/overlays/production

# Or deploy manually
kubectl apply -f k8s/base/deployment.yaml
kubectl apply -f k8s/base/service.yaml
kubectl apply -f k8s/base/configmap.yaml
```

### 5. Verify Deployment

```bash
# Check pod status
kubectl get pods -n data-scraper

# Check service
kubectl get svc -n data-scraper

# View logs
kubectl logs -f deployment/data-scraper -n data-scraper
```

## Configuration Management

### Environment Variables

The agent supports the following environment variables:

```bash
# API Credentials
GITHUB_TOKEN=your_github_token
OPENWEATHER_API_KEY=your_weather_api_key
API_USERNAME=your_username
API_PASSWORD=your_password

# Application Configuration
VERBOSE=false
LOG_LEVEL=INFO
CONFIG_PATH=/app/config
OUTPUT_PATH=/app/output
```

### Configuration Hot-Reloading

The agent supports configuration hot-reloading:

```bash
# Update ConfigMap
kubectl patch configmap api-configs \
  --patch '{"data":{"new-api.yaml":"..."}}' \
  -n data-scraper

# Restart deployment to pick up changes
kubectl rollout restart deployment/data-scraper -n data-scraper
```

## Monitoring and Logging

### 1. Log Aggregation

```bash
# View application logs
kubectl logs -f deployment/data-scraper -n data-scraper

# View logs with timestamps
kubectl logs -f deployment/data-scraper -n data-scraper --timestamps

# View logs for specific time range
kubectl logs deployment/data-scraper -n data-scraper --since=1h
```

### 2. Metrics Collection

```bash
# Enable metrics endpoint
kubectl patch deployment data-scraper \
  --patch '{"spec":{"template":{"spec":{"containers":[{"name":"data-scraper","ports":[{"containerPort":8080,"name":"metrics"}]}]}}}}' \
  -n data-scraper
```

### 3. Health Checks

```bash
# Check pod health
kubectl describe pod -l app=data-scraper -n data-scraper

# Check readiness
kubectl get endpoints data-scraper -n data-scraper
```

## Scaling and Performance

### 1. Horizontal Pod Autoscaling

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: data-scraper-hpa
  namespace: data-scraper
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: data-scraper
  minReplicas: 1
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### 2. Resource Limits

```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "250m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

### 3. Network Policies

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: data-scraper-network-policy
  namespace: data-scraper
spec:
  podSelector:
    matchLabels:
      app: data-scraper
  policyTypes:
  - Egress
  egress:
  - to: []
    ports:
    - protocol: TCP
      port: 443
    - protocol: TCP
      port: 80
```

## Backup and Recovery

### 1. Configuration Backup

```bash
# Backup ConfigMaps
kubectl get configmap api-configs -n data-scraper -o yaml > backup/configmap-backup.yaml

# Backup Secrets
kubectl get secret api-credentials -n data-scraper -o yaml > backup/secret-backup.yaml
```

### 2. Data Backup

```bash
# Backup output data
kubectl exec deployment/data-scraper -n data-scraper -- tar czf /tmp/output-backup.tar.gz /app/output
kubectl cp data-scraper/data-scraper-xxx:/tmp/output-backup.tar.gz ./backup/
```

### 3. Disaster Recovery

```bash
# Restore from backup
kubectl apply -f backup/configmap-backup.yaml
kubectl apply -f backup/secret-backup.yaml
kubectl rollout restart deployment/data-scraper -n data-scraper
```

## Troubleshooting

### Common Issues

#### 1. Pod Not Starting

```bash
# Check pod events
kubectl describe pod -l app=data-scraper -n data-scraper

# Check container logs
kubectl logs deployment/data-scraper -n data-scraper --previous
```

#### 2. Configuration Issues

```bash
# Validate configuration
kubectl exec deployment/data-scraper -n data-scraper -- python -m src.agent.main validate --config github-api

# Check ConfigMap
kubectl get configmap api-configs -n data-scraper -o yaml
```

#### 3. Authentication Issues

```bash
# Check secrets
kubectl get secret api-credentials -n data-scraper -o yaml

# Test API connectivity
kubectl exec deployment/data-scraper -n data-scraper -- curl -H "Authorization: Bearer $GITHUB_TOKEN" https://api.github.com/user
```

#### 4. Rate Limiting Issues

```bash
# Check rate limit headers
kubectl exec deployment/data-scraper -n data-scraper -- curl -I https://api.github.com/rate_limit

# Adjust rate limits in configuration
kubectl patch configmap api-configs --patch '{"data":{"github-api.yaml":"..."}}' -n data-scraper
```

### Debug Mode

```bash
# Enable debug logging
kubectl patch deployment data-scraper \
  --patch '{"spec":{"template":{"spec":{"containers":[{"name":"data-scraper","env":[{"name":"VERBOSE","value":"true"}]}]}}}}' \
  -n data-scraper
```

## Security Best Practices

### 1. RBAC Configuration

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: data-scraper
  name: data-scraper-role
rules:
- apiGroups: [""]
  resources: ["configmaps", "secrets"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: data-scraper-role-binding
  namespace: data-scraper
subjects:
- kind: ServiceAccount
  name: data-scraper
  namespace: data-scraper
roleRef:
  kind: Role
  name: data-scraper-role
  apiGroup: rbac.authorization.k8s.io
```

### 2. Pod Security Standards

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: data-scraper
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    fsGroup: 1000
  containers:
  - name: data-scraper
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
```

### 3. Network Security

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: data-scraper-network-policy
  namespace: data-scraper
spec:
  podSelector:
    matchLabels:
      app: data-scraper
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: monitoring
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to: []
    ports:
    - protocol: TCP
      port: 443
```

## Maintenance

### 1. Regular Updates

```bash
# Update image
docker pull localhost:5000/data-scraper:latest
kubectl set image deployment/data-scraper data-scraper=localhost:5000/data-scraper:latest -n data-scraper

# Update configuration
kubectl apply -f k8s/overlays/production -n data-scraper
```

### 2. Resource Cleanup

```bash
# Clean up old logs
kubectl exec deployment/data-scraper -n data-scraper -- find /app/logs -name "*.log" -mtime +7 -delete

# Clean up old output files
kubectl exec deployment/data-scraper -n data-scraper -- find /app/output -name "*.json" -mtime +30 -delete
```

### 3. Performance Monitoring

```bash
# Monitor resource usage
kubectl top pods -n data-scraper

# Monitor API rate limits
kubectl logs deployment/data-scraper -n data-scraper | grep "rate limit"

# Monitor error rates
kubectl logs deployment/data-scraper -n data-scraper | grep "ERROR"
```


