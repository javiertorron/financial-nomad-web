# Arquitectura del Backend — Financial Nomad

> **Ambito**: arquitectura tecnica del backend (FastAPI + Python)  
> **Enfoque**: security-first, stateless, $0 coste en GCP  
> **Integracion**: Firestore nativo, OAuth Google, Asana API, Google Drive API

---

## 1. Vision general de la arquitectura

### 1.1 Principios arquitectonicos
- **API REST stateless**: sin sesiones persistentes en el servidor
- **Security-first**: validacion estricta de autenticacion/autorizacion en cada endpoint
- **Aislamiento por usuario**: acceso exclusivo a recursos propios via `uid`
- **Idempotencia**: operaciones seguras ante reintentos
- **Cero coste**: diseñado para operar dentro del free tier de GCP

### 1.2 Stack tecnologico
- **Framework**: FastAPI (Python 3.11+)
- **Validacion**: Pydantic v2
- **Base de datos**: Firestore (modo nativo)
- **Autenticacion**: Google ID Token + Firebase Auth
- **Despliegue**: Cloud Run (Always Free)
- **Documentacion**: OpenAPI/Swagger automatico
- **Integraciones**: Asana API, Google Drive API

---

## 2. Arquitectura de capas

```
┌─────────────────────────────────────┐
│        Capa de Presentacion         │
│    (FastAPI Routes + OpenAPI)       │
├─────────────────────────────────────┤
│        Capa de Aplicacion           │
│   (Services + Business Logic)       │
├─────────────────────────────────────┤
│        Capa de Dominio              │
│     (Models + Domain Logic)         │
├─────────────────────────────────────┤
│      Capa de Infraestructura        │
│ (Firestore + External APIs + Auth)  │
└─────────────────────────────────────┘
```

### 2.1 Capa de Presentacion (Routes)
- **Responsabilidad**: endpoints HTTP, validacion de entrada, serializacion
- **Componentes**:
  - `routers/auth.py`: autenticacion y gestion de invitaciones
  - `routers/accounts.py`: gestion de cuentas y metodos de pago
  - `routers/categories.py`: categorias de ingresos/gastos
  - `routers/transactions.py`: transacciones y fijos
  - `routers/budgets.py`: presupuestos por categoria
  - `routers/savings.py`: proyectos de ahorro
  - `routers/deferred_payments.py`: pagos diferidos (prestamos/hipotecas)
  - `routers/exports.py`: exportaciones para LLMs
  - `routers/asana.py`: integracion con Asana
  - `routers/health.py`: health checks y metricas

### 2.2 Capa de Aplicacion (Services)
- **Responsabilidad**: logica de negocio, orquestacion, transacciones
- **Componentes**:
  - `services/auth_service.py`: validacion de tokens, gestion de usuarios
  - `services/financial_service.py`: logica financiera core
  - `services/asana_service.py`: sincronizacion e ingesta desde Asana
  - `services/export_service.py`: generacion de snapshots para LLMs
  - `services/backup_service.py`: replica manual a Google Drive

### 2.3 Capa de Dominio (Models)
- **Responsabilidad**: entidades de negocio, validaciones de dominio
- **Componentes**:
  - `models/user.py`: usuario, configuracion de ahorro
  - `models/invitation.py`: invitaciones por email
  - `models/financial.py`: cuentas, categorias, transacciones, fijos
  - `models/budgets.py`: presupuestos y seguimiento
  - `models/savings.py`: proyectos de ahorro
  - `models/deferred.py`: pagos diferidos
  - `models/asana.py`: configuracion e integracion Asana

### 2.4 Capa de Infraestructura
- **Responsabilidad**: persistencia, servicios externos, configuracion
- **Componentes**:
  - `infrastructure/firestore_client.py`: cliente Firestore
  - `infrastructure/auth_client.py`: verificacion Google ID Token
  - `infrastructure/asana_client.py`: cliente API Asana
  - `infrastructure/drive_client.py`: cliente Google Drive API
  - `infrastructure/config.py`: configuracion y secrets

