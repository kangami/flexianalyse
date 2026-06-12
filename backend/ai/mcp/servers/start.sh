#!/bin/bash
# MCP Servers - Startup and Management Script
# Usage: ./start.sh [command]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed"
        exit 1
    fi
    
    print_success "Docker and Docker Compose found"
}

check_env() {
    if [ ! -f .env ]; then
        print_warning ".env file not found"
        print_warning "Creating .env from .env.example..."
        cp .env.example .env
        print_warning "Please update .env with your credentials"
    fi
}

setup() {
    print_header "Setting up MCP Servers"
    
    check_docker
    check_env
    
    # Create necessary directories
    mkdir -p secrets logs
    print_success "Directories created"
}

build() {
    print_header "Building Docker Images"
    check_docker
    
    docker-compose build --no-cache
    print_success "Build complete"
}

start() {
    print_header "Starting MCP Servers"
    check_docker
    check_env
    
    docker-compose up -d
    print_success "Services started"
    
    # Wait for services to be ready
    echo ""
    echo "Waiting for services to be ready..."
    sleep 5
    
    # Show status
    status
}

stop() {
    print_header "Stopping MCP Servers"
    docker-compose down
    print_success "Services stopped"
}

restart() {
    print_header "Restarting MCP Servers"
    docker-compose restart
    print_success "Services restarted"
    sleep 3
    status
}

logs() {
    SERVICE=$1
    if [ -z "$SERVICE" ]; then
        docker-compose logs -f
    else
        docker-compose logs -f "$SERVICE"
    fi
}

status() {
    print_header "Service Status"
    docker-compose ps
    
    echo ""
    echo "Service URLs:"
    echo -e "  SQL Server:      ${BLUE}stdio://sql-server:3001${NC}"
    echo -e "  Google Drive:    ${BLUE}stdio://google-drive-server:3002${NC}"
    echo -e "  SharePoint:      ${BLUE}stdio://sharepoint-server:3003${NC}"
    echo ""
    echo "Logs:"
    echo "  View all logs:     docker-compose logs -f"
    echo "  SQL server logs:   docker-compose logs -f sql-server"
    echo "  Google Drive:      docker-compose logs -f google-drive-server"
    echo "  SharePoint:        docker-compose logs -f sharepoint-server"
}

health_check() {
    print_header "Health Check"
    
    echo "Checking SQL Server..."
    docker-compose exec sql-server python -c "print('✓ SQL Server OK')" || print_error "SQL Server unreachable"
    
    echo "Checking Google Drive Server..."
    docker-compose exec google-drive-server python -c "print('✓ Google Drive Server OK')" || print_error "Google Drive Server unreachable"
    
    echo "Checking SharePoint Server..."
    docker-compose exec sharepoint-server python -c "print('✓ SharePoint Server OK')" || print_error "SharePoint Server unreachable"
}

shell() {
    SERVICE=$1
    if [ -z "$SERVICE" ]; then
        print_error "Service not specified"
        echo "Usage: ./start.sh shell [sql-server|google-drive-server|sharepoint-server]"
        exit 1
    fi
    
    docker-compose exec "$SERVICE" /bin/bash
}

clean() {
    print_header "Cleaning Up"
    
    print_warning "Stopping containers..."
    docker-compose down -v
    
    print_warning "Removing cache..."
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete
    
    print_success "Cleanup complete"
}

usage() {
    echo "MCP Servers Management Script"
    echo ""
    echo "Usage: ./start.sh [command]"
    echo ""
    echo "Commands:"
    echo "  setup              Setup environment (copy .env, create directories)"
    echo "  build              Build Docker images"
    echo "  start              Start all services"
    echo "  stop               Stop all services"
    echo "  restart            Restart all services"
    echo "  status             Show service status"
    echo "  logs [service]     View logs (optional: service name)"
    echo "  health             Run health checks"
    echo "  shell [service]    Open shell in service container"
    echo "  clean              Clean up and remove containers"
    echo "  help               Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./start.sh setup"
    echo "  ./start.sh build && ./start.sh start"
    echo "  ./start.sh logs sql-server"
    echo "  ./start.sh shell google-drive-server"
}

# Main
COMMAND=${1:-help}

case "$COMMAND" in
    setup)
        setup
        ;;
    build)
        build
        ;;
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    logs)
        logs "$2"
        ;;
    health)
        health_check
        ;;
    shell)
        shell "$2"
        ;;
    clean)
        clean
        ;;
    help)
        usage
        ;;
    *)
        print_error "Unknown command: $COMMAND"
        echo ""
        usage
        exit 1
        ;;
esac
