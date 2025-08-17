# Estrategia de Implementación Conjunta por Fases - Financial Nomad

## Visión General

Esta estrategia define la implementación incremental de Financial Nomad dividida en fases testables que integran frontend Angular y backend FastAPI. Cada fase proporciona funcionalidad completa end-to-end que puede ser probada localmente antes de proceder a la siguiente.

## 1. Principios de la Estrategia

### 1.1 Desarrollo Incremental
- **Fases autónomas**: Cada fase entrega valor funcional completo
- **Testeo continuo**: Testing manual y automatizado en cada fase
- **Integración temprana**: Frontend y backend se desarrollan en paralelo
- **Feedback rápido**: Validación de funcionalidad cada 1-2 semanas

### 1.2 Entorno de Desarrollo Local
- **Docker Compose**: Orquestación de servicios locales
- **Hot Reload**: Desarrollo con recarga automática
- **Base de datos**: Firestore Emulator para desarrollo
- **Proxy**: Nginx para routing entre frontend y backend

### 1.3 Criterios de Completitud por Fase
Para considerar una fase como completada debe cumplir:
- [ ] Backend: Endpoints implementados y testados
- [ ] Frontend: UI completamente funcional
- [ ] Integración: E2E tests pasando
- [ ] Documentación: APIs y componentes documentados
- [ ] Demo: Funcionalidad demostrable end-to-end

---

## 2. Configuración del Entorno de Desarrollo

### 2.1 Docker Compose para Desarrollo Local

```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  # Frontend Angular
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    ports:
      - "4200:4200"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    environment:
      - CHOKIDAR_USEPOLLING=true
    depends_on:
      - backend
    networks:
      - financial-nomad-network

  # Backend FastAPI  
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    ports:
      - "8080:8080"
    volumes:
      - ./backend:/app
    environment:
      - DEBUG=true
      - ENVIRONMENT=development
      - USE_FIRESTORE_EMULATOR=true
      - FIRESTORE_EMULATOR_HOST=firestore-emulator:8081
      - FIRESTORE_PROJECT_ID=financial-nomad-dev
      - SECRET_KEY=dev-secret-key-change-in-production
      - GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
    depends_on:
      - firestore-emulator
    networks:
      - financial-nomad-network

  # Firestore Emulator
  firestore-emulator:
    image: gcr.io/google.com/cloudsdktool/cloud-sdk:alpine
    ports:
      - "8081:8081"
      - "4000:4000"  # UI del emulador
    command: >
      bash -c "
        gcloud emulators firestore start 
        --project=financial-nomad-dev 
        --host-port=0.0.0.0:8081 
        --rules=./firestore.rules
      "
    volumes:
      - ./firebase/firestore.rules:/firestore.rules
      - firestore-data:/opt/data
    networks:
      - financial-nomad-network

  # Nginx Proxy (opcional para routing)
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx/nginx.dev.conf:/etc/nginx/nginx.conf
    depends_on:
      - frontend
      - backend
    networks:
      - financial-nomad-network

volumes:
  firestore-data:

networks:
  financial-nomad-network:
    driver: bridge
```

### 2.2 Dockerfiles de Desarrollo

**Frontend Dockerfile.dev**:
```dockerfile
# frontend/Dockerfile.dev
FROM node:20-alpine

WORKDIR /app

# Instalar Angular CLI globalmente
RUN npm install -g @angular/cli@18

# Copiar package files
COPY package*.json ./

# Instalar dependencias
RUN npm ci

# Copiar codigo fuente
COPY . .

# Exponer puerto
EXPOSE 4200

# Comando de desarrollo con hot reload
CMD ["ng", "serve", "--host", "0.0.0.0", "--port", "4200", "--poll=2000"]
```

**Backend Dockerfile.dev**:
```dockerfile
# backend/Dockerfile.dev  
FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements-dev.txt .

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements-dev.txt

# Copiar codigo fuente
COPY . .

# Exponer puerto
EXPOSE 8080

# Comando de desarrollo con hot reload
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]
```

### 2.3 Scripts de Desarrollo

