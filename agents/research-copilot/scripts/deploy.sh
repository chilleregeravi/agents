#!/bin/bash

# LLM Release Radar Agent Deployment Script
# Deploys the agent to Kubernetes cluster on Raspberry Pi 5

set -euo pipefail

# Configuration
AGENT_NAME="llm-release-radar"
NAMESPACE="agents"
REGISTRY="localhost:5000"
IMAGE_TAG="${1:-latest}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check if kubectl is available
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        exit 1
    fi

    # Check if docker is available
    if ! command -v docker &> /dev/null; then
        log_error "docker is not installed or not in PATH"
        exit 1
    fi

    # Check if we can connect to Kubernetes
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi

    # Check if local registry is running
    if ! curl -s http://localhost:5000/v2/ &> /dev/null; then
        log_warning "Local Docker registry is not running on localhost:5000"
        log_info "Starting local registry..."
        docker run -d -p 5000:5000 --name registry --restart=always registry:2 || {
            log_error "Failed to start local registry"
            exit 1
        }
        sleep 5
    fi

    log_success "Prerequisites check passed"
}

# Build Docker image
build_image() {
    log_info "Building Docker image..."

    cd "$(dirname "$0")/.."

    # Build the image
    docker build -f docker/Dockerfile -t "${AGENT_NAME}:${IMAGE_TAG}" . || {
        log_error "Failed to build Docker image"
        exit 1
    }

    # Tag for registry
    docker tag "${AGENT_NAME}:${IMAGE_TAG}" "${REGISTRY}/${AGENT_NAME}:${IMAGE_TAG}"

    log_success "Docker image built successfully"
}

# Push image to registry
push_image() {
    log_info "Pushing image to registry..."

    docker push "${REGISTRY}/${AGENT_NAME}:${IMAGE_TAG}" || {
        log_error "Failed to push image to registry"
        exit 1
    }

    log_success "Image pushed to registry"
}

# Create namespace
create_namespace() {
    log_info "Creating namespace..."

    kubectl apply -f k8s/namespace.yaml || {
        log_error "Failed to create namespace"
        exit 1
    }

    log_success "Namespace created/updated"
}

# Deploy secrets
deploy_secrets() {
    log_info "Deploying secrets..."

    # Check if secrets file exists and has been configured
    if [[ ! -f "k8s/secrets.yaml" ]]; then
        log_error "secrets.yaml not found"
        exit 1
    fi

    # Warning about default values
    if grep -q "your_notion_integration_token_here" k8s/secrets.yaml; then
        log_warning "Secrets file contains default values!"
        log_warning "Please update k8s/secrets.yaml with actual API keys before deployment"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Deployment cancelled"
            exit 0
        fi
    fi

    kubectl apply -f k8s/secrets.yaml || {
        log_error "Failed to deploy secrets"
        exit 1
    }

    log_success "Secrets deployed"
}

# Deploy configuration
deploy_config() {
    log_info "Deploying configuration..."

    kubectl apply -f k8s/configmap.yaml || {
        log_error "Failed to deploy configuration"
        exit 1
    }

    log_success "Configuration deployed"
}

# Deploy RBAC
deploy_rbac() {
    log_info "Deploying RBAC..."

    kubectl apply -f k8s/service-account.yaml || {
        log_error "Failed to deploy RBAC"
        exit 1
    }

    log_success "RBAC deployed"
}

# Deploy application
deploy_app() {
    log_info "Deploying application..."

    # Update image tag in deployment if not latest
    if [[ "${IMAGE_TAG}" != "latest" ]]; then
        sed -i.bak "s|localhost:5000/${AGENT_NAME}:latest|localhost:5000/${AGENT_NAME}:${IMAGE_TAG}|g" k8s/deployment.yaml
        sed -i.bak "s|localhost:5000/${AGENT_NAME}:latest|localhost:5000/${AGENT_NAME}:${IMAGE_TAG}|g" k8s/cronjob.yaml
    fi

    # Deploy service
    kubectl apply -f k8s/service.yaml || {
        log_error "Failed to deploy service"
        exit 1
    }

    # Deploy main application
    kubectl apply -f k8s/deployment.yaml || {
        log_error "Failed to deploy application"
        exit 1
    }

    # Deploy cronjob
    kubectl apply -f k8s/cronjob.yaml || {
        log_error "Failed to deploy cronjob"
        exit 1
    }

    # Restore original files if we modified them
    if [[ "${IMAGE_TAG}" != "latest" ]]; then
        mv k8s/deployment.yaml.bak k8s/deployment.yaml 2>/dev/null || true
        mv k8s/cronjob.yaml.bak k8s/cronjob.yaml 2>/dev/null || true
    fi

    log_success "Application deployed"
}

