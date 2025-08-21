#!/bin/bash

# Colors para output
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Banner
echo -e "${BLUE}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════════╗
║                    Financial Nomad                           ║
║                      📋 Ver Logs                             ║
╚═══════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Cambiar al directorio del proyecto
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

# Determinar qué servicio mostrar
SERVICE=${1:-""}
FOLLOW=${2:-"--follow"}

if [ -z "$SERVICE" ]; then
    echo "Servicios disponibles:"
    echo "  frontend          - Angular development server"
    echo "  backend           - FastAPI application"
    echo "  firestore-emulator - Firestore emulator"
    echo "  nginx             - Nginx proxy"
    echo "  redis             - Redis cache"
    echo "  mailhog           - Email testing"
    echo ""
    echo "Uso:"
    echo "  $0 [servicio] [--no-follow]"
    echo ""
    echo "Ejemplos:"
    echo "  $0                    # Todos los logs con follow"
    echo "  $0 backend           # Solo logs del backend con follow"
    echo "  $0 frontend --no-follow  # Logs del frontend sin follow"
    echo ""
    
    # Mostrar logs de todos los servicios
    echo "Mostrando logs de todos los servicios (presiona Ctrl+C para salir):"
    docker compose -f devops/docker compose/docker compose.dev.yml logs --follow --tail=100
else
    # Convertir --no-follow a parámetros de docker compose
    if [ "$FOLLOW" = "--no-follow" ]; then
        docker compose -f devops/docker compose/docker compose.dev.yml logs --tail=100 "$SERVICE"
    else
        echo "Mostrando logs de $SERVICE (presiona Ctrl+C para salir):"
        docker compose -f devops/docker compose/docker compose.dev.yml logs --follow --tail=100 "$SERVICE"
    fi
fi