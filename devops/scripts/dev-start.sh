#!/bin/bash
set -e

# Colors para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para logging
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
║                 🚀 Entorno de Desarrollo                      ║
╚═══════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Verificar dependencias
log "Verificando dependencias..."

if ! command -v docker &> /dev/null; then
    error "Docker no está instalado. Por favor instala Docker primero."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    error "Docker Compose no está instalado. Por favor instala Docker Compose primero."
    exit 1
fi

# Verificar si Docker está corriendo
if ! docker ps &> /dev/null; then
    error "Docker no está ejecutándose. Por favor inicia Docker primero."
    exit 1
fi

success "✓ Docker está disponible"

# Cambiar al directorio del proyecto
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

log "Directorio del proyecto: $PROJECT_ROOT"

# Crear archivo .env si no existe
if [ ! -f .env ]; then
    log "Creando archivo .env desde plantilla..."
    
    if [ -f .env.example ]; then
        cp .env.example .env
        warning "⚠️  Archivo .env creado desde .env.example"
        warning "⚠️  Por favor configura las variables en .env antes de continuar"
        warning "⚠️  Especialmente GOOGLE_CLIENT_ID para OAuth"
        echo ""
        echo "Presiona Enter para continuar o Ctrl+C para salir..."
        read -r
    else
        log "Creando .env con valores por defecto..."
        cat > .env << EOL
# Configuración de desarrollo
NODE_ENV=development
DEBUG=true
ENVIRONMENT=development

# Seguridad (cambiar en producción)
SECRET_KEY=dev-secret-key-change-in-production-$(openssl rand -hex 16)

# Google OAuth (configurar con tu Client ID)
GOOGLE_CLIENT_ID=your-google-client-id-here

# Base de datos
USE_FIRESTORE_EMULATOR=true
FIRESTORE_EMULATOR_HOST=localhost:8081
FIRESTORE_PROJECT_ID=financial-nomad-dev

# URLs
API_URL=http://localhost:8080/api/v1
FRONTEND_URL=http://localhost:4200

# Logging
LOG_LEVEL=DEBUG

# Rate limiting (más permisivo en desarrollo)
RATE_LIMIT_PER_MINUTE=1000
EOL
        warning "⚠️  Archivo .env creado con valores por defecto"
        warning "⚠️  IMPORTANTE: Configura GOOGLE_CLIENT_ID en .env"
    fi
fi

# Verificar variables críticas
source .env

if [ -z "$GOOGLE_CLIENT_ID" ] || [ "$GOOGLE_CLIENT_ID" = "your-google-client-id-here" ]; then
    warning "⚠️  GOOGLE_CLIENT_ID no está configurado en .env"
    warning "⚠️  La autenticación OAuth no funcionará correctamente"
    echo ""
    echo "Para configurar Google OAuth:"
    echo "1. Ve a https://console.cloud.google.com/"
    echo "2. Crea un proyecto o selecciona uno existente"
    echo "3. Habilita Google+ API"
    echo "4. Crea credenciales OAuth 2.0"
    echo "5. Añade http://localhost:4200 a URIs autorizados"
    echo "6. Copia el Client ID al archivo .env"
    echo ""
    echo "¿Quieres continuar sin OAuth? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "Configura GOOGLE_CLIENT_ID en .env y ejecuta de nuevo."
        exit 1
    fi
fi

# Limpiar contenedores anteriores si existen
log "Limpiando contenedores anteriores..."
docker-compose -f devops/docker-compose/docker-compose.dev.yml down --remove-orphans 2>/dev/null || true

# Limpiar volúmenes si se solicita
if [ "$1" = "--clean" ]; then
    log "Limpiando volúmenes..."
    docker-compose -f devops/docker-compose/docker-compose.dev.yml down -v 2>/dev/null || true
    docker system prune -f
fi

# Crear directorios necesarios
log "Creando directorios necesarios..."
mkdir -p logs
mkdir -p frontend/node_modules
mkdir -p backend/.pytest_cache

# Construcción e inicio de servicios
log "Construyendo e iniciando servicios..."

