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

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Banner
echo -e "${BLUE}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════════╗
║                    Financial Nomad                           ║
║                   🧪 Tests Backend                           ║
╚═══════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Cambiar al directorio del proyecto
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

# Tipo de tests a ejecutar
TEST_TYPE=${1:-"all"}

case $TEST_TYPE in
    "unit")
        PROFILES="firestore-emulator-test,backend-unit-tests"
        ;;
    "integration")
        PROFILES="firestore-emulator-test,backend-integration-tests"
        ;;
    "all")
        PROFILES="firestore-emulator-test,backend-unit-tests,backend-integration-tests"
        ;;
    *)
        error "Tipo de test inválido: $TEST_TYPE"
        echo "Uso: $0 [unit|integration|all]"
        exit 1
        ;;
esac

log "Ejecutando tests de backend: $TEST_TYPE"

# Exportar variables de entorno
if [ -f .env ]; then
    export $(cat .env | grep -v ^# | xargs)
fi

# Limpiar resultados anteriores
rm -rf test-results/backend
mkdir -p test-results/backend

# Ejecutar tests
log "Iniciando servicios de testing..."

if docker-compose -f devops/docker-compose/docker-compose.test.yml --profile test up -d firestore-emulator-test; then
    log "Esperando Firestore Emulator..."
    sleep 20
    
    # Ejecutar tests según el tipo
    if [ "$TEST_TYPE" = "all" ] || [ "$TEST_TYPE" = "unit" ]; then
        log "Ejecutando tests unitarios..."
        if docker-compose -f devops/docker-compose/docker-compose.test.yml --profile unit-tests run --rm backend-unit-tests; then
            success "✓ Tests unitarios pasaron"
            unit_result=0
        else
            error "✗ Tests unitarios fallaron"
            unit_result=1
        fi
        
        # Copiar resultados
        docker cp financial-nomad-backend-unit-tests:/app/htmlcov test-results/backend/unit-coverage 2>/dev/null || true
        docker cp financial-nomad-backend-unit-tests:/app/test-results test-results/backend/unit-results 2>/dev/null || true
    fi
    
    if [ "$TEST_TYPE" = "all" ] || [ "$TEST_TYPE" = "integration" ]; then
        log "Ejecutando tests de integración..."
        if docker-compose -f devops/docker-compose/docker-compose.test.yml --profile integration-tests run --rm backend-integration-tests; then
            success "✓ Tests de integración pasaron"
            integration_result=0
        else
            error "✗ Tests de integración fallaron"
            integration_result=1
        fi
        
        # Copiar resultados
        docker cp financial-nomad-backend-integration-tests:/app/htmlcov test-results/backend/integration-coverage 2>/dev/null || true
        docker cp financial-nomad-backend-integration-tests:/app/test-results test-results/backend/integration-results 2>/dev/null || true
    fi
    
    # Limpiar servicios
    log "Limpiando servicios de testing..."
    docker-compose -f devops/docker-compose/docker-compose.test.yml --profile test down
    
    # Mostrar resultados
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
    
    overall_result=0
    if [ "$TEST_TYPE" = "all" ]; then
        if [ ${unit_result:-0} -eq 0 ] && [ ${integration_result:-0} -eq 0 ]; then
            echo -e "${BLUE}║                   ${GREEN}✅ TODOS LOS TESTS EXITOSOS${BLUE}               ║${NC}"
        else
            echo -e "${BLUE}║                   ${RED}❌ ALGUNOS TESTS FALLARON${BLUE}                ║${NC}"
            overall_result=1
        fi
    elif [ "$TEST_TYPE" = "unit" ]; then
        if [ ${unit_result:-0} -eq 0 ]; then
            echo -e "${BLUE}║                   ${GREEN}✅ TESTS UNITARIOS EXITOSOS${BLUE}              ║${NC}"
        else
            echo -e "${BLUE}║                   ${RED}❌ TESTS UNITARIOS FALLARON${BLUE}              ║${NC}"
            overall_result=1
        fi
    elif [ "$TEST_TYPE" = "integration" ]; then
        if [ ${integration_result:-0} -eq 0 ]; then
            echo -e "${BLUE}║                 ${GREEN}✅ TESTS INTEGRACIÓN EXITOSOS${BLUE}            ║${NC}"
        else
            echo -e "${BLUE}║                 ${RED}❌ TESTS INTEGRACIÓN FALLARON${BLUE}            ║${NC}"
            overall_result=1
        fi
    fi
    
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
    
    # Mostrar ubicación de reportes
    echo ""
    if [ -d "test-results/backend" ]; then
        echo -e "${BLUE}📊 Reportes disponibles en:${NC}"
        find test-results/backend -name "*.html" -o -name "*.xml" | sort | while read -r file; do
            echo -e "   ${YELLOW}•${NC} $file"
        done
    fi
    
    exit $overall_result
    
else
    error "Error iniciando servicios de testing"
    exit 1
fi