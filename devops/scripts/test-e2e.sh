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

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Banner
echo -e "${BLUE}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════════╗
║                    Financial Nomad                           ║
║                   🧪 Tests End-to-End                        ║
╚═══════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Cambiar al directorio del proyecto
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

# Verificar que Docker esté ejecutándose
if ! docker ps &> /dev/null; then
    error "Docker no está ejecutándose. Por favor inicia Docker primero."
    exit 1
fi

# Función para verificar que un servicio esté respondiendo
wait_for_service() {
    local service_name=$1
    local url=$2
    local timeout=${3:-60}
    local counter=0
    
    log "Esperando que $service_name esté listo..."
    
    while ! curl -s "$url" > /dev/null 2>&1; do
        if [ $counter -eq $timeout ]; then
            error "Timeout esperando $service_name en $url"
            return 1
        fi
        sleep 2
        counter=$((counter + 2))
        echo -n "."
    done
    echo ""
    success "✓ $service_name está listo"
}

# Configurar entorno de testing
log "Configurando entorno de testing..."

# Parar servicios de desarrollo si están ejecutándose
if docker compose -f devops/docker compose/docker compose.dev.yml ps -q | grep -q .; then
    warning "Parando servicios de desarrollo..."
    ./devops/scripts/dev-stop.sh
fi

# Iniciar servicios en modo testing
log "Iniciando servicios para testing..."

# Exportar variables de entorno
if [ -f .env ]; then
    export $(cat .env | grep -v ^# | xargs)
fi

# Configurar variables específicas para testing
export ENVIRONMENT=testing
export DEBUG=false
export USE_FIRESTORE_EMULATOR=true
export FIRESTORE_PROJECT_ID=financial-nomad-test

# Iniciar Firestore Emulator para testing
log "Iniciando Firestore Emulator..."
docker run -d \
    --name financial-nomad-firestore-test \
    -p 8082:8081 \
    -p 4001:4000 \
    -v "$PROJECT_ROOT/devops/firebase:/firebase" \
    gcr.io/google.com/cloudsdktool/cloud-sdk:alpine \
    sh -c "gcloud config set project financial-nomad-test && gcloud emulators firestore start --project=financial-nomad-test --host-port=0.0.0.0:8081 --rules=/firebase/firestore.rules"

# Esperar a que Firestore esté listo
wait_for_service "Firestore Emulator" "http://localhost:8082" 90

# Iniciar backend en modo testing
log "Iniciando Backend para testing..."
docker run -d \
    --name financial-nomad-backend-test \
    -p 8082:8080 \
    --link financial-nomad-firestore-test:firestore-emulator \
    -e ENVIRONMENT=testing \
    -e DEBUG=false \
    -e USE_FIRESTORE_EMULATOR=true \
    -e FIRESTORE_EMULATOR_HOST=firestore-emulator:8081 \
    -e FIRESTORE_PROJECT_ID=financial-nomad-test \
    -e SECRET_KEY="test-secret-key" \
    -e GOOGLE_CLIENT_ID="${GOOGLE_CLIENT_ID:-test-client-id}" \
    -v "$PROJECT_ROOT/backend:/app" \
    financial-nomad-backend-test:latest

# Esperar a que backend esté listo
wait_for_service "Backend API" "http://localhost:8082/api/v1/health" 120

# Iniciar frontend en modo testing
log "Iniciando Frontend para testing..."
docker run -d \
    --name financial-nomad-frontend-test \
    -p 4201:4200 \
    --link financial-nomad-backend-test:backend \
    -e NODE_ENV=testing \
    -e API_URL=http://localhost:8082/api/v1 \
    -e GOOGLE_CLIENT_ID="${GOOGLE_CLIENT_ID:-test-client-id}" \
    -v "$PROJECT_ROOT/frontend:/app" \
    financial-nomad-frontend-test:latest

# Esperar a que frontend esté listo
wait_for_service "Frontend" "http://localhost:4201" 180

# Ejecutar tests
log "Ejecutando tests end-to-end..."

# Crear directorio de reportes si no existe
mkdir -p test-results/e2e

# Ejecutar tests con Playwright
cd frontend

if [ ! -d "node_modules" ]; then
    log "Instalando dependencias de frontend..."
    npm ci
fi

# Instalar Playwright si no está instalado
if [ ! -d "node_modules/@playwright" ]; then
    log "Instalando Playwright..."
    npm install @playwright/test
    npx playwright install
fi

# Configurar variables para tests
export PLAYWRIGHT_BASE_URL=http://localhost:4201
export API_BASE_URL=http://localhost:8082/api/v1

# Ejecutar tests E2E
log "Ejecutando tests Playwright..."
if npx playwright test --reporter=html --output-dir=../test-results/e2e; then
    success "✓ Tests E2E completados exitosamente"
    test_result=0
else
    error "✗ Tests E2E fallaron"
    test_result=1
fi

cd ..

# Limpiar servicios de testing
log "Limpiando servicios de testing..."

cleanup_containers() {
    docker stop financial-nomad-frontend-test 2>/dev/null || true
    docker stop financial-nomad-backend-test 2>/dev/null || true
    docker stop financial-nomad-firestore-test 2>/dev/null || true
    
    docker rm financial-nomad-frontend-test 2>/dev/null || true
    docker rm financial-nomad-backend-test 2>/dev/null || true
    docker rm financial-nomad-firestore-test 2>/dev/null || true
}

# Configurar trap para limpiar en caso de interrupción
trap cleanup_containers EXIT

cleanup_containers

# Mostrar resultados
echo ""
echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
if [ $test_result -eq 0 ]; then
    echo -e "${BLUE}║                     ${GREEN}✅ TESTS EXITOSOS${BLUE}                      ║${NC}"
else
    echo -e "${BLUE}║                     ${RED}❌ TESTS FALLARON${BLUE}                      ║${NC}"
fi
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

if [ $test_result -eq 0 ]; then
    success "🎉 Todos los tests E2E pasaron correctamente"
    
    if [ -f "test-results/e2e/index.html" ]; then
        echo -e "${BLUE}📊 Reporte HTML:${NC} test-results/e2e/index.html"
    fi
else
    error "❌ Algunos tests E2E fallaron"
    
    if [ -f "test-results/e2e/index.html" ]; then
        echo -e "${YELLOW}📊 Reporte con detalles:${NC} test-results/e2e/index.html"
    fi
    
    echo ""
    echo "Para más detalles:"
    echo "  - Revisa los logs: ./devops/scripts/logs.sh"
    echo "  - Ejecuta tests individuales: cd frontend && npx playwright test --debug"
fi

echo ""
echo -e "${BLUE}🔄 Para volver al desarrollo:${NC} ./devops/scripts/dev-start.sh"

exit $test_result