```bash
#!/bin/bash
# scripts/dev-start.sh
echo "🚀 Iniciando entorno de desarrollo Financial Nomad..."

# Verificar dependencias
command -v docker >/dev/null 2>&1 || { echo "❌ Docker requerido" >&2; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "❌ Docker Compose requerido" >&2; exit 1; }

# Crear archivo .env si no existe
if [ ! -f .env ]; then
    echo "📋 Creando archivo .env desde template..."
    cp .env.example .env
    echo "⚠️  Por favor configura las variables en .env antes de continuar"
    exit 1
fi

# Iniciar servicios
echo "🔧 Iniciando servicios..."
docker-compose -f docker-compose.dev.yml up --build -d

# Esperar a que los servicios estén listos
echo "⏳ Esperando servicios..."
./scripts/wait-for-services.sh

echo "✅ Entorno listo!"
echo ""
echo "🌐 Frontend: http://localhost:4200"
echo "🔗 Backend API: http://localhost:8080"
echo "📊 API Docs: http://localhost:8080/docs" 
echo "🔥 Firestore UI: http://localhost:4000"
echo ""
echo "📋 Para ver logs: docker-compose -f docker-compose.dev.yml logs -f"
echo "🛑 Para parar: docker-compose -f docker-compose.dev.yml down"
```

```bash
#!/bin/bash
# scripts/wait-for-services.sh
echo "Esperando Firestore Emulator..."
until curl -s http://localhost:8081 > /dev/null; do
    sleep 2
done
echo "✅ Firestore Emulator listo"

echo "Esperando Backend..."
until curl -s http://localhost:8080/health > /dev/null; do
    sleep 2  
done
echo "✅ Backend listo"

echo "Esperando Frontend..."
until curl -s http://localhost:4200 > /dev/null; do
    sleep 2
done
echo "✅ Frontend listo"
```

---

## 3. FASE 1: AUTENTICACIÓN Y SETUP BASE (2 semanas)

### 3.1 Objetivos de la Fase
- Configurar entorno de desarrollo local completo
- Implementar autenticación Google OAuth end-to-end
- Crear layout base de la aplicación
- Establecer CI/CD básico

### 3.2 Implementación Backend (Semana 1)

**Sprint 1.1: Setup y Configuración (3 días)**
```bash
Día 1-2: Estructura del proyecto y configuración
- Crear estructura de directorios backend
- Configurar requirements.txt y dependencias
- Implementar Pydantic Settings
- Configurar Dockerfile.dev y docker-compose
- Setup testing con pytest

Día 3: Health checks y middleware básico
- Implementar endpoint /health
- Configurar middleware de logging y errores
- Setup Firestore emulator connection
- Configurar CI/CD básico con GitHub Actions
```

**Sprint 1.2: Autenticación (4 días)**
```bash
Día 4-5: Modelos y servicios de auth
- Implementar modelos User, Session, Invitation
- Crear AuthService con Google OAuth
- Implementar JWT token management
- Setup Firestore collections y rules

Día 6-7: Endpoints de autenticación
- POST /auth/login (Google OAuth)
- POST /auth/logout  
- GET /auth/profile
- POST /auth/invite
- Middleware de autenticación para rutas protegidas
```

### 3.3 Implementación Frontend (Semana 2)

**Sprint 1.3: Setup Angular (3 días)**
```bash
Día 8-9: Proyecto base y configuración
- Crear proyecto Angular 18 con standalone components
- Configurar Angular Material y tema personalizado
- Setup path mapping y estructura de directorios
- Configurar testing (Jest + Angular Testing Library)

Día 10: Servicios y guards base
- Implementar AuthService con Signals
- Crear HTTP interceptors (auth, error, loading)
- Implementar AuthGuard y GuestGuard
- Setup routing con lazy loading
```

**Sprint 1.4: UI de Autenticación (4 días)**
```bash
Día 11-12: Componentes de auth
- Crear LoginComponent con Google OAuth
- Implementar layout base (ShellComponent)
- Crear componentes de navegación
- Setup de formularios reactivos

Día 13-14: Integración y testing
- Integrar frontend con backend auth
- Implementar manejo de errores
- Testing end-to-end básico
- Documentar APIs y componentes
```

### 3.4 Criterios de Aceptación Fase 1

**Funcionalidad**:
- [ ] Usuario puede hacer login con Google OAuth
- [ ] Sesión se mantiene en refresh de página
- [ ] Usuario puede hacer logout
- [ ] Rutas protegidas funcionan correctamente
- [ ] Error handling para auth funciona

**Testing**:
- [ ] Backend: Tests unitarios auth ≥ 90% coverage
- [ ] Frontend: Tests unitarios auth ≥ 85% coverage  
- [ ] E2E: Login/logout flow completo
- [ ] Manual: Flujo de auth probado en 3 navegadores

