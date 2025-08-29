#!/bin/bash

# Research Copilot Deployment Script
# Automated deployment with environment validation and setup

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
AGENT_NAME="research-copilot"
REGISTRY="localhost:5000"

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

# Usage information
usage() {
    cat << EOF
Research Copilot Deployment Script

Usage: $0 [OPTIONS] ENVIRONMENT

ENVIRONMENT:
    development     Deploy to development environment
    staging         Deploy to staging environment
    production      Deploy to production environment

OPTIONS:
    -h, --help      Show this help message
    -v, --validate  Only validate configuration, don't deploy
    -b, --build     Force rebuild of Docker image
    -s, --secrets   Recreate secrets
    --dry-run       Show what would be deployed without applying
    --skip-checks   Skip prerequisite checks

Examples:
    $0 production                    # Deploy to production
    $0 development --build           # Build and deploy to development
    $0 staging --validate            # Validate staging configuration
    $0 production --dry-run          # Show production deployment plan

Environment Variables:
    NOTION_TOKEN                     # Required: Notion integration token
    NOTION_DATABASE_ID               # Required: Notion database ID
    SERPAPI_KEY                      # Optional: SerpAPI key
    BING_API_KEY                     # Optional: Bing Search API key
    BING_ENDPOINT                    # Optional: Bing Search endpoint

EOF
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    local errors=0

    # Check required commands
    for cmd in kubectl kustomize docker make; do
        if ! command -v "$cmd" &> /dev/null; then
            log_error "$cmd is not installed or not in PATH"
            ((errors++))
        fi
    done

    # Check kubectl connectivity
    if ! kubectl cluster-info &> /dev/null; then
        log_error "kubectl cannot connect to Kubernetes cluster"
        ((errors++))
    fi

    # Check Docker registry
    if ! curl -s -X GET "http://${REGISTRY}/v2/_catalog" &> /dev/null; then
        log_warning "Docker registry at ${REGISTRY} is not accessible"
        log_warning "Make sure your local registry is running"
    fi

    # Check required environment variables
    if [[ -z "${NOTION_TOKEN:-}" ]]; then
        log_error "NOTION_TOKEN environment variable is required"
        ((errors++))
    fi

    if [[ -z "${NOTION_DATABASE_ID:-}" ]]; then
        log_error "NOTION_DATABASE_ID environment variable is required"
        ((errors++))
    fi

    if [[ $errors -gt 0 ]]; then
        log_error "Prerequisites check failed with $errors errors"
        exit 1
    fi

    log_success "Prerequisites check passed"
}

# Validate Kustomize configuration
validate_config() {
    local env=$1
    log_info "Validating Kustomize configuration for $env environment..."

    cd "$PROJECT_DIR"

    if ! make validate-kustomize; then
        log_error "Kustomize validation failed"
        exit 1
    fi

    log_success "Configuration validation passed"
}



# Show deployment status
show_status() {
    log_info "Checking deployment status..."

    cd "$PROJECT_DIR"

    echo "Deployment Status:"
    make status

    echo -e "\nRecent Events:"
    make events | tail -10
}

# Dry run deployment
dry_run() {
    local env=$1
    log_info "Showing deployment plan for $env environment..."

    cd "$PROJECT_DIR"

    ENVIRONMENT=$env make dry-run
}

# Main deployment function
main() {
    local environment=""
    local validate_only=false
    local force_build=false
    local recreate_secrets=false
    local dry_run_only=false
    local skip_checks=false

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                exit 0
                ;;
            -v|--validate)
                validate_only=true
                shift
                ;;
            -b|--build)
                force_build=true
                shift
                ;;
            -s|--secrets)
                recreate_secrets=true
                shift
                ;;
            --dry-run)
                dry_run_only=true
                shift
                ;;
            --skip-checks)
                skip_checks=true
                shift
                ;;
            development|staging|production)
                environment=$1
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done

    # Validate environment parameter
    if [[ -z "$environment" ]]; then
        log_error "Environment parameter is required"
        usage
        exit 1
    fi

    if [[ ! "$environment" =~ ^(development|staging|production)$ ]]; then
        log_error "Invalid environment: $environment"
        usage
        exit 1
    fi

    log_info "Starting deployment process for $environment environment"

    # Skip checks if requested
    if [[ "$skip_checks" != true ]]; then
        check_prerequisites
    fi

    # Validate configuration
    validate_config "$environment"

    # Handle dry run
    if [[ "$dry_run_only" == true ]]; then
        dry_run "$environment"
        exit 0
    fi

    # Handle validate only
    if [[ "$validate_only" == true ]]; then
        log_success "Validation completed successfully"
        exit 0
    fi

    # Build image if requested or if it doesn't exist
    if [[ "$force_build" == true ]] || ! docker images | grep -q "$AGENT_NAME"; then
        log_info "Building and pushing Docker image..."
        cd "$PROJECT_DIR"
        make build push
    fi

    # Manage secrets if requested or if they don't exist
    if [[ "$recreate_secrets" == true ]] || ! kubectl get secret api-credentials -n research-copilot &> /dev/null; then
        log_info "Managing secrets..."
        cd "$PROJECT_DIR"
        make create-secrets
    fi

    # Deploy to Kubernetes using Makefile
    log_info "Deploying to $environment environment..."
    cd "$PROJECT_DIR"
    make "deploy-${environment}"

    # Show deployment status
    show_status

    log_success "Deployment process completed successfully!"

    # Provide useful next steps
    echo -e "\n${BLUE}Next Steps:${NC}"
    echo "  • Monitor logs: make logs"
    echo "  • Check health: make health"
    echo "  • View metrics: make metrics"
    echo "  • Port forward: make port-forward"
    echo "  • Scale deployment: make scale REPLICAS=N"

    if [[ "$environment" == "production" ]]; then
        echo "  • Backup config: make backup-config"
    fi
}

# Handle script interruption
trap 'log_error "Deployment interrupted"; exit 1' INT TERM

# Run main function
main "$@"
