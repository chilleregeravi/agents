# Research Copilot Agent - Deployment Guide

## Prerequisites

### System Requirements

- Kubernetes cluster (version 1.21+)
- Raspberry Pi 5 or equivalent ARM64 hardware
- 8GB RAM minimum, 16GB recommended
- 50GB storage for models and data
- Docker registry access (local or remote)

### Required External Services

- Notion workspace with API integration
- Search API provider (SerpAPI or Bing Search API)
- Container registry for custom images

## Pre-Deployment Setup

### 1. Notion Configuration

1. Create a Notion integration at <https://developers.notion.com/>
2. Create a database in your Notion workspace
3. Share the database with your integration
4. Note the integration token and database ID

### 2. Search API Configuration

#### Option A: SerpAPI

1. Sign up at <https://serpapi.com/>
2. Obtain API key from dashboard
3. Note the API key for secrets configuration

#### Option B: Bing Search API

1. Create Azure Cognitive Services account
2. Create Bing Search v7 resource
3. Obtain API key and endpoint
4. Note the credentials for secrets configuration

### 3. Container Registry Setup

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

## Build and Push Images

### 1. Build Research Agent Image

```bash
cd agents/research-copilot
make build

# Tag and push to registry
docker tag research-copilot:latest localhost:5000/research-copilot:latest
docker push localhost:5000/research-copilot:latest
```

### 2. Prepare Ollama Server Image

```bash
# Pull and customize Ollama image for ARM64
docker pull ollama/ollama:latest
docker tag ollama/ollama:latest localhost:5000/ollama:latest
docker push localhost:5000/ollama:latest
```

## Kubernetes Deployment

### 1. Create Namespace

```bash
kubectl apply -f k8s/namespace.yaml
```

### 2. Configure Secrets

```bash
# Create API credentials secret
kubectl create secret generic api-credentials \
  --from-literal=notion-token="your_notion_integration_token" \
  --from-literal=notion-database-id="your_database_id" \
  --from-literal=serpapi-key="your_serpapi_key" \
  --from-literal=bing-api-key="your_bing_api_key" \
  --from-literal=bing-endpoint="your_bing_endpoint" \
  -n research-copilot

# Create LLM configuration secret
kubectl create secret generic llm-config \
  --from-literal=ollama-url="http://ollama-service:11434" \
  --from-literal=model-name="qwen2.5:7b" \
  -n research-copilot
```

### 3. Deploy ConfigMaps

```bash
# Apply research configuration templates
kubectl apply -f k8s/configmaps/
```

### 4. Deploy Core Services

```bash
# Deploy in order
kubectl apply -f k8s/service-account.yaml
kubectl apply -f k8s/rbac.yaml
kubectl apply -f k8s/persistent-volume.yaml
kubectl apply -f k8s/ollama-deployment.yaml
kubectl apply -f k8s/ollama-service.yaml

# Wait for Ollama to be ready
kubectl wait --for=condition=ready pod -l app=ollama-server -n research-copilot --timeout=300s

# Deploy research agent
kubectl apply -f k8s/research-agent-deployment.yaml
kubectl apply -f k8s/research-agent-service.yaml
```

### 5. Deploy Scheduling

```bash
# Deploy CronJob for automated research
kubectl apply -f k8s/cronjob.yaml
```

## Configuration Management

### Research Configuration Templates

The system includes several pre-built research templates:

#### Technology Research Template

```yaml
# k8s/configmaps/tech-research-template.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: tech-research-template
  namespace: research-copilot
data:
  research_prompt.yaml: |
    research_request:
      topic:
        name: "Technology Research"
        description: "Comprehensive analysis of emerging technology trends"
        keywords: ["AI", "machine learning", "blockchain", "cloud computing"]
        focus_areas: ["innovations", "market impact", "adoption trends"]
        time_range: "past_month"
        depth: "detailed"
      search_strategy:
        max_sources: 20
        source_types: ["news", "research_papers", "blogs", "official_announcements"]
        credibility_threshold: 0.7
      analysis_instructions: |
        Analyze the collected information to identify:
        1. Key technological breakthroughs and innovations
        2. Market trends and adoption patterns
        3. Industry impact and future implications
        4. Competitive landscape changes
        
        Provide detailed analysis with supporting evidence and credible sources.
  
  output_schema.yaml: |
    output_format:
      type: "notion_page"
      template: "research_report"
    
    page_structure:
      title_template: "Technology Research Report - {topic_name} - {date}"
      sections:
        - name: "Executive Summary"
          type: "text_block"
          content_source: "summary"
          configuration:
            max_length: 500
            include_key_points: true
        
        - name: "Key Findings"
          type: "bullet_list"
          content_source: "findings"
          configuration:
            max_items: 10
            include_sources: true
        
        - name: "Detailed Analysis"
          type: "toggle_blocks"
          content_source: "analysis"
          configuration:
            group_by: "category"
            include_confidence_scores: true
        
        - name: "Sources"
          type: "table"
          content_source: "sources"
          configuration:
            columns: ["Title", "URL", "Credibility", "Date"]
            sort_by: "credibility"
    
    content_processing:
      summary_length: "detailed"
      include_confidence_scores: true
      group_similar_findings: true
```