# Exportar variables de entorno para docker-compose
export $(cat .env | grep -v ^# | xargs)

# Iniciar servicios en orden
log "Iniciando Firestore Emulator..."
docker-compose -f devops/docker-compose/docker-compose.dev.yml up -d firestore-emulator

# Esperar a que Firestore esté listo
log "Esperando Firestore Emulator..."
timeout=60
counter=0
while ! curl -s http://localhost:8081 > /dev/null 2>&1; do
    if [ $counter -eq $timeout ]; then
        error "Timeout esperando Firestore Emulator"
        docker-compose -f devops/docker-compose/docker-compose.dev.yml logs firestore-emulator
        exit 1
    fi
    sleep 2
    counter=$((counter + 2))
    echo -n "."
done
echo ""
success "✓ Firestore Emulator está listo"

# Iniciar backend
log "Iniciando Backend..."
docker-compose -f devops/docker-compose/docker-compose.dev.yml up -d backend

# Esperar a que backend esté listo
log "Esperando Backend API..."
timeout=120
counter=0
while ! curl -s http://localhost:8080/api/v1/health > /dev/null 2>&1; do
    if [ $counter -eq $timeout ]; then
        error "Timeout esperando Backend API"
        docker-compose -f devops/docker-compose/docker-compose.dev.yml logs backend
        exit 1
    fi
    sleep 2
    counter=$((counter + 2))
    echo -n "."
done
echo ""
success "✓ Backend API está listo"

# Iniciar frontend
log "Iniciando Frontend..."
docker-compose -f devops/docker-compose/docker-compose.dev.yml up -d frontend

# Esperar a que frontend esté listo
log "Esperando Frontend..."
timeout=180
counter=0
while ! curl -s http://localhost:4200 > /dev/null 2>&1; do
    if [ $counter -eq $timeout ]; then
        error "Timeout esperando Frontend"
        docker-compose -f devops/docker-compose/docker-compose.dev.yml logs frontend
        exit 1
    fi
    sleep 3
    counter=$((counter + 3))
    echo -n "."
done
echo ""
success "✓ Frontend está listo"

# Iniciar servicios adicionales
log "Iniciando servicios adicionales..."
docker-compose -f devops/docker-compose/docker-compose.dev.yml up -d redis mailhog

# Iniciar Nginx
log "Iniciando Nginx..."
docker-compose -f devops/docker-compose/docker-compose.dev.yml up -d nginx

# Verificar estado de todos los servicios
log "Verificando estado de servicios..."
sleep 5

services=(
    "firestore-emulator:8081"
    "backend:8080/api/v1/health"
    "frontend:4200"
    "nginx:80/health"
)

all_healthy=true
for service in "${services[@]}"; do
    IFS=':' read -r name endpoint <<< "$service"
    if curl -s http://localhost:"$endpoint" > /dev/null 2>&1; then
        success "✓ $name está funcionando"
    else
        error "✗ $name no responde"
        all_healthy=false
    fi
done

# Mostrar resumen
echo ""
echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                        🎉 ¡LISTO!                            ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

if [ "$all_healthy" = true ]; then
    success "🌐 Todos los servicios están funcionando correctamente"
    echo ""
    echo -e "${GREEN}🔗 URLs de acceso:${NC}"
    echo -e "   🌍 Frontend:      ${BLUE}http://localhost:4200${NC}"
    echo -e "   🔗 Backend API:   ${BLUE}http://localhost:8080/api/v1${NC}"
    echo -e "   📚 API Docs:      ${BLUE}http://localhost:8080/docs${NC}"
    echo -e "   🔥 Firestore UI:  ${BLUE}http://localhost:4000${NC}"
    echo -e "   📧 Mailhog:       ${BLUE}http://localhost:8025${NC}"
    echo -e "   🌐 Nginx Proxy:   ${BLUE}http://localhost:80${NC}"
    
    echo ""
    echo -e "${YELLOW}📋 Comandos útiles:${NC}"
    echo -e "   Ver logs:         ${BLUE}./devops/scripts/logs.sh${NC}"
    echo -e "   Parar servicios:  ${BLUE}./devops/scripts/dev-stop.sh${NC}"
    echo -e "   Reiniciar:        ${BLUE}./devops/scripts/dev-restart.sh${NC}"
    echo -e "   Ejecutar tests:   ${BLUE}./devops/scripts/test-e2e.sh${NC}"
    
    echo ""
    echo -e "${GREEN}🚀 ¡Listo para desarrollar!${NC}"
else
    error "❌ Algunos servicios no están funcionando correctamente"
    echo ""
    echo "Para ver logs detallados:"
    echo "  docker-compose -f devops/docker-compose/docker-compose.dev.yml logs"
    exit 1
fi