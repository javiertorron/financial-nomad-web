# Financial Nomad API

> 🏦 Personal finance management API with Asana integration and advanced analytics

[![Cloud Run](https://img.shields.io/badge/Google%20Cloud-Cloud%20Run-4285F4?logo=google-cloud)](https://cloud.google.com/run)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Firebase](https://img.shields.io/badge/Firebase-Firestore-FFCA28?logo=firebase)](https://firebase.google.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 🌟 Features

- 📊 **Complete Financial Management**: Accounts, transactions, categories, and budgets
- 📈 **Advanced Analytics**: Comprehensive reporting and insights
- 🔗 **Asana Integration**: Sync tasks and financial tracking
- 💾 **Backup & Export**: Full data export to JSON/CSV with Google Drive integration
- 🔐 **OAuth Authentication**: Secure Google OAuth integration
- 🚀 **High Performance**: Advanced caching, query optimization, and rate limiting
- 📊 **Monitoring**: Prometheus metrics and comprehensive health checks
- 🐳 **Cloud Native**: Optimized for Google Cloud Run deployment

## 📋 Requisitos

- Python 3.11+
- Docker (opcional, recomendado)
- Google Cloud SDK (para Firestore emulator)

## 🛠️ Configuración de desarrollo

### Opción 1: Setup automático

```bash
./scripts/dev_setup.sh
```

### Opción 2: Setup manual

1. **Crear entorno virtual:**
```bash
python3.11 -m venv venv
source venv/bin/activate
```

2. **Instalar dependencias:**
```bash
pip install -r requirements-dev.txt
```

3. **Configurar variables de entorno:**
```bash
cp .env.example .env
# Editar .env con tu configuración
```

4. **Instalar pre-commit hooks:**
```bash
pre-commit install
```

### Opción 3: Docker Compose

```bash
docker-compose up -d
```

## 🏃 Ejecución

### Desarrollo local
```bash
# Activar entorno virtual
source venv/bin/activate

# Ejecutar servidor de desarrollo
uvicorn src.main:app --reload --host 0.0.0.0 --port 8080
```

### Con Docker
```bash
docker-compose up
```

La API estará disponible en:
- **API**: http://localhost:8080
- **Documentación**: http://localhost:8080/docs
- **ReDoc**: http://localhost:8080/redoc

## 🧪 Testing

### Ejecutar todos los tests
```bash
./scripts/run_tests.sh
```

### Tests específicos
```bash
# Tests unitarios
pytest tests/unit -v

# Tests de integración
pytest tests/integration -v

# Tests E2E
pytest tests/e2e -v

# Con coverage
pytest --cov=src --cov-report=html
```

### Testing con Docker
```bash
docker-compose -f docker-compose.test.yml up --build
```

## 📁 Estructura del proyecto

```
backend/
├── src/                        # Código fuente
│   ├── config.py              # Configuración con Pydantic Settings
│   ├── main.py                # FastAPI app principal
│   ├── models/                # Modelos Pydantic
│   ├── routers/               # Endpoints API
│   ├── services/              # Lógica de negocio
│   ├── infrastructure/        # Clientes externos (DB, APIs)
│   ├── middleware/            # Middlewares custom
│   └── utils/                 # Utilidades y helpers
├── tests/                     # Tests
│   ├── unit/                  # Tests unitarios
│   ├── integration/           # Tests de integración
│   ├── e2e/                   # Tests end-to-end
│   ├── factories/             # Factories para datos de prueba
│   └── mocks/                 # Mocks reutilizables
├── scripts/                   # Scripts de utilidad
├── docs/                      # Documentación adicional
└── .github/workflows/         # CI/CD pipelines
```

## 🔧 Configuración

Las variables de entorno se configuran en `.env`:

```bash
# App
APP_NAME=financial-nomad-api
DEBUG=true
ENVIRONMENT=development

# Security
SECRET_KEY=your-secret-key
GOOGLE_CLIENT_ID=your-google-client-id

# Database
FIRESTORE_PROJECT_ID=your-project-id
USE_FIRESTORE_EMULATOR=true

# API
CORS_ORIGINS=["http://localhost:3000"]
```

## 🐳 Docker

### Desarrollo
```bash
docker-compose up -d
```

### Testing
```bash
docker-compose -f docker-compose.test.yml up --build
```

### Producción
```bash
docker build -t financial-nomad-api .
docker run -p 8080:8080 financial-nomad-api
```

## 🔒 Seguridad

- **Autenticación**: Google OAuth + JWT sessions
- **Autorización**: Role-based access control
- **Rate limiting**: Por IP address
- **Security headers**: OWASP recommendations
- **Input validation**: Pydantic strict validation
- **Dependency scanning**: Safety + Bandit

## 📊 Observabilidad

- **Logging estructurado**: JSON logs con structlog
- **Métricas**: Process time, request counts
- **Health checks**: Kubernetes-ready endpoints
- **Tracing**: Request IDs en headers

## 🚀 Deployment

### Google Cloud Run

```bash
# Build y push imagen
docker build -t gcr.io/PROJECT_ID/financial-nomad-api .
docker push gcr.io/PROJECT_ID/financial-nomad-api

# Deploy a Cloud Run
gcloud run deploy financial-nomad-api \
  --image gcr.io/PROJECT_ID/financial-nomad-api \
  --platform managed \
  --region us-central1 \
  --min-instances 0 \
  --max-instances 10
```

## 🛣️ Roadmap

### ✅ Fase 1: Fundamentos (Completada)
- [x] Estructura del proyecto
- [x] Configuración base
- [x] FastAPI app con middlewares
- [x] Framework de testing
- [x] CI/CD básico

### 🔄 Fase 2: Core Financiero (En progreso)
- [ ] Cliente Firestore
- [ ] Autenticación Google OAuth
- [ ] Gestión de cuentas
- [ ] Gestión de categorías
- [ ] CRUD de transacciones
- [ ] Importación YAML

### ⏳ Fase 3: Funcionalidades Avanzadas
- [ ] Elementos fijos (ingresos/gastos periódicos)
- [ ] Presupuestos por categoría
- [ ] Proyectos de ahorro
- [ ] Pagos diferidos

### ⏳ Fase 4: Integración Asana
- [ ] OAuth con Asana
- [ ] Sincronización de tareas
- [ ] Webhooks
- [ ] Mapeo de campos

### ⏳ Fase 5: Exportaciones y Ops
- [ ] Exportaciones para LLMs
- [ ] Backups a Google Drive
- [ ] Métricas avanzadas
- [ ] Optimizaciones

## 🤝 Contribución

1. Fork del proyecto
2. Crear feature branch (`git checkout -b feature/amazing-feature`)
3. Commit cambios (`git commit -m 'Add amazing feature'`)
4. Push a branch (`git push origin feature/amazing-feature`)
5. Abrir Pull Request

### Estándares de código

- **Formato**: Black + isort
- **Linting**: Ruff
- **Type checking**: mypy
- **Testing**: pytest con 85% coverage mínimo
- **Security**: Bandit scan

## 📄 Licencia

Este proyecto está bajo la licencia MIT - ver el archivo [LICENSE](LICENSE) para detalles.

## 📞 Soporte

- **Issues**: [GitHub Issues](https://github.com/your-org/financial-nomad/issues)
- **Docs**: [Documentación completa](../documentation/)
- **API Docs**: http://localhost:8080/docs (en desarrollo)