**Demo Script Fase 1**:
```bash
# 1. Iniciar entorno
./scripts/dev-start.sh

# 2. Abrir http://localhost:4200
# 3. Verificar redirect a /auth/login
# 4. Hacer click en "Login with Google"
# 5. Verificar redirect a /app/dashboard
# 6. Hacer logout
# 7. Verificar redirect a /auth/login
```

---

## 4. FASE 2: DASHBOARD Y TRANSACCIONES BÁSICAS (3 semanas)

### 4.1 Objetivos de la Fase
- Dashboard financiero con métricas básicas
- CRUD completo de transacciones
- Gestión básica de cuentas y categorías
- Visualización de datos financieros

### 4.2 Implementación Backend (Semana 3-4)

**Sprint 2.1: Modelos Financieros (5 días)**
```bash
Día 15-16: Modelos de datos
- Implementar Account, Category, Transaction models
- Configurar Firestore schemas y validation
- Crear factory patterns para testing
- Setup database migrations/fixtures

Día 17-19: Servicios CRUD
- AccountService con operaciones CRUD
- CategoryService con jerarquías  
- TransactionService con filtros y paginación
- Implementar business logic y validaciones
```

**Sprint 2.2: APIs REST (5 días)**
```bash
Día 20-21: Endpoints de cuentas
- GET /accounts (list con filtros)
- POST /accounts (create)
- PUT /accounts/{id} (update)  
- DELETE /accounts/{id} (soft delete)
- GET /accounts/{id}/balance

Día 22-24: Endpoints de transacciones  
- GET /transactions (list paginada con filtros)
- POST /transactions (create)
- PUT /transactions/{id} (update)
- DELETE /transactions/{id} (soft delete)
- GET /dashboard/summary (métricas básicas)
```

### 4.3 Implementación Frontend (Semana 5)

**Sprint 2.3: Dashboard y Componentes Base (5 días)**
```bash
Día 25-26: Dashboard
- DashboardComponent con métricas
- Balance summary cards
- Recent transactions list
- Quick actions para crear transacciones

Día 27-29: Gestión de Transacciones
- TransactionListComponent con filtros
- TransactionFormComponent (crear/editar)
- Transaction cards y tabla
- Paginación y búsqueda
```

### 4.4 Criterios de Aceptación Fase 2

**Funcionalidad**:
- [ ] Dashboard muestra balance total y métricas del mes
- [ ] Usuario puede crear/editar/eliminar transacciones
- [ ] Lista de transacciones con filtros funciona
- [ ] CRUD de cuentas básico funciona
- [ ] Validaciones frontend/backend consistentes

**Testing**:
- [ ] Backend: APIs con tests de integración
- [ ] Frontend: Componentes con tests unitarios
- [ ] E2E: Flujo completo crear transacción
- [ ] Performance: Dashboard carga <2s

**Demo Script Fase 2**:
```bash
# 1. Login exitoso
# 2. Ver dashboard con balance €0.00
# 3. Crear cuenta "Banco Principal" €1000
# 4. Crear categoría "Alimentación" 
# 5. Crear transacción gasto "Supermercado" €50
# 6. Verificar balance actualizado €950
# 7. Ver transacción en lista
# 8. Editar transacción cambiar monto €45
# 9. Verificar balance actualizado €955
```

---

## 5. FASE 3: CATEGORÍAS Y PRESUPUESTOS (2 semanas)

### 5.1 Objetivos de la Fase
- Gestión completa de categorías con jerarquías
- Sistema de presupuestos por categoría
- Alertas de presupuesto
- Reportes básicos por categoría

### 5.2 Implementación Backend (Semana 6)

**Sprint 3.1: Categorías Avanzadas (7 días)**
```bash
Día 30-31: Jerarquías de categorías
- Implementar parent-child relationships
- Endpoints para categorías anidadas
- Validaciones de circularidad
- Bulk operations para categorías

Día 32-34: Sistema de presupuestos
- Budget model con períodos
- BudgetService con alertas automáticas
- Cálculo de gastos por categoría
- Endpoints de presupuestos CRUD

Día 35-36: Reportes básicos
- CategorySpending aggregations
- Monthly/yearly breakdowns
- Top categories endpoint
- Budget vs actual reports
```

### 5.3 Implementación Frontend (Semana 7)