#### Market Research Template

```yaml
# k8s/configmaps/market-research-template.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: market-research-template
  namespace: research-copilot
data:
  research_prompt.yaml: |
    research_request:
      topic:
        name: "Market Research"
        description: "Market analysis and competitive intelligence"
        keywords: ["market size", "competition", "growth trends", "consumer behavior"]
        focus_areas: ["market dynamics", "competitive analysis", "opportunities"]
        time_range: "past_quarter"
        depth: "comprehensive"
      search_strategy:
        max_sources: 25
        source_types: ["market_reports", "financial_news", "industry_analysis", "surveys"]
        credibility_threshold: 0.8
      analysis_instructions: |
        Conduct comprehensive market analysis focusing on:
        1. Market size, growth, and segmentation
        2. Competitive landscape and key players
        3. Consumer trends and preferences
        4. Market opportunities and threats
        5. Financial performance and projections
        
        Provide quantitative data where available and cite all sources.
  
  output_schema.yaml: |
    output_format:
      type: "notion_page"
      template: "market_report"
    
    page_structure:
      title_template: "Market Research - {topic_name} - {date}"
      sections:
        - name: "Market Overview"
          type: "text_block"
          content_source: "overview"
          configuration:
            include_metrics: true
            highlight_key_stats: true
        
        - name: "Market Metrics"
          type: "table"
          content_source: "metrics"
          configuration:
            columns: ["Metric", "Value", "Change", "Source"]
            format_numbers: true
        
        - name: "Competitive Analysis"
          type: "toggle_blocks"
          content_source: "competitors"
          configuration:
            group_by: "company"
            include_market_share: true
        
        - name: "Key Insights"
          type: "bullet_list"
          content_source: "insights"
          configuration:
            prioritize_by_impact: true
            include_confidence_scores: true
    
    content_processing:
      summary_length: "detailed"
      include_confidence_scores: true
      group_similar_findings: true
```

### Custom Configuration Deployment

To deploy custom research configurations:

1. Create ConfigMap YAML files following the template structure
2. Apply to cluster:

```bash
kubectl apply -f your-custom-config.yaml
```

3. Reference in CronJob or manual execution:

```bash
kubectl create job manual-research-job \
  --from=cronjob/research-scheduler \
  --env="RESEARCH_CONFIG=your-custom-config" \
  -n research-copilot
```

## Verification and Testing

### 1. Verify Deployments

```bash
# Check all pods are running
kubectl get pods -n research-copilot

# Check services are accessible
kubectl get services -n research-copilot

# Verify ConfigMaps are loaded
kubectl get configmaps -n research-copilot
```

### 2. Test Ollama Service

```bash
# Port forward to test Ollama directly
kubectl port-forward svc/ollama-service 11434:11434 -n research-copilot

# Test in another terminal
curl http://localhost:11434/api/generate \
  -d '{"model": "qwen2.5:7b", "prompt": "Hello", "stream": false}'
```

### 3. Test Research Agent

```bash
# Check agent logs
kubectl logs -l app=research-agent -n research-copilot

# Run manual research job
kubectl create job test-research \
  --from=cronjob/research-scheduler \
  --env="RESEARCH_CONFIG=tech-research-template" \
  -n research-copilot

# Monitor job execution
kubectl logs job/test-research -n research-copilot -f
```

## Monitoring and Maintenance

### Health Checks

```bash
# Check pod health
kubectl describe pods -n research-copilot

# View resource usage
kubectl top pods -n research-copilot

# Check persistent volumes
kubectl get pv,pvc -n research-copilot
```

