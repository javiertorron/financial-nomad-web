# Financial Nomad - Deployment Scripts

Este directorio contiene los scripts de despliegue para la aplicación Financial Nomad.

## Scripts Disponibles

### `deploy-backend.sh`
Despliega el backend FastAPI en Google Cloud Run.

**Funcionalidades:**
- Valida prerrequisitos y autenticación
- Habilita APIs necesarias de GCP
- Configura Artifact Registry
- Crea service account con permisos apropiados
- Configura secrets (con placeholders)
- Construye imagen Docker
- Despliega a Cloud Run
- Valida el despliegue

**Uso:**
```bash
PROJECT_ID=tu-proyecto ./deploy-backend.sh
```

### `deploy-frontend.sh`
Despliega el frontend Angular en Firebase Hosting.

**Funcionalidades:**
- Valida prerrequisitos (Node.js, Firebase CLI)
- Instala dependencias npm
- Construye la aplicación Angular para producción
- Configura Firebase Hosting
- Despliega a Firebase Hosting
- Valida el despliegue

**Uso:**
```bash
PROJECT_ID=tu-proyecto ./deploy-frontend.sh
```

### `deploy-full.sh`
Script unificado que despliega tanto backend como frontend.

**Funcionalidades:**
- Ejecuta tests (opcional)
- Despliega backend y/o frontend
- Valida integración completa
- Proporciona resumen del despliegue

**Uso:**
```bash
# Despliegue completo
PROJECT_ID=tu-proyecto ./deploy-full.sh

# Solo backend
PROJECT_ID=tu-proyecto DEPLOY_FRONTEND=false ./deploy-full.sh

# Solo frontend  
PROJECT_ID=tu-proyecto DEPLOY_BACKEND=false ./deploy-full.sh

# Sin tests
PROJECT_ID=tu-proyecto SKIP_TESTS=true ./deploy-full.sh
```

## Variables de Entorno

| Variable | Descripción | Por Defecto | Requerido |
|----------|-------------|-------------|-----------|
| `PROJECT_ID` | ID del proyecto GCP | - | ✅ |
| `REGION` | Región de despliegue | `us-central1` | ❌ |
| `FIREBASE_PROJECT` | ID del proyecto Firebase | `$PROJECT_ID` | ❌ |
| `DEPLOY_BACKEND` | Desplegar backend | `true` | ❌ |
| `DEPLOY_FRONTEND` | Desplegar frontend | `true` | ❌ |
| `SKIP_TESTS` | Omitir tests | `false` | ❌ |

## Prerrequisitos

### Para Backend
- Google Cloud CLI instalado y autenticado
- Docker (para builds locales, opcional)
- Proyecto GCP configurado

### Para Frontend
- Node.js 18+
- npm o yarn
- Firebase CLI instalado y autenticado
- Angular CLI (global o via npx)

### Servicios GCP Necesarios
Los scripts habilitarán automáticamente:
- Cloud Build API
- Cloud Run API
- Container Registry API / Artifact Registry API
- Secret Manager API
- Firestore API
- Logging API
- Monitoring API

## Configuración de Secretos

Los scripts crean automáticamente los siguientes secrets con valores placeholder:

### Backend
- `jwt-secret-key`: Clave para firmar JWT tokens
- `session-secret-key`: Clave para cookies de sesión
- `asana-client-secret`: Secret de OAuth para Asana
- `google-service-account-key`: Credenciales de servicio

**Actualizar secrets:**
```bash
# Ejemplo para JWT secret
echo "tu-jwt-secret-super-seguro" | gcloud secrets versions add jwt-secret-key --data-file=- --project=tu-proyecto

# Desde archivo
gcloud secrets versions add google-service-account-key --data-file=service-account.json --project=tu-proyecto
```

## Arquitectura de Despliegue

