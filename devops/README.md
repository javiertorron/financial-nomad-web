# DevOps - Financial Nomad

## Vision General

Este directorio contiene toda la configuración de infraestructura y despliegue para Financial Nomad, enfocado principalmente en el desarrollo local con Docker para testing de la implementación por fases.

## Estructura

```
devops/
├── docker/                     # Configuraciones Docker
│   ├── frontend/              # Dockerfiles frontend
│   ├── backend/               # Dockerfiles backend
│   └── nginx/                 # Proxy y routing
├── docker-compose/            # Archivos compose por entorno
│   ├── docker-compose.dev.yml
│   ├── docker-compose.test.yml
│   └── docker-compose.prod.yml
├── scripts/                   # Scripts de automatización
│   ├── dev-start.sh
│   ├── dev-stop.sh
│   ├── test-e2e.sh
│   └── backup-firestore.sh
├── firebase/                  # Configuración Firebase
│   ├── firestore.rules
│   ├── firestore.indexes.json
│   └── firebase.json
├── nginx/                     # Configuraciones Nginx
│   ├── dev.conf
│   ├── test.conf
│   └── prod.conf
└── monitoring/                # Observabilidad local
    ├── prometheus.yml
    └── grafana/
```

## Comandos Rápidos

```bash
# Iniciar entorno completo de desarrollo
./devops/scripts/dev-start.sh

# Parar entorno de desarrollo
./devops/scripts/dev-stop.sh

# Ejecutar tests E2E completos
./devops/scripts/test-e2e.sh

# Ver logs de todos los servicios
./devops/scripts/logs.sh

# Limpiar volúmenes y reiniciar
./devops/scripts/clean-restart.sh
```

## Entornos Disponibles

### 🔧 Desarrollo (development)
- Hot reload para frontend y backend
- Firestore Emulator con UI
- Debug habilitado
- Logs detallados

### 🧪 Testing (testing)
- Firestore Emulator aislado
- Configuración optimizada para CI/CD
- Coverage reports
- E2E testing automatizado

### 🚀 Producción Local (production-local)
- Configuración similar a producción
- SSL con certificados auto-firmados
- Nginx con optimizaciones
- Monitoring básico

## URLs por Entorno

### Desarrollo:
- **Frontend**: http://localhost:4200
- **Backend API**: http://localhost:8080
- **API Docs**: http://localhost:8080/docs
- **Firestore UI**: http://localhost:4000
- **Nginx Proxy**: http://localhost:80

### Testing:
- **Frontend**: http://localhost:4201
- **Backend API**: http://localhost:8081
- **Firestore UI**: http://localhost:4001

### Producción Local:
- **App Principal**: https://localhost:443
- **API**: https://localhost:443/api
- **Monitoring**: http://localhost:3000 (Grafana)