# Wait for deployment
wait_for_deployment() {
    log_info "Waiting for deployment to be ready..."

    kubectl wait --for=condition=available --timeout=300s deployment/${AGENT_NAME} -n ${NAMESPACE} || {
        log_error "Deployment did not become ready in time"
        log_info "Checking pod status..."
        kubectl get pods -n ${NAMESPACE} -l app=${AGENT_NAME}
        log_info "Checking pod logs..."
        kubectl logs -n ${NAMESPACE} -l app=${AGENT_NAME} --tail=20
        exit 1
    }

    log_success "Deployment is ready"
}

# Show deployment status
show_status() {
    log_info "Deployment status:"

    echo
    echo "Namespace:"
    kubectl get namespace ${NAMESPACE}

    echo
    echo "Pods:"
    kubectl get pods -n ${NAMESPACE} -l app=${AGENT_NAME}

    echo
    echo "Services:"
    kubectl get services -n ${NAMESPACE} -l app=${AGENT_NAME}

    echo
    echo "CronJobs:"
    kubectl get cronjobs -n ${NAMESPACE} -l app=${AGENT_NAME}

    echo
    echo "ConfigMaps:"
    kubectl get configmaps -n ${NAMESPACE} -l app=${AGENT_NAME}

    echo
    echo "Secrets:"
    kubectl get secrets -n ${NAMESPACE} -l app=${AGENT_NAME}
}

# Health check
health_check() {
    log_info "Performing health check..."

    # Get pod name
    POD_NAME=$(kubectl get pods -n ${NAMESPACE} -l app=${AGENT_NAME} -o jsonpath='{.items[0].metadata.name}')

    if [[ -z "${POD_NAME}" ]]; then
        log_error "No pods found for ${AGENT_NAME}"
        return 1
    fi

    # Execute health check
    kubectl exec -n ${NAMESPACE} "${POD_NAME}" -- python -m src.agent.main --health-check || {
        log_error "Health check failed"
        return 1
    }

    log_success "Health check passed"
}

# Manual test run
test_run() {
    log_info "Running manual test..."

    # Create a test job
    cat <<EOF | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: ${AGENT_NAME}-test-$(date +%s)
  namespace: ${NAMESPACE}
  labels:
    app: ${AGENT_NAME}
    job-type: test
spec:
  template:
    metadata:
      labels:
        app: ${AGENT_NAME}
        job-type: test
    spec:
      serviceAccountName: ${AGENT_NAME}
      containers:
      - name: test-runner
        image: ${REGISTRY}/${AGENT_NAME}:${IMAGE_TAG}
        command: ["python", "-m", "src.agent.main", "--log-level", "DEBUG"]
        envFrom:
        - configMapRef:
            name: ${AGENT_NAME}-config
        - secretRef:
            name: ${AGENT_NAME}-secrets
      restartPolicy: Never
  backoffLimit: 1
EOF

    log_success "Test job created. Monitor with: kubectl logs -n ${NAMESPACE} -l job-type=test -f"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up deployment..."

    kubectl delete -f k8s/ -n ${NAMESPACE} --ignore-not-found=true

    log_success "Cleanup completed"
}

# Main deployment function
main() {
    log_info "Starting deployment of ${AGENT_NAME} with image tag: ${IMAGE_TAG}"

    case "${1:-deploy}" in
        "deploy")
            check_prerequisites
            build_image
            push_image
            create_namespace
            deploy_secrets
            deploy_config
            deploy_rbac
            deploy_app
            wait_for_deployment
            show_status
            health_check
            log_success "Deployment completed successfully!"
            ;;
        "build")
            check_prerequisites
            build_image
            push_image
            ;;
        "status")
            show_status
            ;;
        "health")
            health_check
            ;;
        "test")
            test_run
            ;;
        "cleanup")
            cleanup
            ;;
        "help"|"-h"|"--help")
            echo "Usage: $0 [deploy|build|status|health|test|cleanup] [image-tag]"
            echo
            echo "Commands:"
            echo "  deploy   - Full deployment (default)"
            echo "  build    - Build and push image only"
            echo "  status   - Show deployment status"
            echo "  health   - Run health check"
            echo "  test     - Run manual test"
            echo "  cleanup  - Remove deployment"
            echo
            echo "Arguments:"
            echo "  image-tag - Docker image tag (default: latest)"
            ;;
        *)
            log_error "Unknown command: $1"
            echo "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
