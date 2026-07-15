#!/bin/bash
# Setup script: Moodle 3.9 + AI Chatbot integration
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()    { echo -e "${GREEN}[INFO]${NC} $*"; }
warning() { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

check_requirements() {
    info "Checking requirements..."
    command -v docker  >/dev/null 2>&1 || error "Docker not found"
    docker compose version >/dev/null 2>&1 || error "Docker Compose v2 not found"

    if [ ! -f "${PROJECT_DIR}/.env.moodle" ]; then
        error ".env.moodle not found in ${PROJECT_DIR}"
    fi
    info "Requirements OK."
}

check_port_80() {
    info "Checking port 80..."
    if ss -tlnp 2>/dev/null | grep -q ':80 '; then
        warning "Port 80 is in use. Moodle will fail to bind."
        ss -tlnp | grep ':80 '
        read -rp "Continue anyway? [y/N] " ans
        [[ "${ans,,}" == "y" ]] || exit 1
    else
        info "Port 80 is free."
    fi
}

build_moodle() {
    info "Building Moodle 3.9 Docker image (this may take 5-10 min for the first build)..."
    docker compose \
        -f "${PROJECT_DIR}/docker-compose.moodle.yml" \
        --env-file "${PROJECT_DIR}/.env.moodle" \
        build --no-cache moodle
    info "Build complete."
}

start_moodle() {
    info "Starting Moodle + MariaDB..."
    docker compose \
        -f "${PROJECT_DIR}/docker-compose.moodle.yml" \
        --env-file "${PROJECT_DIR}/.env.moodle" \
        up -d

    info "Waiting for Moodle installation to complete (may take 3-5 min)..."
    local retries=60
    while ! curl -sf "http://localhost:80/" -o /dev/null 2>/dev/null; do
        retries=$((retries - 1))
        if [ $retries -le 0 ]; then
            warning "Moodle did not respond in time. Check logs:"
            docker logs fcim-moodle --tail 30
            exit 1
        fi
        printf "."
        sleep 5
    done
    echo ""
    info "Moodle is up!"
}

install_plugin() {
    info "Installing AI Chatbot block plugin..."
    docker exec fcim-moodle php /var/www/html/admin/cli/upgrade.php --non-interactive 2>/dev/null || true
    info "Plugin installed. Configure it at: Admin > Site Administration > Plugins > Blocks > AI Assistant"
}

print_summary() {
    local moodle_url
    moodle_url=$(grep MOODLE_WWWROOT "${PROJECT_DIR}/.env.moodle" | cut -d= -f2)
    local admin_user
    admin_user=$(grep MOODLE_ADMIN_USER "${PROJECT_DIR}/.env.moodle" | cut -d= -f2)
    local admin_pass
    admin_pass=$(grep MOODLE_ADMIN_PASSWORD "${PROJECT_DIR}/.env.moodle" | cut -d= -f2)

    echo ""
    echo "=========================================="
    echo "  Moodle 3.9 is ready!"
    echo "=========================================="
    echo "  URL:      ${moodle_url}"
    echo "  Admin:    ${admin_user}"
    echo "  Password: ${admin_pass}"
    echo ""
    echo "  Chatbot API: http://10.202.40.130:8010"
    echo "  (start with: docker compose -f docker-compose.chatbot.yml up -d)"
    echo "=========================================="
    echo ""
    echo "  Plugin setup:"
    echo "  1. Login to Moodle as admin"
    echo "  2. Go to: Site Admin > Plugins > Blocks > AI Assistant"
    echo "  3. Set API URL to: http://10.202.40.130:8010"
    echo "  4. Add block to any course"
    echo "=========================================="
}

main() {
    check_requirements
    check_port_80
    build_moodle
    start_moodle
    install_plugin
    print_summary
}

main "$@"
