#!/bin/bash
#
# Deployment script for Billing System
# Builds and deploys the Docker container
#
# Usage:
#   ./scripts/deploy.sh [environment]
#
# Arguments:
#   environment: development, testing, or production (default: development)
#

set -e  # Exit on error
set -u  # Exit on undefined variable

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT=${1:-development}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
IMAGE_NAME="billing-system"
VERSION="1.0.0"
BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
VCS_REF=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

# Functions
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

check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi

    # Check if .env file exists
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        log_error ".env file not found. Please create one from .env.example"
        log_info "Run: cp .env.example .env"
        exit 1
    fi

    log_success "Prerequisites check passed"
}

validate_config() {
    log_info "Validating configuration..."

    cd "$PROJECT_ROOT"

    # Run configuration validation script
    if ! python scripts/validate_config.py; then
        log_error "Configuration validation failed"
        exit 1
    fi

    log_success "Configuration is valid"
}

build_image() {
    log_info "Building Docker image..."

    cd "$PROJECT_ROOT"

    docker build \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VCS_REF="$VCS_REF" \
        --build-arg VERSION="$VERSION" \
        -t "$IMAGE_NAME:$VERSION" \
        -t "$IMAGE_NAME:latest" \
        -f Dockerfile \
        .

    log_success "Docker image built successfully"
}

test_image() {
    log_info "Testing Docker image..."

    # Test that image can run
    if ! docker run --rm "$IMAGE_NAME:latest" python -c "from src.config.settings import BillingSystemConfig; print('✓ Import successful')"; then
        log_error "Docker image test failed"
        exit 1
    fi

    log_success "Docker image test passed"
}

deploy_with_compose() {
    log_info "Deploying with Docker Compose..."

    cd "$PROJECT_ROOT"

    # Set environment variables for compose
    export BUILD_DATE
    export VCS_REF
    export VERSION

    # Stop and remove existing containers
    docker-compose down

    # Start services
    docker-compose up -d

    # Wait for health check
    log_info "Waiting for container to be healthy..."
    sleep 5

    # Check container status
    if docker-compose ps | grep -q "Up"; then
        log_success "Container is running"
    else
        log_error "Container failed to start"
        docker-compose logs
        exit 1
    fi

    log_success "Deployment completed successfully"
}

show_usage() {
    log_info "Deployment completed!"
    echo ""
    echo "Available commands:"
    echo "  - View logs:          docker-compose logs -f"
    echo "  - Stop container:     docker-compose down"
    echo "  - Restart container:  docker-compose restart"
    echo "  - Run report:         docker-compose run billing-system python -m src.cli generate-report --month 2024-10"
    echo "  - List timesheets:    docker-compose run billing-system python -m src.cli list-timesheets"
    echo "  - Validate data:      docker-compose run billing-system python -m src.cli validate-data"
}

# Main execution
main() {
    log_info "Starting deployment for environment: $ENVIRONMENT"
    echo ""

    check_prerequisites
    validate_config
    build_image
    test_image
    deploy_with_compose

    echo ""
    show_usage
}

# Run main function
main "$@"