```
┌─────────────────────┐    ┌─────────────────────┐
│   Frontend (SPA)    │    │    Backend (API)    │
│                     │    │                     │
│  Firebase Hosting   │────│    Cloud Run        │
│  • Angular App      │    │  • FastAPI          │
│  • Static Assets    │    │  • Python 3.11      │
│  • Service Worker   │    │  • Container        │
└─────────────────────┘    └─────────────────────┘
           │                           │
           │                           │
           ▼                           ▼
┌─────────────────────┐    ┌─────────────────────┐
│     Firestore       │    │   Secret Manager    │
│  • Auth Data        │    │  • JWT Keys         │
│  • Financial Data   │    │  • API Secrets      │
│  • User Profiles    │    │  • Service Account  │
└─────────────────────┘    └─────────────────────┘
```

## ⚠️ FREE TIER ÚNICAMENTE - Sin Costos

Los scripts están **estrictamente diseñados para operar SOLO dentro del free tier de GCP**:

### Cloud Run (Always Free)
- ✅ 2M requests/mes
- ✅ 400,000 GB-seconds/mes  
- ✅ Configuración: 512MB RAM, 1 vCPU, max 1 instancia
- ✅ Container Registry (no Artifact Registry)

### Firebase Hosting (Spark Plan - Free)
- ✅ 10GB storage
- ✅ 360MB/día de transferencia
- ✅ SSL certificates incluidos

### Firestore (Spark Plan - Free)
- ✅ 50,000 reads/día
- ✅ 20,000 writes/día
- ✅ 1GB storage

### Cloud Build (Free Tier)
- ✅ 120 build-minutes/día

### Secret Manager (Free Tier)
- ✅ 6 secret versions activas
- ✅ 10,000 access operations/mes

**🚫 NO SE USAN SERVICIOS DE PAGO:**
- ❌ Artifact Registry (usa Container Registry gratuito)
- ❌ Cloud Logging/Monitoring premium
- ❌ Instancias múltiples de Cloud Run

## Troubleshooting

### Errores Comunes

**"Not authenticated with gcloud"**
```bash
gcloud auth login
gcloud config set project tu-proyecto
```

**"Firebase login required"**
```bash
firebase login
firebase use tu-proyecto
```

**"Node.js version too old"**
```bash
# Instalar Node.js 18+ desde nodejs.org
node --version  # Verificar versión
```

**"Build failed"**
```bash
# Backend
cd backend && python -m pytest tests/
docker build -f Dockerfile.production .

# Frontend  
cd frontend && npm install
npm run build --prod
```

### Logs y Monitoreo

**Cloud Run logs:**
```bash
gcloud logs read --project=tu-proyecto \
  --filter="resource.type=cloud_run_revision AND resource.labels.service_name=financial-nomad-api"
```

**Firebase Hosting logs:**
```bash
firebase hosting:channel:list --project=tu-proyecto
```

**Métricas de performance:**
- Cloud Console > Cloud Run > financial-nomad-api
- Firebase Console > Hosting > Usage

## Desarrollo y CI/CD

Estos scripts pueden integrarse en pipelines de CI/CD:

### GitHub Actions Example
```yaml
- name: Deploy Backend
  env:
    PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
  run: ./devops/scripts/deploy-backend.sh

- name: Deploy Frontend  
  env:
    PROJECT_ID: ${{ secrets.FIREBASE_PROJECT_ID }}
  run: ./devops/scripts/deploy-frontend.sh
```

### Cloud Build Integration
```yaml
steps:
- name: 'gcr.io/cloud-builders/gcloud'
  entrypoint: 'bash'
  args: ['./devops/scripts/deploy-full.sh']
  env:
  - 'PROJECT_ID=$PROJECT_ID'
```

## Seguridad

- Nunca incluir secrets en el código fuente
- Usar Secret Manager para datos sensibles
- Revisar permisos de service accounts regularmente
- Habilitar audit logs en producción
- Configurar alertas de seguridad

## Soporte

Para problemas con los scripts:
1. Verificar prerequisites y autenticación
2. Revisar logs de despliegue
3. Consultar documentación oficial de GCP/Firebase
4. Crear issue en el repositorio