### Log Management

```bash
# View recent logs
kubectl logs -l app=research-agent -n research-copilot --tail=100

# Follow logs in real-time
kubectl logs -l app=research-agent -n research-copilot -f

# Export logs for analysis
kubectl logs -l app=research-agent -n research-copilot > research-agent.log
```

### Backup and Recovery

```bash
# Backup ConfigMaps
kubectl get configmaps -n research-copilot -o yaml > configmaps-backup.yaml

# Backup Secrets (be careful with sensitive data)
kubectl get secrets -n research-copilot -o yaml > secrets-backup.yaml

# Backup Persistent Volume data
kubectl exec -n research-copilot deployment/ollama-server -- tar czf - /root/.ollama > ollama-backup.tar.gz
```

## Troubleshooting

### Common Issues

#### 1. Ollama Model Not Loading

```bash
# Check if model is downloaded
kubectl exec -n research-copilot deployment/ollama-server -- ollama list

# Download model manually
kubectl exec -n research-copilot deployment/ollama-server -- ollama pull qwen2.5:7b

# Check model size and storage
kubectl exec -n research-copilot deployment/ollama-server -- df -h
```

#### 2. Research Agent Connection Issues

```bash
# Test service connectivity
kubectl exec -n research-copilot deployment/research-agent -- \
  curl -v http://ollama-service:11434/api/tags

# Check DNS resolution
kubectl exec -n research-copilot deployment/research-agent -- \
  nslookup ollama-service
```

#### 3. Notion API Failures

```bash
# Verify secrets are mounted correctly
kubectl exec -n research-copilot deployment/research-agent -- \
  ls -la /etc/secrets/

# Test Notion API connectivity
kubectl exec -n research-copilot deployment/research-agent -- \
  curl -H "Authorization: Bearer $(cat /etc/secrets/notion-token)" \
  https://api.notion.com/v1/users/me
```

#### 4. Search API Issues

```bash
# Test SerpAPI connection
kubectl exec -n research-copilot deployment/research-agent -- \
  curl "https://serpapi.com/search.json?q=test&api_key=$(cat /etc/secrets/serpapi-key)"

# Check API quota and usage
kubectl logs -l app=research-agent -n research-copilot | grep -i "api\|quota\|rate"
```

### Performance Tuning

#### Resource Optimization

```bash
# Adjust resource requests and limits
kubectl patch deployment research-agent -n research-copilot -p '
{
  "spec": {
    "template": {
      "spec": {
        "containers": [{
          "name": "research-agent",
          "resources": {
            "requests": {"memory": "2Gi", "cpu": "1000m"},
            "limits": {"memory": "4Gi", "cpu": "2000m"}
          }
        }]
      }
    }
  }
}'
```

#### Scaling Configuration

```bash
# Scale research agent pods
kubectl scale deployment research-agent --replicas=3 -n research-copilot

# Configure horizontal pod autoscaler
kubectl autoscale deployment research-agent \
  --cpu-percent=70 \
  --min=1 \
  --max=5 \
  -n research-copilot
```

## Security Considerations

### Network Security

- Ensure proper network policies are in place
- Use TLS for all external communications
- Restrict egress traffic to required services only

### Secrets Management

- Rotate API keys regularly
- Use Kubernetes secrets with proper RBAC
- Consider external secret management solutions

### Container Security

- Use non-root users in containers
- Implement security contexts and pod security policies
- Regular security scanning of container images

## Upgrade Procedures

### Application Updates

```bash
# Build new image version
make build VERSION=v1.1.0

# Tag and push
docker tag research-copilot:latest localhost:5000/research-copilot:v1.1.0
docker push localhost:5000/research-copilot:v1.1.0

# Update deployment
kubectl set image deployment/research-agent \
  research-agent=localhost:5000/research-copilot:v1.1.0 \
  -n research-copilot

# Monitor rollout
kubectl rollout status deployment/research-agent -n research-copilot
```

### Configuration Updates

```bash
# Update ConfigMaps
kubectl apply -f k8s/configmaps/

# Restart pods to pick up new configuration
kubectl rollout restart deployment/research-agent -n research-copilot
```

This deployment guide provides comprehensive instructions for setting up, configuring, and maintaining
the Research Copilot Agent in a Kubernetes environment.