**Sprint 3.2: UI Categorías y Presupuestos (7 días)**
```bash
Día 37-38: Gestión de categorías
- CategoryListComponent con tree view
- CategoryFormComponent con parent selector
- Drag & drop para reordenar
- Color picker y iconos

Día 39-41: Sistema de presupuestos
- BudgetListComponent con progress bars
- BudgetFormComponent con validaciones
- Budget alerts y notificaciones
- Charts para presupuesto vs gasto real

Día 42-43: Reportes y visualización
- CategoryReportComponent
- Pie charts por categoría
- Bar charts presupuesto vs real
- Export básico a CSV
```

### 5.4 Criterios de Aceptación Fase 3

**Funcionalidad**:
- [ ] Categorías con subcategorías funcionan
- [ ] Presupuestos por categoría se crean y monitorean
- [ ] Alertas cuando se supera 80% del presupuesto
- [ ] Reportes muestran spending por categoría
- [ ] Visualización con charts interactivos

**Demo Script Fase 3**:
```bash
# 1. Crear categoría principal "Gastos Hogar"
# 2. Crear subcategorías "Alimentación", "Limpieza"
# 3. Crear presupuesto €300 para "Alimentación"
# 4. Crear varias transacciones hasta €250
# 5. Ver alerta de presupuesto en 83%
# 6. Ver reporte de gastos por categoría
# 7. Exportar reporte a CSV
```

---

## 6. FASE 4: IMPORTACIÓN YAML Y FUNCIONES AVANZADAS (2 semanas)

### 6.1 Objetivos de la Fase
- Importación masiva de transacciones vía YAML
- Elementos fijos (ingresos/gastos recurrentes)
- Mejoras de UX y performance
- PWA básico

### 6.2 Implementación Backend (Semana 8)

**Sprint 4.1: Importación YAML (7 días)**
```bash
Día 44-45: Parser YAML
- YAMLImportService con validaciones
- Mapeo de categorías automático
- Detección de duplicados
- Preview antes de importar

Día 46-48: Elementos recurrentes
- RecurringTransaction model
- Job scheduler para ejecución automática
- Templates de transacciones comunes
- Notificaciones de elementos vencidos

Día 49-50: Optimizaciones
- Caching inteligente con Redis
- Batch operations para performance
- Índices de base de datos optimizados
- Rate limiting por usuario
```

### 6.3 Implementación Frontend (Semana 9)

**Sprint 4.2: Import UI y PWA (7 días)**
```bash
Día 51-52: Importación UI
- YamlImportComponent con drag & drop
- Preview de transacciones a importar
- Progress bar para imports largos
- Error handling detallado

Día 53-55: Elementos recurrentes UI
- RecurringTransactionComponent
- Calendar view para elementos programados
- Quick templates para gastos comunes
- Notification system

Día 56-57: PWA y optimizaciones
- Service Worker básico
- Offline detection
- Performance optimizations
- Lazy loading mejorado
```

### 6.4 Criterios de Aceptación Fase 4

**Funcionalidad**:
- [ ] Import YAML funciona con validación
- [ ] Elementos recurrentes se ejecutan automáticamente
- [ ] PWA instala correctamente
- [ ] Performance optimizada (LCP <2.5s)
- [ ] Funcionalidad básica offline

**Demo Script Fase 4**:
```bash
# 1. Crear archivo YAML con 20 transacciones
# 2. Importar vía drag & drop
# 3. Preview y corregir errores
# 4. Confirmar import
# 5. Crear elemento recurrente "Salario" mensual
# 6. Instalar PWA
# 7. Probar offline básico
```

---

## 7. FASE 5: INTEGRACIÓN ASANA (OPCIONAL - 2 semanas)

### 7.1 Objetivos de la Fase
- OAuth con Asana
- Sincronización de tareas financieras
- Webhooks para updates automáticos
- Dashboard integrado

### 7.2 Implementación Backend (Semana 10)

**Sprint 5.1: Asana Integration (7 días)**
```bash
Día 58-59: OAuth Asana
- AsanaOAuthService
- Secure token storage
- Workspace selection
- User permissions

Día 60-62: Sincronización
- Task mapping a transacciones
- Webhook endpoints
- Sync service con rate limiting
- Conflict resolution

Día 63-64: Dashboard integration
- Asana tasks en dashboard
- Financial task templates
- Status tracking
```

### 7.3 Implementación Frontend (Semana 11)

