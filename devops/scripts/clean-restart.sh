#!/bin/bash
set -e

# Colors para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Banner
echo -e "${BLUE}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════════╗
║                    Financial Nomad                           ║
║                   🔄 Reinicio Limpio                         ║
╚═══════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Cambiar al directorio del proyecto
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

warning "⚠️  Este comando realizará un reinicio limpio eliminando:"
warning "   - Todos los contenedores de Financial Nomad"
warning "   - Volúmenes de datos (incluyendo datos de Firestore)"
warning "   - Imágenes Docker del proyecto"
warning "   - Cache de build"

echo ""
echo "¿Estás seguro de que quieres continuar? (y/N)"
read -r response

if [[ ! "$response" =~ ^[Yy]$ ]]; then
    echo "Operación cancelada."
    exit 0
fi

echo ""
log "Iniciando reinicio limpio..."

# Parar todos los servicios
log "Parando servicios..."
./devops/scripts/dev-stop.sh --clean

# Limpiar contenedores relacionados
log "Limpiando contenedores de Financial Nomad..."
docker ps -a --filter "name=financial-nomad" --format "{{.Names}}" | xargs -r docker rm -f

# Limpiar volúmenes
log "Limpiando volúmenes..."
docker volume ls --filter "name=financial-nomad" --format "{{.Name}}" | xargs -r docker volume rm

# Limpiar imágenes del proyecto
log "Limpiando imágenes del proyecto..."
docker images --filter "reference=financial-nomad*" --format "{{.Repository}}:{{.Tag}}" | xargs -r docker rmi -f

# Limpiar cache de Docker
log "Limpiando cache de Docker..."
docker builder prune -f

# Limpiar cache de frontend si existe
if [ -d "frontend/node_modules" ]; then
    log "Limpiando cache de frontend..."
    rm -rf frontend/node_modules
    rm -rf frontend/.angular
fi

# Limpiar cache de backend si existe
if [ -d "backend/.pytest_cache" ]; then
    log "Limpiando cache de backend..."
    rm -rf backend/.pytest_cache
    rm -rf backend/__pycache__
    find backend -name "*.pyc" -delete
    find backend -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
fi

# Limpiar logs si existen
if [ -d "logs" ]; then
    log "Limpiando logs..."
    rm -rf logs/*
fi

success "✓ Limpieza completada"

echo ""
log "Reiniciando servicios..."

# Reconstruir e iniciar servicios
./devops/scripts/dev-start.sh

echo ""
echo -e "${GREEN}🎉 Reinicio limpio completado exitosamente${NC}"
echo ""
echo -e "${BLUE}Los servicios están funcionando con una instalación completamente limpia.${NC}"