---

## 3. Modelo de datos (Firestore)

### 3.1 Estructura de colecciones
```
firestore/
├── users/{uid}                          # Perfil y configuracion usuario
├── invitations/{code}                   # Invitaciones por email
├── accounts/{uid}/                      # Datos financieros por usuario
│   ├── bank_accounts/{account_id}       # Cuentas bancarias
│   ├── categories/{category_id}         # Categorias personalizadas
│   ├── transactions/{transaction_id}    # Transacciones individuales
│   ├── fixed_items/{fixed_id}          # Ingresos/gastos fijos
│   ├── budgets/{budget_id}             # Presupuestos por categoria
│   ├── savings_projects/{project_id}    # Proyectos de ahorro
│   └── deferred_payments/{payment_id}   # Pagos diferidos
├── integrations/{uid}/                  # Integraciones externas
│   └── asana/                          # Configuracion Asana usuario
└── exports/{uid}/                       # Metadatos exportaciones LLM
    └── {export_id}
```

### 3.2 Reglas de seguridad Firestore
```javascript
// Acceso exclusivo por uid autenticado
match /users/{uid} {
  allow read, write: if request.auth != null && request.auth.uid == uid;
}

match /accounts/{uid}/{document=**} {
  allow read, write: if request.auth != null && request.auth.uid == uid;
}

// Solo admins pueden gestionar invitaciones
match /invitations/{code} {
  allow read, write: if request.auth != null && 
    get(/databases/$(database)/documents/users/$(request.auth.uid)).data.role == 'admin';
}
```

### 3.3 Indices compuestos necesarios
- `transactions`: `(uid, date desc)`, `(uid, category, date desc)`, `(uid, account, date desc)`
- `budgets`: `(uid, category, period)`
- `fixed_items`: `(uid, active, next_occurrence)`

---

## 4. Autenticacion y autorizacion

### 4.1 Flujo de autenticacion
```
Frontend → Google OAuth → ID Token → Backend Validation → Session Cookie
```

1. Usuario se autentica con Google (frontend)
2. Frontend recibe Google ID Token
3. Backend valida token con Google API
4. Backend verifica que email tiene invitacion valida
5. Backend genera session cookie (httpOnly, SameSite)

### 4.2 Middleware de autenticacion
```python
@router.middleware("http")
async def auth_middleware(request: Request, call_next):
    # Validar session cookie o Authorization header
    # Extraer uid del token validado
    # Inyectar user_context en request.state
    pass
```

### 4.3 Autorizacion por recurso
- **Principio**: cada endpoint valida que `request.state.uid` coincide con el propietario del recurso
- **Admins**: pueden gestionar invitaciones y acceder a metricas globales
- **Users**: acceso exclusivo a sus propios recursos

---

## 5. Integracion con Asana

### 5.1 Arquitectura de sincronizacion
```
Usuario → Configuracion Asana → OAuth → Mapeo Secciones → Sync On-Demand
                                                              ↓
Asana API ← Leer Tareas Pendientes ← Validar Proyecto/Secciones
    ↓
Crear Transacciones → Mover Tareas a Procesados → Resumen Sync
```

### 5.2 Componentes de integracion
- **OAuth Flow**: `/asana/oauth/authorize` y `/asana/oauth/callback`
- **Configuracion**: seleccion de proyecto y mapeo de 4 secciones obligatorias
- **Sincronizacion**: `/asana/sync` (on-demand, idempotente)
- **Webhooks**: `/asana/webhook` (recepcion de eventos, trigger sync)

### 5.3 Reglas de ingesta
- **Idempotencia**: campo `external_ref` en transacciones con ID de tarea Asana
- **Extraccion de datos**:
  - Monto: regex en titulo/notas (`€123,45`, `123.45 EUR`)
  - Fecha: due_date de tarea o fecha actual
  - Categoria: etiquetas/secciones o "Sin clasificar"
  - Cuenta: mapeo por keywords o cuenta predeterminada
