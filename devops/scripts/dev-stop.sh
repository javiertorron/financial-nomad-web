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

# Banner
echo -e "${BLUE}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════════╗
║                    Financial Nomad                           ║
║                    🛑 Parando Servicios                      ║
╚═══════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Cambiar al directorio del proyecto
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

log "Parando servicios de desarrollo..."

# Parar todos los servicios
docker-compose -f devops/docker-compose/docker-compose.dev.yml down

# Limpiar volúmenes si se solicita
if [ "$1" = "--clean" ]; then
    log "Limpiando volúmenes..."
    docker-compose -f devops/docker-compose/docker-compose.dev.yml down -v
    docker system prune -f
    success "✓ Volúmenes limpiados"
fi

# Mostrar estado final
log "Verificando que todos los servicios estén parados..."

ports=(4200 8080 8081 4000 80 6379 8025)
running_ports=()

for port in "${ports[@]}"; do
    if lsof -i :$port &> /dev/null; then
        running_ports+=($port)
    fi
done

if [ ${#running_ports[@]} -eq 0 ]; then
    success "✓ Todos los servicios han sido parados correctamente"
else
    echo -e "${YELLOW}⚠️  Los siguientes puertos aún están en uso: ${running_ports[*]}${NC}"
    echo "Esto puede ser normal si tienes otros servicios ejecutándose."
fi

echo ""
echo -e "${GREEN}🛑 Servicios de desarrollo parados${NC}"
echo ""
echo -e "${BLUE}Para reiniciar:${NC} ./devops/scripts/dev-start.sh"