**Sprint 5.2: Asana UI (7 días)**
```bash
Día 65-66: Configuración Asana
- Asana connect flow
- Settings para mapping
- Workspace selector
- Task preview

Día 67-69: Dashboard Asana
- Asana tasks en sidebar
- Quick create financial tasks
- Status indicators
- Sync notifications

Día 70-71: Testing y polish
- E2E tests con Asana
- Error handling
- Performance testing
```

---

## 8. Testing y Deployment Strategy

### 8.1 Testing por Fases

**Unit Tests**:
```bash
# Backend
pytest --cov=src tests/unit/
coverage html

# Frontend  
npm run test:coverage
```

**Integration Tests**:
```bash
# Backend con Firestore Emulator
pytest tests/integration/

# Frontend con MSW
npm run test:integration
```

**E2E Tests**:
```bash
# Con Playwright
npm run e2e:dev
```

### 8.2 CI/CD Pipeline

```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements-test.txt
      
      - name: Run tests
        run: |
          cd backend
          pytest --cov=src tests/

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      
      - name: Install dependencies
        run: |
          cd frontend
          npm ci
      
      - name: Run tests
        run: |
          cd frontend
          npm run test:ci

  e2e-tests:
    needs: [backend-tests, frontend-tests]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Start services
        run: |
          docker-compose -f docker-compose.dev.yml up -d
          ./scripts/wait-for-services.sh
      
      - name: Run E2E tests
        run: |
          cd frontend
          npm run e2e:ci
      
      - name: Cleanup
        run: docker-compose -f docker-compose.dev.yml down
```

### 8.3 Quality Gates por Fase

**Code Coverage**:
- Backend: ≥ 80% unit test coverage
- Frontend: ≥ 75% unit test coverage
- E2E: Flujos críticos cubiertos

**Performance**:
- API response time: <500ms p95
- Frontend FCP: <2s
- Frontend LCP: <2.5s

**Security**:
- OWASP dependency scan: No high/critical
- Secrets scanning: Clean
- CORS configurado correctamente

---

## 9. Documentación y Handoff

### 9.1 Documentación por Fase

**API Documentation**:
- OpenAPI/Swagger actualizado automáticamente
- Ejemplos de requests/responses
- Error codes documentados

**Frontend Documentation**:
- Component library con Storybook
- User guides para cada feature
- Deployment instructions

### 9.2 Demo Scripts

Cada fase incluye scripts detallados para demostrar funcionalidad:

```bash
# scripts/demo-fase-1.sh
#!/bin/bash
echo "🎬 Demo Fase 1: Autenticación"

echo "1. Iniciando entorno..."
./scripts/dev-start.sh

echo "2. Abriendo aplicación..."
open http://localhost:4200

echo "3. Sigue estos pasos:"
echo "   - Click 'Login with Google'"
echo "   - Autorizar aplicación"  
echo "   - Verificar dashboard cargado"
echo "   - Click logout"
echo "   - Verificar redirect a login"

echo "✅ Demo completado!"
```

---

## 10. Cronograma y Milestones

### 10.1 Timeline General

```
Semana 1-2:  Fase 1 - Autenticación ✅
Semana 3-5:  Fase 2 - Dashboard y Transacciones ✅  
Semana 6-7:  Fase 3 - Categorías y Presupuestos ✅
Semana 8-9:  Fase 4 - Import YAML y PWA ✅
Semana 10-11: Fase 5 - Asana (Opcional) ⏳
```

### 10.2 Milestones de Entrega

**M1 - MVP Funcional (Semana 5)**:
- Autenticación completa
- CRUD transacciones básico
- Dashboard con métricas

**M2 - Feature Complete (Semana 7)**:
- Presupuestos funcionales
- Categorías con jerarquías  
- Reportes básicos

**M3 - Production Ready (Semana 9)**:
- Import YAML
- PWA funcional
- Performance optimizada

**M4 - Extended (Semana 11)**:
- Integración Asana
- Features avanzadas
- Monitoring completo

---

## Conclusión

Esta estrategia de implementación por fases asegura:

1. **Entrega incremental de valor** con funcionalidad testeable
2. **Feedback temprano** en cada milestone
3. **Integración continua** entre frontend y backend
4. **Quality gates** en cada fase
5. **Documentación actualizada** progresivamente

Cada fase construye sobre la anterior, permitiendo detectar y corregir problemas tempranamente, manteniendo alta calidad de código y experiencia de usuario.