- **Manejo de errores**: tareas sin monto quedan en "pendientes" con flag "requiere revision"

---

## 6. Exportaciones para LLMs

### 6.1 Arquitectura de exportes
```
Usuario → Solicitud Export → Generar Snapshot → Anonimizar → Crear Enlace Temporal
```

### 6.2 Proceso de anonimizacion
- Eliminar PII: nombres, emails, descripciones con datos personales
- Sustituir por codigos: `CATEGORY_001`, `ACCOUNT_002`, etc.
- Normalizar: fechas ISO-8601, montos en centimos, monedas ISO-4217
- Estructura: `snapshot.json` + `instructions.md` + `constraints.md`

### 6.3 Almacenamiento temporal
- Generar enlace firmado (Cloud Storage) con TTL corto (24h)
- Metadatos en Firestore: fecha, rango, tipos incluidos, estado

---

## 7. Gestion de configuracion y secrets

### 7.1 Variables de entorno
```python
class Settings(BaseSettings):
    # App
    app_name: str = "financial-nomad-api"
    debug: bool = False
    cors_origins: List[str] = []
    
    # GCP
    project_id: str
    firestore_database: str = "(default)"
    
    # Auth
    google_client_id: str
    session_secret_key: str
    
    # Integrations
    asana_client_id: str
    asana_client_secret: str  # From Secret Manager
    drive_credentials_path: str
```

### 7.2 Secret Manager
- `asana_client_secret`: credenciales OAuth Asana
- `session_secret_key`: firma de cookies de sesion
- `google_service_account`: credenciales para APIs de Google

---

## 8. Observabilidad y monitoreo

### 8.1 Logging estructurado
```python
import structlog

logger = structlog.get_logger()

@router.post("/transactions")
async def create_transaction(data: TransactionCreate, user: UserContext):
    logger.info(
        "transaction_create_start",
        user_id=user.uid,
        amount=data.amount,
        type=data.type
    )
```

### 8.2 Metricas de negocio
- Usuarios activos por dia/mes
- Transacciones creadas/importadas
- Sincronizaciones Asana exitosas/fallidas
- Exportaciones LLM generadas
- Uso de cuotas Firestore

### 8.3 Health checks
```python
@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "firestore": await check_firestore_connection(),
        "timestamp": datetime.utcnow().isoformat()
    }
```

---

## 9. Manejo de errores y resilencia

### 9.1 Estrategia de errores
```python
class AppException(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "request_id": request.headers.get("x-request-id")}
    )
```

### 9.2 Reintentos y circuit breakers
- **Asana API**: exponential backoff con jitter
- **Firestore**: reintentos automaticos del SDK
- **Drive API**: timeouts y reintentos limitados

### 9.3 Validacion de entrada
```python
class TransactionCreate(BaseModel):
    amount: PositiveInt  # En centimos
    type: Literal["income", "expense"]
    category_id: str
    account_id: str
    description: str = Field(max_length=200)
    date: date
    
    @validator('date')
    def validate_date_not_future(cls, v):
        if v > date.today():
            raise ValueError('Date cannot be in the future')
        return v
```

---

## 10. Optimizacion y performance

### 10.1 Estrategias de caching
- **Application-level**: cache en memoria para categorias/cuentas de usuario
- **Database-level**: indices apropiados, consultas eficientes
- **HTTP-level**: ETags para recursos que cambian poco

### 10.2 Paginacion
```python
class PaginatedResponse(BaseModel):
    items: List[Any]
    page: int
    page_size: int
    total_count: int
    has_next: bool

@router.get("/transactions")
async def get_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: UserContext = Depends(get_current_user)
):
    # Implementar paginacion eficiente con Firestore
    pass
```

### 10.3 Batch operations
- Importacion YAML: procesar en lotes para evitar timeouts
- Sincronizacion Asana: agrupar operaciones de escritura
- Exportaciones: streaming para datasets grandes

---

## 11. Testing y calidad

### 11.1 Estrategia de testing
```
tests/
├── unit/                    # Tests unitarios por capa
│   ├── models/
│   ├── services/
│   └── routers/
├── integration/             # Tests con Firestore emulator
│   ├── test_auth_flow.py
│   ├── test_asana_sync.py
│   └── test_export_flow.py
└── e2e/                    # Tests end-to-end
    └── test_user_journey.py
```

### 11.2 Mocking de dependencias
```python
@pytest.fixture
def mock_firestore():
    with patch('infrastructure.firestore_client.FirestoreClient') as mock:
        yield mock

@pytest.fixture
def mock_asana_client():
    with patch('infrastructure.asana_client.AsanaClient') as mock:
        yield mock
```

### 11.3 Coverage y calidad
- Coverage minimo: 85%
- Type checking: mypy strict mode
- Linting: ruff con configuracion estricta
- Security: bandit para analisis de vulnerabilidades

---

## 12. Despliegue y DevOps

### 12.1 Containerizacion
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### 12.2 Cloud Run deployment
```yaml
# cloudbuild.yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/financial-nomad-api', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/financial-nomad-api']
  - name: 'gcr.io/cloud-builders/gcloud'
    args: ['run', 'deploy', 'financial-nomad-api',
           '--image', 'gcr.io/$PROJECT_ID/financial-nomad-api',
           '--platform', 'managed',
           '--region', 'us-central1',
           '--min-instances', '0',
           '--max-instances', '10']
```

### 12.3 Configuracion Cloud Run
- **CPU**: 1 vCPU (dentro del free tier)
- **Memory**: 512 MiB
- **Min instances**: 0 (cold start acceptable)
- **Max instances**: 10
- **Timeout**: 300s para exports/sync largos
- **Concurrency**: 80 requests/instance

---

## 13. Seguridad

### 13.1 Configuracion de seguridad
```python
# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

# Security headers
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response
```

### 13.2 Rate limiting
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.route("/auth/login")
@limiter.limit("5/minute")
async def login_endpoint(request: Request):
    pass
```

### 13.3 Input validation y sanitizacion
- Validacion estricta con Pydantic
- Sanitizacion de strings para prevenir injection
- Validacion de rangos de fechas y montos
- Escape de contenido en exportaciones

---

## 14. Migracion y evolucion

### 14.1 Versionado de API
```python
@app.include_router(
    auth_router,
    prefix="/api/v1/auth",
    tags=["authentication"]
)
```

### 14.2 Schema evolution
```python
# Migracion de datos con retrocompatibilidad
class TransactionV1(BaseModel):
    amount: int
    description: str

class TransactionV2(BaseModel):
    amount: int
    description: str
    tags: List[str] = []  # Campo nuevo opcional
    
    @validator('tags', pre=True)
    def handle_legacy_format(cls, v):
        # Manejar documentos legacy sin tags
        return v if v is not None else []
```

---

## 15. Consideraciones de escalabilidad

### 15.1 Limites del free tier
- **Cloud Run**: 2M requests/mes
- **Firestore**: 50k reads, 20k writes/dia
- **Monitoring**: logs basicos incluidos

### 15.2 Optimizaciones para free tier
- Minimizar lecturas Firestore con caching
- Batch operations para reducir writes
- Compresion de respuestas grandes
- Lazy loading de datos relacionados

### 15.3 Puntos de escalabilidad futura
- Separacion de servicios por dominio
- Cache distribuido (Redis/Memorystore)
- Queue system para tareas async (Cloud Tasks)
- CDN para assets estaticos

---

Esta arquitectura proporciona una base solida para el desarrollo del backend, manteniendo los principios de seguridad, escalabilidad dentro del free tier y claridad en la separacion de responsabilidades.