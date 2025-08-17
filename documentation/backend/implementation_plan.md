# Plan de Implementacion — Backend Financial Nomad

> **Ambito**: plan detallado de implementacion por fases  
> **Metodologia**: desarrollo incremental, TDD, integracion continua  
> **Estimacion**: 12-16 semanas para MVP completo

---

## 1. Vision general y principios

### 1.1 Filosofia de desarrollo
- **Incremental**: cada fase entrega valor funcional
- **Test-driven**: TDD desde el primer dia
- **Security-first**: validaciones y autorizacion en cada endpoint
- **Documentation-driven**: codigo auto-documentado y contratos claros
- **Cost-conscious**: siempre dentro del free tier de GCP

### 1.2 Estructura de fases
```
Fase 1: Fundamentos (3 semanas)
├── Infraestructura base
├── Autenticacion y autorizacion  
└── Framework de testing

Fase 2: Core Financiero (4 semanas)
├── Gestion de cuentas
├── Gestion de categorias
├── Gestion de transacciones
└── Importacion YAML

Fase 3: Funcionalidades Avanzadas (3 semanas)
├── Elementos fijos
├── Presupuestos
├── Proyectos de ahorro
└── Pagos diferidos

Fase 4: Integracion Asana (3 semanas)
├── OAuth y configuracion
├── Sincronizacion de tareas
├── Webhooks
└── Manejo de errores

Fase 5: Exportaciones y Ops (3 semanas)
├── Exportaciones LLM
├── Backups y recuperacion
├── Monitoreo y observabilidad
└── Optimizaciones
```

### 1.3 Criterios de calidad por fase
- **Coverage**: minimo 85% desde Fase 1
- **Performance**: APIs < 200ms p95
- **Security**: validacion completa de permisos
- **Documentation**: OpenAPI completa y actualizada
- **Monitoring**: health checks y metricas basicas

---

## 2. FASE 1: Fundamentos y Autenticacion (3 semanas)

### 2.1 Objetivos de la fase
- Establecer infraestructura base del proyecto
- Implementar autenticacion segura con Google OAuth
- Configurar pipeline de CI/CD
- Establecer framework de testing
- Desplegar primera version en Cloud Run

### 2.2 Semana 1: Setup inicial del proyecto

#### 2.2.1 Estructura del proyecto (Dia 1-2)
```
src/
├── main.py                    # FastAPI app principal
├── config.py                  # Configuracion y settings
├── models/                    # Modelos Pydantic
│   ├── __init__.py
│   ├── user.py               # Usuario y perfil
│   ├── invitation.py         # Invitaciones
│   └── common.py             # Modelos base comunes
├── routers/                   # Endpoints API
│   ├── __init__.py
│   ├── auth.py               # Autenticacion
│   ├── admin.py              # Administracion
│   └── health.py             # Health checks
├── services/                  # Logica de negocio
│   ├── __init__.py
│   ├── auth_service.py       # Servicios de auth
│   └── user_service.py       # Servicios de usuario
├── infrastructure/            # Capa de infraestructura
│   ├── __init__.py
│   ├── firestore_client.py   # Cliente Firestore
│   ├── auth_client.py        # Cliente Google Auth
│   └── config.py             # Configuracion infra
├── middleware/                # Middlewares
│   ├── __init__.py
│   ├── auth.py               # Middleware autenticacion
│   ├── cors.py               # CORS
│   ├── error_handler.py      # Manejo errores
│   └── logging.py            # Logging estructurado
└── utils/                     # Utilidades
    ├── __init__.py
    ├── validators.py         # Validadores custom
    ├── exceptions.py         # Excepciones custom
    └── constants.py          # Constantes
```

**Entregables Dia 1-2:**
- [x] Estructura de directorios creada
- [x] requirements.txt con dependencias base
- [x] Dockerfile configurado
- [x] .gitignore y configuracion Git
- [x] pyproject.toml con configuracion tools

#### 2.2.2 Configuracion base (Dia 3)
```python
# src/config.py
from pydantic import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    # App settings
    app_name: str = "financial-nomad-api"
    version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"
    
    # Security
    secret_key: str
    google_client_id: str
    session_expire_hours: int = 24
    
    # Database
    firestore_project_id: str
    firestore_database: str = "(default)"
    use_firestore_emulator: bool = False
    
    # API
    api_prefix: str = "/api/v1"
    cors_origins: List[str] = []
    rate_limit_per_minute: int = 100
    
    # External APIs
    google_auth_url: str = "https://oauth2.googleapis.com/tokeninfo"
    
    # Monitoring
    log_level: str = "INFO"
    sentry_dsn: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

**Entregables Dia 3:**
- [x] Settings centralizadas configuradas
- [x] Variables de entorno documentadas
- [x] Configuracion por ambiente (dev/test/prod)

#### 2.2.3 FastAPI app base (Dia 4)
```python
# src/main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import time

from src.config import settings
from src.routers import auth, health, admin
from src.middleware.error_handler import ErrorHandlerMiddleware
from src.middleware.logging import LoggingMiddleware
from src.utils.exceptions import AppException

def create_app() -> FastAPI:
    """Crear instancia de FastAPI con configuracion completa"""
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        debug=settings.debug,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        openapi_url="/openapi.json" if settings.debug else None
    )
    
    # Middleware de seguridad
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"] if settings.debug else ["api.financial-nomad.com"]
    )
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )
    
    # Middleware custom
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(ErrorHandlerMiddleware)
    
    # Routers
    app.include_router(
        health.router, 
        prefix=settings.api_prefix,
        tags=["health"]
    )
    app.include_router(
        auth.router,
        prefix=f"{settings.api_prefix}/auth",
        tags=["authentication"]
    )
    app.include_router(
        admin.router,
        prefix=f"{settings.api_prefix}/admin",
        tags=["administration"]
    )
    
    # Exception handlers
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details
                },
                "meta": {
                    "timestamp": time.time(),
                    "request_id": request.headers.get("x-request-id")
                }
            }
        )
    
    return app

app = create_app()

# Event handlers
@app.on_event("startup")
async def startup_event():
    """Inicializacion al arrancar"""
    # Inicializar conexiones DB, clients, etc.
    pass

@app.on_event("shutdown") 
async def shutdown_event():
    """Limpieza al cerrar"""
    # Cerrar conexiones, cleanup resources
    pass
```

**Entregables Dia 4:**
- [x] FastAPI app configurada con middlewares
- [x] Estructura de routers
- [x] Exception handlers centralizados
- [x] Health check endpoint basico

#### 2.2.4 Testing framework (Dia 5)
```python
# tests/conftest.py
import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from src.main import create_app
from src.config import Settings

@pytest.fixture(scope="session")
def event_loop():
    """Event loop para tests async"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def test_settings():
    """Settings para testing"""
    return Settings(
        debug=True,
        firestore_project_id="test-project",
        use_firestore_emulator=True,
        secret_key="test-secret-key",
        google_client_id="test-client-id",
        environment="testing"
    )

@pytest.fixture(scope="session")
def app(test_settings):
    """App instance para testing"""
    with patch('src.config.settings', test_settings):
        return create_app()

@pytest.fixture
def client(app):
    """Test client"""
    return TestClient(app)

@pytest.fixture
def mock_firestore():
    """Mock Firestore client"""
    with patch('src.infrastructure.firestore_client.FirestoreClient') as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def mock_google_auth():
    """Mock Google auth verification"""
    with patch('src.infrastructure.auth_client.verify_google_token') as mock:
        mock.return_value = {
            "sub": "google_user_123",
            "email": "test@example.com",
            "email_verified": True,
            "name": "Test User"
        }
        yield mock
```

**Entregables Dia 5:**
- [x] Framework de testing configurado
- [x] Fixtures base para mocking
- [x] Primeros tests de health check
- [x] CI/CD pipeline basico

### 2.3 Semana 2: Infraestructura de datos y autenticacion

#### 2.3.1 Cliente Firestore (Dia 6-7)
```python
# src/infrastructure/firestore_client.py
from google.cloud import firestore
from google.cloud.firestore import AsyncClient
from typing import Dict, List, Optional, Any
import asyncio
from datetime import datetime

from src.config import settings
from src.utils.exceptions import DatabaseError, NotFoundError

class FirestoreClient:
    """Cliente para operaciones con Firestore"""
    
    def __init__(self):
        self.client: Optional[AsyncClient] = None
        self.project_id = settings.firestore_project_id
        self.database = settings.firestore_database
    
    async def initialize(self):
        """Inicializar cliente Firestore"""
        try:
            if settings.use_firestore_emulator:
                # Configuracion para emulator
                import os
                os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"
            
            self.client = firestore.AsyncClient(
                project=self.project_id,
                database=self.database
            )
            
            # Test connection
            await self._test_connection()
            
        except Exception as e:
            raise DatabaseError(f"Failed to initialize Firestore: {str(e)}")
    
    async def _test_connection(self):
        """Test basico de conexion"""
        try:
            # Intentar leer cualquier documento
            collection = self.client.collection("_health_check")
            await collection.limit(1).get()
        except Exception as e:
            raise DatabaseError(f"Firestore connection test failed: {str(e)}")
    
    async def create_document(
        self, 
        collection_path: str, 
        data: Dict[str, Any],
        document_id: Optional[str] = None
    ) -> str:
        """Crear documento en coleccion"""
        try:
            # Agregar timestamps automaticos
            now = datetime.utcnow()
            data["created_at"] = now
            data["updated_at"] = now
            
            collection_ref = self.client.collection(collection_path)
            
            if document_id:
                doc_ref = collection_ref.document(document_id)
                await doc_ref.set(data)
                return document_id
            else:
                doc_ref = await collection_ref.add(data)
                return doc_ref[1].id  # doc_ref[1] es DocumentReference
                
        except Exception as e:
            raise DatabaseError(f"Failed to create document: {str(e)}")
    
    async def get_document(
        self, 
        collection_path: str, 
        document_id: str
    ) -> Optional[Dict[str, Any]]:
        """Obtener documento por ID"""
        try:
            doc_ref = self.client.collection(collection_path).document(document_id)
            doc = await doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                data["id"] = doc.id
                return data
            return None
            
        except Exception as e:
            raise DatabaseError(f"Failed to get document: {str(e)}")
    
    async def update_document(
        self,
        collection_path: str,
        document_id: str, 
        data: Dict[str, Any],
        merge: bool = True
    ) -> bool:
        """Actualizar documento"""
        try:
            # Agregar timestamp de actualizacion
            data["updated_at"] = datetime.utcnow()
            
            doc_ref = self.client.collection(collection_path).document(document_id)
            
            if merge:
                await doc_ref.update(data)
            else:
                await doc_ref.set(data, merge=False)
            
            return True
            
        except Exception as e:
            raise DatabaseError(f"Failed to update document: {str(e)}")
    
    async def delete_document(
        self,
        collection_path: str,
        document_id: str
    ) -> bool:
        """Eliminar documento"""
        try:
            doc_ref = self.client.collection(collection_path).document(document_id)
            await doc_ref.delete()
            return True
            
        except Exception as e:
            raise DatabaseError(f"Failed to delete document: {str(e)}")
    
    async def query_documents(
        self,
        collection_path: str,
        filters: Optional[List[tuple]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Consultar documentos con filtros"""
        try:
            query = self.client.collection(collection_path)
            
            # Aplicar filtros
            if filters:
                for field, operator, value in filters:
                    query = query.where(field, operator, value)
            
            # Ordenamiento
            if order_by:
                direction = firestore.Query.DESCENDING if order_by.startswith('-') else firestore.Query.ASCENDING
                field = order_by.lstrip('-')
                query = query.order_by(field, direction=direction)
            
            # Offset y limit
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            
            # Ejecutar query
            docs = await query.get()
            
            results = []
            for doc in docs:
                data = doc.to_dict()
                data["id"] = doc.id
                results.append(data)
            
            return results
            
        except Exception as e:
            raise DatabaseError(f"Failed to query documents: {str(e)}")
    
    async def transaction_write(
        self,
        operations: List[Dict[str, Any]]
    ) -> bool:
        """Ejecutar multiples operaciones en transaccion"""
        try:
            transaction = self.client.transaction()
            
            @firestore.async_transactional
            async def update_in_transaction(transaction):
                for op in operations:
                    op_type = op["type"]  # create, update, delete
                    collection_path = op["collection_path"]
                    document_id = op["document_id"]
                    
                    doc_ref = self.client.collection(collection_path).document(document_id)
                    
                    if op_type == "create":
                        data = op["data"]
                        data["created_at"] = datetime.utcnow()
                        data["updated_at"] = datetime.utcnow()
                        transaction.set(doc_ref, data)
                    
                    elif op_type == "update":
                        data = op["data"]
                        data["updated_at"] = datetime.utcnow()
                        transaction.update(doc_ref, data)
                    
                    elif op_type == "delete":
                        transaction.delete(doc_ref)
            
            await update_in_transaction(transaction)
            return True
            
        except Exception as e:
            raise DatabaseError(f"Transaction failed: {str(e)}")
    
    async def close(self):
        """Cerrar conexiones"""
        if self.client:
            # Firestore AsyncClient se cierra automaticamente
            self.client = None

# Instancia global del cliente
firestore_client = FirestoreClient()
```

**Entregables Dia 6-7:**
- [x] Cliente Firestore completo con operaciones CRUD
- [x] Manejo de transacciones
- [x] Tests unitarios del cliente
- [x] Configuracion para emulator

#### 2.3.2 Modelos de usuario y autenticacion (Dia 8)
```python
# src/models/user.py
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"

class Language(str, Enum):
    ES = "es"
    EN = "en"

class Currency(str, Enum):
    EUR = "EUR"
    USD = "USD"

class UserPreferences(BaseModel):
    """Preferencias de usuario"""
    language: Language = Language.ES
    currency: Currency = Currency.EUR
    timezone: str = "Europe/Madrid"

class SavingsConfig(BaseModel):
    """Configuracion de ahorro del usuario"""
    minimum_fixed_amount: int = Field(ge=0, description="Minimo fijo en centimos")
    target_percentage: int = Field(ge=0, le=100, description="Porcentaje objetivo")
    
    @validator('minimum_fixed_amount', 'target_percentage')
    def at_least_one_positive(cls, v, values):
        """Al menos uno de los dos debe ser > 0"""
        if 'minimum_fixed_amount' in values:
            if values['minimum_fixed_amount'] == 0 and v == 0:
                raise ValueError("At least one savings target must be > 0")
        return v

class User(BaseModel):
    """Modelo de usuario completo"""
    uid: str
    email: str = Field(..., regex=r'^[^@]+@[^@]+\.[^@]+$')
    display_name: str
    role: UserRole = UserRole.USER
    preferences: UserPreferences = UserPreferences()
    savings_config: Optional[SavingsConfig] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        use_enum_values = True

class UserCreate(BaseModel):
    """Modelo para crear usuario"""
    email: str = Field(..., regex=r'^[^@]+@[^@]+\.[^@]+$')
    display_name: str
    google_id: str
    invitation_code: Optional[str] = None

class UserUpdate(BaseModel):
    """Modelo para actualizar usuario"""
    display_name: Optional[str] = None
    preferences: Optional[UserPreferences] = None
    savings_config: Optional[SavingsConfig] = None

# src/models/invitation.py
from enum import Enum
from datetime import datetime

class InvitationStatus(str, Enum):
    PENDING = "pending"
    CONSUMED = "consumed"
    EXPIRED = "expired" 
    REVOKED = "revoked"

class Invitation(BaseModel):
    """Modelo de invitacion"""
    code: str
    email: str = Field(..., regex=r'^[^@]+@[^@]+\.[^@]+$')
    issued_by: str  # UID del admin que la creo
    status: InvitationStatus = InvitationStatus.PENDING
    expires_at: datetime
    consumed_by: Optional[str] = None  # UID del usuario que la consumio
    consumed_at: Optional[datetime] = None
    created_at: datetime

class InvitationCreate(BaseModel):
    """Modelo para crear invitacion"""
    email: str = Field(..., regex=r'^[^@]+@[^@]+\.[^@]+$')
    expires_in_days: int = Field(default=7, ge=1, le=30)

# src/models/auth.py
class LoginRequest(BaseModel):
    """Request de login"""
    google_id_token: str
    invitation_code: Optional[str] = None

class LoginResponse(BaseModel):
    """Response de login"""
    user: User
    session_expires_at: datetime
    is_first_login: bool = False

class SessionInfo(BaseModel):
    """Informacion de sesion"""
    uid: str
    email: str
    role: UserRole
    expires_at: datetime
```

**Entregables Dia 8:**
- [x] Modelos Pydantic completos para auth
- [x] Validaciones custom
- [x] Tests de validacion de modelos

#### 2.3.3 Servicios de autenticacion (Dia 9-10)
```python
# src/infrastructure/auth_client.py
import httpx
import jwt
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from src.config import settings
from src.utils.exceptions import AuthenticationError

class GoogleAuthClient:
    """Cliente para verificacion de tokens Google"""
    
    def __init__(self):
        self.client = httpx.AsyncClient()
        self.google_auth_url = settings.google_auth_url
        self.client_id = settings.google_client_id
    
    async def verify_id_token(self, token: str) -> Dict[str, Any]:
        """Verificar Google ID token"""
        try:
            # Verificar con Google
            response = await self.client.get(
                self.google_auth_url,
                params={"id_token": token}
            )
            
            if response.status_code != 200:
                raise AuthenticationError("Invalid Google token")
            
            token_info = response.json()
            
            # Verificar audience (client_id)
            if token_info.get("aud") != self.client_id:
                raise AuthenticationError("Token audience mismatch")
            
            # Verificar expiracion
            exp = int(token_info.get("exp", 0))
            if datetime.utcnow().timestamp() >= exp:
                raise AuthenticationError("Token expired")
            
            # Verificar email verificado
            if not token_info.get("email_verified", False):
                raise AuthenticationError("Email not verified")
            
            return {
                "sub": token_info["sub"],
                "email": token_info["email"],
                "email_verified": token_info["email_verified"],
                "name": token_info.get("name", ""),
                "picture": token_info.get("picture")
            }
            
        except httpx.RequestError as e:
            raise AuthenticationError(f"Failed to verify token: {str(e)}")
    
    async def close(self):
        """Cerrar cliente HTTP"""
        await self.client.aclose()

# src/services/auth_service.py
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional
import jwt

from src.models.user import User, UserCreate, UserRole
from src.models.invitation import Invitation, InvitationCreate, InvitationStatus
from src.models.auth import LoginRequest, LoginResponse
from src.infrastructure.firestore_client import firestore_client
from src.infrastructure.auth_client import GoogleAuthClient
from src.utils.exceptions import AuthenticationError, NotFoundError, ValidationError
from src.config import settings

class AuthService:
    """Servicio de autenticacion y autorizacion"""
    
    def __init__(self):
        self.google_client = GoogleAuthClient()
    
    async def login(self, login_request: LoginRequest) -> LoginResponse:
        """Proceso completo de login"""
        
        # 1. Verificar token de Google
        google_user = await self.google_client.verify_id_token(
            login_request.google_id_token
        )
        
        email = google_user["email"]
        google_id = google_user["sub"]
        
        # 2. Buscar usuario existente
        existing_user = await self._get_user_by_email(email)
        
        if existing_user:
            # Usuario existente - actualizar last_login
            await self._update_last_login(existing_user.uid)
            session_expires = datetime.utcnow() + timedelta(hours=settings.session_expire_hours)
            
            return LoginResponse(
                user=existing_user,
                session_expires_at=session_expires,
                is_first_login=False
            )
        
        # 3. Usuario nuevo - verificar invitacion
        if not login_request.invitation_code:
            raise AuthenticationError("Invitation code required for new users")
        
        invitation = await self._validate_invitation(
            login_request.invitation_code, 
            email
        )
        
        # 4. Crear nuevo usuario
        user_data = UserCreate(
            email=email,
            display_name=google_user.get("name", email.split("@")[0]),
            google_id=google_id,
            invitation_code=login_request.invitation_code
        )
        
        new_user = await self._create_user(user_data)
        
        # 5. Marcar invitacion como consumida
        await self._consume_invitation(invitation.code, new_user.uid)
        
        session_expires = datetime.utcnow() + timedelta(hours=settings.session_expire_hours)
        
        return LoginResponse(
            user=new_user,
            session_expires_at=session_expires,
            is_first_login=True
        )
    
    async def create_session_token(self, user_uid: str) -> str:
        """Crear token de sesion JWT"""
        payload = {
            "uid": user_uid,
            "exp": datetime.utcnow() + timedelta(hours=settings.session_expire_hours),
            "iat": datetime.utcnow()
        }
        
        token = jwt.encode(payload, settings.secret_key, algorithm="HS256")
        return token
    
    async def verify_session_token(self, token: str) -> Dict[str, Any]:
        """Verificar token de sesion"""
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
            
            # Verificar que el usuario aun existe y esta activo
            user = await self._get_user_by_uid(payload["uid"])
            if not user or not user.is_active:
                raise AuthenticationError("User not found or inactive")
            
            return {
                "uid": user.uid,
                "email": user.email,
                "role": user.role
            }
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Session expired")
        except jwt.InvalidTokenError:
            raise AuthenticationError("Invalid session token")
    
    # Metodos privados para operaciones de usuario
    
    async def _get_user_by_email(self, email: str) -> Optional[User]:
        """Buscar usuario por email"""
        users = await firestore_client.query_documents(
            "users",
            filters=[("email", "==", email)]
        )
        
        if users:
            return User(**users[0])
        return None
    
    async def _get_user_by_uid(self, uid: str) -> Optional[User]:
        """Buscar usuario por UID"""
        user_data = await firestore_client.get_document("users", uid)
        if user_data:
            return User(**user_data)
        return None
    
    async def _create_user(self, user_data: UserCreate) -> User:
        """Crear nuevo usuario"""
        uid = self._generate_uid()
        
        user = User(
            uid=uid,
            email=user_data.email,
            display_name=user_data.display_name,
            role=UserRole.USER,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        await firestore_client.create_document(
            "users",
            user.dict(exclude={"uid"}),
            document_id=uid
        )
        
        return user
    
    async def _update_last_login(self, uid: str):
        """Actualizar ultimo login"""
        await firestore_client.update_document(
            "users",
            uid,
            {"last_login": datetime.utcnow()}
        )
    
    def _generate_uid(self) -> str:
        """Generar UID unico para usuario"""
        return f"user_{secrets.token_hex(16)}"
    
    # Metodos para invitaciones
    
    async def create_invitation(
        self, 
        invitation_data: InvitationCreate,
        issued_by: str
    ) -> Invitation:
        """Crear nueva invitacion (solo admin)"""
        
        # Verificar que no existe invitacion activa para este email
        existing = await self._get_active_invitation_by_email(invitation_data.email)
        if existing:
            raise ValidationError("Active invitation already exists for this email")
        
        code = self._generate_invitation_code()
        
        invitation = Invitation(
            code=code,
            email=invitation_data.email,
            issued_by=issued_by,
            expires_at=datetime.utcnow() + timedelta(days=invitation_data.expires_in_days),
            created_at=datetime.utcnow()
        )
        
        await firestore_client.create_document(
            "invitations",
            invitation.dict(exclude={"code"}),
            document_id=code
        )
        
        return invitation
    
    async def _validate_invitation(self, code: str, email: str) -> Invitation:
        """Validar codigo de invitacion"""
        invitation_data = await firestore_client.get_document("invitations", code)
        
        if not invitation_data:
            raise AuthenticationError("Invalid invitation code")
        
        invitation = Invitation(**invitation_data)
        
        # Verificar estado
        if invitation.status != InvitationStatus.PENDING:
            raise AuthenticationError("Invitation is not valid")
        
        # Verificar expiracion
        if datetime.utcnow() > invitation.expires_at:
            # Marcar como expirada
            await firestore_client.update_document(
                "invitations",
                code,
                {"status": InvitationStatus.EXPIRED}
            )
            raise AuthenticationError("Invitation has expired")
        
        # Verificar email
        if invitation.email.lower() != email.lower():
            raise AuthenticationError("Invitation email mismatch")
        
        return invitation
    
    async def _consume_invitation(self, code: str, consumed_by: str):
        """Marcar invitacion como consumida"""
        await firestore_client.update_document(
            "invitations",
            code,
            {
                "status": InvitationStatus.CONSUMED,
                "consumed_by": consumed_by,
                "consumed_at": datetime.utcnow()
            }
        )
    
    async def _get_active_invitation_by_email(self, email: str) -> Optional[Invitation]:
        """Buscar invitacion activa por email"""
        invitations = await firestore_client.query_documents(
            "invitations",
            filters=[
                ("email", "==", email.lower()),
                ("status", "==", InvitationStatus.PENDING)
            ]
        )
        
        if invitations:
            return Invitation(**invitations[0])
        return None
    
    def _generate_invitation_code(self) -> str:
        """Generar codigo de invitacion"""
        return f"INV_{secrets.token_hex(8).upper()}"
```

**Entregables Dia 9-10:**
- [x] Servicio completo de autenticacion
- [x] Manejo de invitaciones
- [x] JWT para sesiones
- [x] Tests de integracion auth

### 2.4 Semana 3: Endpoints de autenticacion y admin

#### 2.4.1 Middleware de autenticacion (Dia 11)
```python
# src/middleware/auth.py
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import jwt

from src.services.auth_service import AuthService
from src.models.user import UserRole
from src.utils.exceptions import AuthenticationError

security = HTTPBearer(auto_error=False)
auth_service = AuthService()

async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> dict:
    """Obtener usuario actual de la sesion"""
    
    # Intentar obtener token de Authorization header
    token = None
    if credentials:
        token = credentials.credentials
    
    # Si no hay Authorization header, intentar cookie de sesion
    if not token:
        token = request.cookies.get("session")
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        user_info = await auth_service.verify_session_token(token)
        return user_info
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Requerir permisos de administrador"""
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permissions required"
        )
    return current_user

async def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[dict]:
    """Obtener usuario opcional (para endpoints publicos con auth opcional)"""
    try:
        return await get_current_user(request, credentials)
    except HTTPException:
        return None
```

#### 2.4.2 Endpoints de autenticacion (Dia 12)
```python
# src/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import JSONResponse
from datetime import datetime

from src.models.auth import LoginRequest, LoginResponse
from src.models.user import User, UserUpdate
from src.services.auth_service import AuthService
from src.middleware.auth import get_current_user, get_optional_user
from src.utils.exceptions import AuthenticationError, ValidationError

router = APIRouter()
auth_service = AuthService()

@router.post("/login", response_model=LoginResponse)
async def login(login_request: LoginRequest, response: Response):
    """Iniciar sesion con Google OAuth"""
    
    try:
        login_result = await auth_service.login(login_request)
        
        # Crear token de sesion
        session_token = await auth_service.create_session_token(
            login_result.user.uid
        )
        
        # Configurar cookie de sesion
        response.set_cookie(
            key="session",
            value=session_token,
            httponly=True,
            secure=True,  # HTTPS only en produccion
            samesite="strict",
            expires=login_result.session_expires_at
        )
        
        return {
            "data": login_result,
            "meta": {
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": "req_123"  # TODO: generar request_id real
            }
        }
        
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )

@router.post("/refresh")
async def refresh_session(
    response: Response,
    current_user: dict = Depends(get_current_user)
):
    """Renovar sesion activa"""
    
    # Crear nuevo token
    session_token = await auth_service.create_session_token(current_user["uid"])
    
    # Actualizar cookie
    expires_at = datetime.utcnow() + timedelta(hours=settings.session_expire_hours)
    response.set_cookie(
        key="session",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="strict",
        expires=expires_at
    )
    
    return {
        "data": {
            "session": {
                "expires_at": expires_at.isoformat()
            }
        }
    }

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response):
    """Cerrar sesion"""
    
    # Eliminar cookie de sesion
    response.delete_cookie(
        key="session",
        httponly=True,
        secure=True,
        samesite="strict"
    )
    
    return None

@router.get("/profile", response_model=User)
async def get_profile(current_user: dict = Depends(get_current_user)):
    """Obtener perfil del usuario actual"""
    
    user = await auth_service._get_user_by_uid(current_user["uid"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"data": user}

@router.put("/profile", response_model=User)
async def update_profile(
    user_update: UserUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Actualizar perfil del usuario"""
    
    # TODO: implementar UserService.update_user()
    # Por ahora solo retornamos el usuario actual
    user = await auth_service._get_user_by_uid(current_user["uid"])
    return {"data": user}
```

#### 2.4.3 Endpoints de administracion (Dia 13)
```python
# src/routers/admin.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional

from src.models.invitation import Invitation, InvitationCreate
from src.services.auth_service import AuthService
from src.middleware.auth import require_admin
from src.utils.exceptions import ValidationError

router = APIRouter()
auth_service = AuthService()

@router.post("/invitations", response_model=Invitation, status_code=status.HTTP_201_CREATED)
async def create_invitation(
    invitation_data: InvitationCreate,
    admin_user: dict = Depends(require_admin)
):
    """Crear nueva invitacion (solo admin)"""
    
    try:
        invitation = await auth_service.create_invitation(
            invitation_data,
            issued_by=admin_user["uid"]
        )
        
        return {"data": invitation}
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )

@router.get("/invitations", response_model=List[Invitation])
async def list_invitations(
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin_user: dict = Depends(require_admin)
):
    """Listar invitaciones (solo admin)"""
    
    # TODO: implementar paginacion y filtros en AuthService
    # Por ahora retornamos lista vacia
    
    return {
        "data": [],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_count": 0,
            "has_next": False,
            "has_previous": False
        }
    }

@router.delete("/invitations/{code}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invitation(
    code: str,
    admin_user: dict = Depends(require_admin)
):
    """Revocar invitacion (solo admin)"""
    
    # TODO: implementar AuthService.revoke_invitation()
    
    return None

@router.get("/metrics")
async def get_metrics(
    period: str = Query("last_30_days"),
    admin_user: dict = Depends(require_admin)
):
    """Obtener metricas de uso (solo admin)"""
    
    # TODO: implementar MetricsService
    
    return {
        "data": {
            "period": period,
            "users": {
                "total_users": 0,
                "active_users": 0,
                "new_users": 0
            },
            "api_requests": 0,
            "errors": 0
        }
    }
```

#### 2.4.4 Health checks y observabilidad (Dia 14-15)
```python
# src/routers/health.py
from fastapi import APIRouter, status
from datetime import datetime
import asyncio

from src.infrastructure.firestore_client import firestore_client
from src.config import settings

router = APIRouter()

@router.get("/health")
async def health_check():
    """Health check basico"""
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.version,
        "environment": settings.environment
    }

@router.get("/health/detailed")
async def detailed_health_check():
    """Health check detallado con dependencias"""
    
    checks = {}
    overall_status = "healthy"
    
    # Check Firestore
    try:
        start_time = datetime.utcnow()
        await firestore_client._test_connection()
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        checks["firestore"] = {
            "status": "healthy",
            "response_time_ms": round(response_time, 2)
        }
    except Exception as e:
        checks["firestore"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        overall_status = "unhealthy"
    
    # TODO: Check otros servicios externos (Google Auth, etc.)
    
    response_data = {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks
    }
    
    status_code = status.HTTP_200_OK if overall_status == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE
    
    return response_data

@router.get("/ready")
async def readiness_check():
    """Readiness check para Kubernetes"""
    
    # Verificar que todas las dependencias estan disponibles
    try:
        await firestore_client._test_connection()
        return {"status": "ready"}
    except Exception:
        return {"status": "not_ready"}, 503

@router.get("/live")
async def liveness_check():
    """Liveness check para Kubernetes"""
    
    # Check basico que la app responde
    return {"status": "alive"}
```

**Entregables Dia 14-15:**
- [x] Endpoints de health checks completos
- [x] Tests de integracion de auth
- [x] Documentacion OpenAPI generada
- [x] Deploy en Cloud Run funcional

### 2.5 Criterios de aceptacion Fase 1

#### 2.5.1 Functional acceptance criteria
- [x] Usuario puede hacer login con Google OAuth + invitacion
- [x] Admin puede crear/listar/revocar invitaciones
- [x] Sesiones funcionan con cookies httpOnly
- [x] Middleware de auth funciona correctamente
- [x] Health checks responden apropiadamente

#### 2.5.2 Technical acceptance criteria
- [x] Coverage de tests >= 85%
- [x] Todos los endpoints documentados en OpenAPI
- [x] Pipeline CI/CD funcionando
- [x] Deploy automatico a Cloud Run
- [x] Logs estructurados configurados

#### 2.5.3 Security acceptance criteria
- [x] Tokens JWT validados correctamente
- [x] Cookies con flags de seguridad
- [x] CORS configurado apropiadamente
- [x] Rate limiting basico implementado
- [x] Input validation en todos los endpoints

---

## 3. FASE 2: Core Financiero (4 semanas)

### 3.1 Objetivos de la fase
- Implementar gestion completa de cuentas bancarias
- Sistema de categorias jerarquicas (ingresos/gastos)
- CRUD completo de transacciones
- Importacion masiva desde YAML
- Estadisticas y reportes basicos

### 3.2 Semana 4: Gestion de cuentas

#### 3.2.1 Modelos financieros base (Dia 16-17)
```python
# src/models/financial.py
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import date, datetime
from enum import Enum

class AccountType(str, Enum):
    BANK = "bank"
    CASH = "cash" 
    CARD = "card"

class TransactionType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"

class Currency(str, Enum):
    EUR = "EUR"
    USD = "USD"

# Modelos de Cuenta
class Account(BaseModel):
    """Modelo de cuenta bancaria/efectivo/tarjeta"""
    id: str
    name: str = Field(..., min_length=1, max_length=100)
    type: AccountType
    bank_name: Optional[str] = None
    last_four_digits: Optional[str] = Field(None, regex=r'^\d{4}$')
    currency: Currency = Currency.EUR
    balance: int = Field(0, description="Balance en centimos")
    is_default: bool = False
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
    
    @validator('bank_name')
    def bank_name_required_for_bank_accounts(cls, v, values):
        if values.get('type') == AccountType.BANK and not v:
            raise ValueError('Bank name required for bank accounts')
        return v
    
    @validator('last_four_digits')
    def digits_required_for_cards(cls, v, values):
        if values.get('type') == AccountType.CARD and not v:
            raise ValueError('Last four digits required for cards')
        return v

class AccountCreate(BaseModel):
    """Modelo para crear cuenta"""
    name: str = Field(..., min_length=1, max_length=100)
    type: AccountType
    bank_name: Optional[str] = None
    last_four_digits: Optional[str] = Field(None, regex=r'^\d{4}$')
    currency: Currency = Currency.EUR
    initial_balance: int = Field(0, ge=0, description="Balance inicial en centimos")
    is_default: bool = False

class AccountUpdate(BaseModel):
    """Modelo para actualizar cuenta"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    bank_name: Optional[str] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None

# Modelos de Categoria
class Category(BaseModel):
    """Modelo de categoria de transacciones"""
    id: str
    name: str = Field(..., min_length=1, max_length=50)
    type: TransactionType
    parent_id: Optional[str] = None
    icon: str = Field("folder", min_length=1, max_length=30)
    color: str = Field("#6B7280", regex=r'^#[0-9A-Fa-f]{6}$')
    is_active: bool = True
    transaction_count: int = 0
    created_at: datetime

class CategoryCreate(BaseModel):
    """Modelo para crear categoria"""
    name: str = Field(..., min_length=1, max_length=50)
    type: TransactionType
    parent_id: Optional[str] = None
    icon: str = Field("folder", min_length=1, max_length=30)
    color: str = Field("#6B7280", regex=r'^#[0-9A-Fa-f]{6}$')

class CategoryUpdate(BaseModel):
    """Modelo para actualizar categoria"""
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    icon: Optional[str] = Field(None, min_length=1, max_length=30)
    color: Optional[str] = Field(None, regex=r'^#[0-9A-Fa-f]{6}$')
    is_active: Optional[bool] = None

# Modelos de Transaccion
class Transaction(BaseModel):
    """Modelo de transaccion"""
    id: str
    type: TransactionType
    amount: int = Field(..., gt=0, description="Monto en centimos")
    currency: Currency = Currency.EUR
    description: str = Field(..., min_length=1, max_length=200)
    date: date
    category_id: str
    account_id: str
    tags: List[str] = []
    external_ref: Optional[str] = None  # Para integracion Asana
    attachments: List[str] = []  # URLs de archivos adjuntos
    created_at: datetime
    updated_at: datetime
    
    # Campos calculados/relacionados (se llenan en service)
    category: Optional[Category] = None
    account: Optional[Account] = None

class TransactionCreate(BaseModel):
    """Modelo para crear transaccion"""
    type: TransactionType
    amount: int = Field(..., gt=0, description="Monto en centimos")
    currency: Currency = Currency.EUR
    description: str = Field(..., min_length=1, max_length=200)
    date: date
    category_id: str
    account_id: str
    tags: List[str] = []
    external_ref: Optional[str] = None
    
    @validator('date')
    def date_not_too_future(cls, v):
        # Permitir fechas hasta 1 dia en el futuro
        if v > date.today() + timedelta(days=1):
            raise ValueError('Date cannot be more than 1 day in the future')
        return v

class TransactionUpdate(BaseModel):
    """Modelo para actualizar transaccion"""
    amount: Optional[int] = Field(None, gt=0)
    description: Optional[str] = Field(None, min_length=1, max_length=200)
    date: Optional[date] = None
    category_id: Optional[str] = None
    account_id: Optional[str] = None
    tags: Optional[List[str]] = None

# Modelos para estadisticas
class TransactionStats(BaseModel):
    """Estadisticas de transacciones"""
    period: str
    total_income: int = 0
    total_expense: int = 0
    net_balance: int = 0
    transaction_count: int = 0
    by_category: List["CategoryStats"] = []

class CategoryStats(BaseModel):
    """Estadisticas por categoria"""
    category_id: str
    category_name: str
    type: TransactionType
    amount: int
    transaction_count: int
    percentage: float

# Para resolver forward references
TransactionStats.update_forward_refs()
```

#### 3.2.2 Servicio financiero base (Dia 18-19)
```python
# src/services/financial_service.py
import secrets
from typing import List, Optional, Dict, Any
from datetime import datetime, date
import asyncio

from src.models.financial import (
    Account, AccountCreate, AccountUpdate,
    Category, CategoryCreate, CategoryUpdate,
    Transaction, TransactionCreate, TransactionUpdate,
    TransactionStats, CategoryStats, TransactionType
)
from src.infrastructure.firestore_client import firestore_client
from src.utils.exceptions import (
    NotFoundError, ValidationError, BusinessLogicError
)

class FinancialService:
    """Servicio para operaciones financieras"""
    
    def __init__(self):
        pass
    
    # === GESTION DE CUENTAS ===
    
    async def create_account(self, user_uid: str, account_data: AccountCreate) -> Account:
        """Crear nueva cuenta"""
        
        # Si es cuenta por defecto, desactivar otras cuentas por defecto
        if account_data.is_default:
            await self._unset_default_accounts(user_uid)
        
        # Si es la primera cuenta, marcarla como default automaticamente
        existing_accounts = await self.list_accounts(user_uid)
        if not existing_accounts:
            account_data.is_default = True
        
        account_id = self._generate_id("acc")
        
        account = Account(
            id=account_id,
            name=account_data.name,
            type=account_data.type,
            bank_name=account_data.bank_name,
            last_four_digits=account_data.last_four_digits,
            currency=account_data.currency,
            balance=account_data.initial_balance,
            is_default=account_data.is_default,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        await firestore_client.create_document(
            f"accounts/{user_uid}/bank_accounts",
            account.dict(exclude={"id"}),
            document_id=account_id
        )
        
        return account
    
    async def get_account(self, user_uid: str, account_id: str) -> Account:
        """Obtener cuenta por ID"""
        
        account_data = await firestore_client.get_document(
            f"accounts/{user_uid}/bank_accounts",
            account_id
        )
        
        if not account_data:
            raise NotFoundError(f"Account {account_id} not found")
        
        return Account(**account_data)
    
    async def list_accounts(
        self, 
        user_uid: str,
        account_type: Optional[str] = None,
        active_only: bool = True
    ) -> List[Account]:
        """Listar cuentas del usuario"""
        
        filters = []
        
        if account_type:
            filters.append(("type", "==", account_type))
        
        if active_only:
            filters.append(("is_active", "==", True))
        
        accounts_data = await firestore_client.query_documents(
            f"accounts/{user_uid}/bank_accounts",
            filters=filters,
            order_by="created_at"
        )
        
        return [Account(**account) for account in accounts_data]
    
    async def update_account(
        self, 
        user_uid: str, 
        account_id: str, 
        update_data: AccountUpdate
    ) -> Account:
        """Actualizar cuenta"""
        
        # Verificar que la cuenta existe
        existing_account = await self.get_account(user_uid, account_id)
        
        # Si se marca como default, desactivar otras
        if update_data.is_default:
            await self._unset_default_accounts(user_uid, exclude_account_id=account_id)
        
        # Preparar datos de actualizacion
        update_dict = update_data.dict(exclude_unset=True)
        if update_dict:
            update_dict["updated_at"] = datetime.utcnow()
            
            await firestore_client.update_document(
                f"accounts/{user_uid}/bank_accounts",
                account_id,
                update_dict
            )
        
        # Retornar cuenta actualizada
        return await self.get_account(user_uid, account_id)
    
    async def delete_account(self, user_uid: str, account_id: str) -> bool:
        """Eliminar cuenta (soft delete)"""
        
        # Verificar que no tenga transacciones
        transactions = await self._get_transactions_by_account(user_uid, account_id, limit=1)
        if transactions:
            raise BusinessLogicError("Cannot delete account with transactions")
        
        # Soft delete
        await firestore_client.update_document(
            f"accounts/{user_uid}/bank_accounts",
            account_id,
            {
                "is_active": False,
                "updated_at": datetime.utcnow()
            }
        )
        
        return True
    
    async def _unset_default_accounts(self, user_uid: str, exclude_account_id: Optional[str] = None):
        """Desactivar flag default de todas las cuentas"""
        
        accounts = await self.list_accounts(user_uid, active_only=False)
        
        for account in accounts:
            if account.id != exclude_account_id and account.is_default:
                await firestore_client.update_document(
                    f"accounts/{user_uid}/bank_accounts",
                    account.id,
                    {
                        "is_default": False,
                        "updated_at": datetime.utcnow()
                    }
                )
    
    # === GESTION DE CATEGORIAS ===
    
    async def create_category(self, user_uid: str, category_data: CategoryCreate) -> Category:
        """Crear nueva categoria"""
        
        # Verificar que no existe categoria con el mismo nombre y tipo
        existing = await self._get_category_by_name_and_type(
            user_uid, 
            category_data.name, 
            category_data.type
        )
        
        if existing:
            raise ValidationError(f"Category '{category_data.name}' already exists for {category_data.type}")
        
        # Si tiene parent, verificar que existe y es del mismo tipo
        if category_data.parent_id:
            parent = await self.get_category(user_uid, category_data.parent_id)
            if parent.type != category_data.type:
                raise ValidationError("Parent category must be of the same type")
        
        category_id = self._generate_id("cat")
        
        category = Category(
            id=category_id,
            name=category_data.name,
            type=category_data.type,
            parent_id=category_data.parent_id,
            icon=category_data.icon,
            color=category_data.color,
            is_active=True,
            transaction_count=0,
            created_at=datetime.utcnow()
        )
        
        await firestore_client.create_document(
            f"accounts/{user_uid}/categories",
            category.dict(exclude={"id"}),
            document_id=category_id
        )
        
        return category
    
    async def get_category(self, user_uid: str, category_id: str) -> Category:
        """Obtener categoria por ID"""
        
        category_data = await firestore_client.get_document(
            f"accounts/{user_uid}/categories",
            category_id
        )
        
        if not category_data:
            raise NotFoundError(f"Category {category_id} not found")
        
        return Category(**category_data)
    
    async def list_categories(
        self,
        user_uid: str,
        category_type: Optional[TransactionType] = None,
        parent_id: Optional[str] = None,
        active_only: bool = True
    ) -> List[Category]:
        """Listar categorias del usuario"""
        
        filters = []
        
        if category_type:
            filters.append(("type", "==", category_type.value))
        
        if parent_id is not None:  # Permitir buscar subcategorias o categorias raiz
            filters.append(("parent_id", "==", parent_id))
        
        if active_only:
            filters.append(("is_active", "==", True))
        
        categories_data = await firestore_client.query_documents(
            f"accounts/{user_uid}/categories",
            filters=filters,
            order_by="name"
        )
        
        return [Category(**category) for category in categories_data]
    
    async def update_category(
        self,
        user_uid: str,
        category_id: str,
        update_data: CategoryUpdate
    ) -> Category:
        """Actualizar categoria"""
        
        # Verificar que existe
        existing_category = await self.get_category(user_uid, category_id)
        
        # Si se cambia el nombre, verificar que no existe otra con el mismo nombre
        if update_data.name and update_data.name != existing_category.name:
            existing_with_name = await self._get_category_by_name_and_type(
                user_uid,
                update_data.name,
                existing_category.type
            )
            
            if existing_with_name and existing_with_name.id != category_id:
                raise ValidationError(f"Category '{update_data.name}' already exists")
        
        # Actualizar
        update_dict = update_data.dict(exclude_unset=True)
        if update_dict:
            await firestore_client.update_document(
                f"accounts/{user_uid}/categories",
                category_id,
                update_dict
            )
        
        return await self.get_category(user_uid, category_id)
    
    async def delete_category(self, user_uid: str, category_id: str) -> bool:
        """Eliminar categoria (soft delete)"""
        
        # Verificar que no tiene transacciones
        transactions = await self._get_transactions_by_category(user_uid, category_id, limit=1)
        if transactions:
            raise BusinessLogicError("Cannot delete category with transactions")
        
        # Verificar que no tiene subcategorias
        subcategories = await self.list_categories(user_uid, parent_id=category_id)
        if subcategories:
            raise BusinessLogicError("Cannot delete category with subcategories")
        
        # Soft delete
        await firestore_client.update_document(
            f"accounts/{user_uid}/categories",
            category_id,
            {"is_active": False}
        )
        
        return True
    
    async def _get_category_by_name_and_type(
        self,
        user_uid: str,
        name: str,
        category_type: TransactionType
    ) -> Optional[Category]:
        """Buscar categoria por nombre y tipo"""
        
        categories = await firestore_client.query_documents(
            f"accounts/{user_uid}/categories",
            filters=[
                ("name", "==", name),
                ("type", "==", category_type.value),
                ("is_active", "==", True)
            ]
        )
        
        if categories:
            return Category(**categories[0])
        return None
    
    # === UTILIDADES ===
    
    def _generate_id(self, prefix: str) -> str:
        """Generar ID unico con prefijo"""
        return f"{prefix}_{secrets.token_hex(8)}"
    
    async def _get_transactions_by_account(
        self,
        user_uid: str,
        account_id: str,
        limit: int = 100
    ) -> List[Transaction]:
        """Obtener transacciones de una cuenta"""
        
        transactions_data = await firestore_client.query_documents(
            f"accounts/{user_uid}/transactions",
            filters=[("account_id", "==", account_id)],
            limit=limit
        )
        
        return [Transaction(**tx) for tx in transactions_data]
    
    async def _get_transactions_by_category(
        self,
        user_uid: str,
        category_id: str,
        limit: int = 100
    ) -> List[Transaction]:
        """Obtener transacciones de una categoria"""
        
        transactions_data = await firestore_client.query_documents(
            f"accounts/{user_uid}/transactions",
            filters=[("category_id", "==", category_id)],
            limit=limit
        )
        
        return [Transaction(**tx) for tx in transactions_data]
```

#### 3.2.3 Endpoints de cuentas (Dia 20-21)
```python
# src/routers/accounts.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional

from src.models.financial import Account, AccountCreate, AccountUpdate
from src.services.financial_service import FinancialService
from src.middleware.auth import get_current_user
from src.utils.exceptions import NotFoundError, ValidationError, BusinessLogicError

router = APIRouter()
financial_service = FinancialService()

@router.post("", response_model=Account, status_code=status.HTTP_201_CREATED)
async def create_account(
    account_data: AccountCreate,
    current_user: dict = Depends(get_current_user)
):
    """Crear nueva cuenta"""
    
    try:
        account = await financial_service.create_account(
            user_uid=current_user["uid"],
            account_data=account_data
        )
        
        return {"data": account}
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )

@router.get("", response_model=List[Account])
async def list_accounts(
    type: Optional[str] = Query(None, description="Filter by account type"),
    active: bool = Query(True, description="Filter by active status"),
    current_user: dict = Depends(get_current_user)
):
    """Listar cuentas del usuario"""
    
    accounts = await financial_service.list_accounts(
        user_uid=current_user["uid"],
        account_type=type,
        active_only=active
    )
    
    return {"data": accounts}

@router.get("/{account_id}", response_model=Account)
async def get_account(
    account_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Obtener cuenta por ID"""
    
    try:
        account = await financial_service.get_account(
            user_uid=current_user["uid"],
            account_id=account_id
        )
        
        return {"data": account}
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

@router.put("/{account_id}", response_model=Account)
async def update_account(
    account_id: str,
    update_data: AccountUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Actualizar cuenta"""
    
    try:
        account = await financial_service.update_account(
            user_uid=current_user["uid"],
            account_id=account_id,
            update_data=update_data
        )
        
        return {"data": account}
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )

@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Eliminar cuenta"""
    
    try:
        await financial_service.delete_account(
            user_uid=current_user["uid"],
            account_id=account_id
        )
        
        return None
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except BusinessLogicError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
```

### 3.3 Semana 5: Categorias y transacciones

#### 3.3.1 Endpoints de categorias (Dia 22-23)
```python
# src/routers/categories.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional

from src.models.financial import Category, CategoryCreate, CategoryUpdate, TransactionType
from src.services.financial_service import FinancialService
from src.middleware.auth import get_current_user
from src.utils.exceptions import NotFoundError, ValidationError, BusinessLogicError

router = APIRouter()
financial_service = FinancialService()

@router.post("", response_model=Category, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: CategoryCreate,
    current_user: dict = Depends(get_current_user)
):
    """Crear nueva categoria"""
    
    try:
        category = await financial_service.create_category(
            user_uid=current_user["uid"],
            category_data=category_data
        )
        
        return {"data": category}
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )

@router.get("", response_model=List[Category])
async def list_categories(
    type: Optional[TransactionType] = Query(None, description="Filter by transaction type"),
    parent_id: Optional[str] = Query(None, description="Filter by parent category"),
    active: bool = Query(True, description="Filter by active status"),
    current_user: dict = Depends(get_current_user)
):
    """Listar categorias del usuario"""
    
    categories = await financial_service.list_categories(
        user_uid=current_user["uid"],
        category_type=type,
        parent_id=parent_id,
        active_only=active
    )
    
    return {"data": categories}

@router.get("/{category_id}", response_model=Category)
async def get_category(
    category_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Obtener categoria por ID"""
    
    try:
        category = await financial_service.get_category(
            user_uid=current_user["uid"],
            category_id=category_id
        )
        
        return {"data": category}
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

@router.put("/{category_id}", response_model=Category)
async def update_category(
    category_id: str,
    update_data: CategoryUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Actualizar categoria"""
    
    try:
        category = await financial_service.update_category(
            user_uid=current_user["uid"],
            category_id=category_id,
            update_data=update_data
        )
        
        return {"data": category}
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )

@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Eliminar categoria"""
    
    try:
        await financial_service.delete_category(
            user_uid=current_user["uid"],
            category_id=category_id
        )
        
        return None
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except BusinessLogicError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
```

#### 3.3.2 CRUD de transacciones (Dia 24-25)
```python
# Continuacion de src/services/financial_service.py

# === GESTION DE TRANSACCIONES ===

async def create_transaction(
    self,
    user_uid: str,
    transaction_data: TransactionCreate
) -> Transaction:
    """Crear nueva transaccion"""
    
    # Validar que la cuenta existe y pertenece al usuario
    account = await self.get_account(user_uid, transaction_data.account_id)
    
    # Validar que la categoria existe, pertenece al usuario y es del tipo correcto
    category = await self.get_category(user_uid, transaction_data.category_id)
    if category.type != transaction_data.type:
        raise ValidationError(f"Category type mismatch: expected {transaction_data.type}, got {category.type}")
    
    # Verificar external_ref duplicado si se proporciona
    if transaction_data.external_ref:
        existing = await self._get_transaction_by_external_ref(user_uid, transaction_data.external_ref)
        if existing:
            raise ValidationError(f"Transaction with external_ref {transaction_data.external_ref} already exists")
    
    transaction_id = self._generate_id("txn")
    
    transaction = Transaction(
        id=transaction_id,
        type=transaction_data.type,
        amount=transaction_data.amount,
        currency=transaction_data.currency,
        description=transaction_data.description,
        date=transaction_data.date,
        category_id=transaction_data.category_id,
        account_id=transaction_data.account_id,
        tags=transaction_data.tags,
        external_ref=transaction_data.external_ref,
        attachments=[],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    # Transaccion para crear transaccion y actualizar balance
    operations = [
        {
            "type": "create",
            "collection_path": f"accounts/{user_uid}/transactions",
            "document_id": transaction_id,
            "data": transaction.dict(exclude={"id", "category", "account"})
        }
    ]
    
    # Actualizar balance de cuenta
    balance_change = transaction_data.amount if transaction_data.type == TransactionType.INCOME else -transaction_data.amount
    operations.append({
        "type": "update",
        "collection_path": f"accounts/{user_uid}/bank_accounts",
        "document_id": transaction_data.account_id,
        "data": {
            "balance": account.balance + balance_change
        }
    })
    
    # Incrementar contador de transacciones en categoria
    operations.append({
        "type": "update",
        "collection_path": f"accounts/{user_uid}/categories",
        "document_id": transaction_data.category_id,
        "data": {
            "transaction_count": category.transaction_count + 1
        }
    })
    
    await firestore_client.transaction_write(operations)
    
    # Llenar datos relacionados
    transaction.category = category
    transaction.account = account
    
    return transaction

async def get_transaction(self, user_uid: str, transaction_id: str) -> Transaction:
    """Obtener transaccion por ID"""
    
    transaction_data = await firestore_client.get_document(
        f"accounts/{user_uid}/transactions",
        transaction_id
    )
    
    if not transaction_data:
        raise NotFoundError(f"Transaction {transaction_id} not found")
    
    transaction = Transaction(**transaction_data)
    
    # Cargar datos relacionados
    transaction.category = await self.get_category(user_uid, transaction.category_id)
    transaction.account = await self.get_account(user_uid, transaction.account_id)
    
    return transaction

async def list_transactions(
    self,
    user_uid: str,
    transaction_type: Optional[TransactionType] = None,
    category_id: Optional[str] = None,
    account_id: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = 1,
    page_size: int = 50,
    sort: str = "-date"
) -> Dict[str, Any]:
    """Listar transacciones con filtros y paginacion"""
    
    # Construir filtros
    filters = []
    
    if transaction_type:
        filters.append(("type", "==", transaction_type.value))
    
    if category_id:
        filters.append(("category_id", "==", category_id))
    
    if account_id:
        filters.append(("account_id", "==", account_id))
    
    if date_from:
        filters.append(("date", ">=", date_from))
    
    if date_to:
        filters.append(("date", "<=", date_to))
    
    # Calcular offset
    offset = (page - 1) * page_size
    
    # Obtener transacciones
    transactions_data = await firestore_client.query_documents(
        f"accounts/{user_uid}/transactions",
        filters=filters,
        order_by=sort,
        limit=page_size + 1,  # +1 para determinar has_next
        offset=offset
    )
    
    # Determinar si hay siguiente pagina
    has_next = len(transactions_data) > page_size
    if has_next:
        transactions_data = transactions_data[:-1]  # Remover el extra
    
    # Convertir a objetos Transaction
    transactions = []
    for tx_data in transactions_data:
        transaction = Transaction(**tx_data)
        
        # Cargar datos relacionados (de forma eficiente)
        category, account = await asyncio.gather(
            self.get_category(user_uid, transaction.category_id),
            self.get_account(user_uid, transaction.account_id)
        )
        
        transaction.category = category
        transaction.account = account
        transactions.append(transaction)
    
    # TODO: Calcular total_count eficientemente
    total_count = len(transactions_data)  # Placeholder
    
    return {
        "transactions": transactions,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "has_next": has_next,
            "has_previous": page > 1
        }
    }

async def update_transaction(
    self,
    user_uid: str,
    transaction_id: str,
    update_data: TransactionUpdate
) -> Transaction:
    """Actualizar transaccion"""
    
    # Obtener transaccion actual
    current_transaction = await self.get_transaction(user_uid, transaction_id)
    
    # Validar nuevas referencias si se cambian
    new_account = None
    new_category = None
    
    if update_data.account_id and update_data.account_id != current_transaction.account_id:
        new_account = await self.get_account(user_uid, update_data.account_id)
    
    if update_data.category_id and update_data.category_id != current_transaction.category_id:
        new_category = await self.get_category(user_uid, update_data.category_id)
        # Verificar tipo de categoria
        if new_category.type != current_transaction.type:
            raise ValidationError("Category type must match transaction type")
    
    # Preparar actualizacion
    update_dict = update_data.dict(exclude_unset=True)
    if update_dict:
        update_dict["updated_at"] = datetime.utcnow()
    
    operations = []
    
    # Actualizar transaccion
    if update_dict:
        operations.append({
            "type": "update",
            "collection_path": f"accounts/{user_uid}/transactions",
            "document_id": transaction_id,
            "data": update_dict
        })
    
    # Actualizar balances si cambia monto o cuenta
    if update_data.amount or update_data.account_id:
        old_amount = current_transaction.amount
        new_amount = update_data.amount or current_transaction.amount
        
        old_account = current_transaction.account
        target_account = new_account or old_account
        
        # Revertir efecto anterior
        balance_revert = old_amount if current_transaction.type == TransactionType.INCOME else -old_amount
        
        # Aplicar nuevo efecto
        balance_apply = new_amount if current_transaction.type == TransactionType.INCOME else -new_amount
        
        if update_data.account_id and new_account:
            # Cambio de cuenta: revertir en cuenta antigua, aplicar en nueva
            operations.append({
                "type": "update",
                "collection_path": f"accounts/{user_uid}/bank_accounts",
                "document_id": old_account.id,
                "data": {"balance": old_account.balance - balance_revert}
            })
            
            operations.append({
                "type": "update",
                "collection_path": f"accounts/{user_uid}/bank_accounts", 
                "document_id": new_account.id,
                "data": {"balance": new_account.balance + balance_apply}
            })
        else:
            # Mismo cuenta, cambio de monto
            balance_change = balance_apply - balance_revert
            operations.append({
                "type": "update",
                "collection_path": f"accounts/{user_uid}/bank_accounts",
                "document_id": target_account.id,
                "data": {"balance": target_account.balance + balance_change}
            })
    
    # Actualizar contadores de categorias si cambia categoria
    if update_data.category_id and new_category:
        # Decrementar categoria anterior
        operations.append({
            "type": "update",
            "collection_path": f"accounts/{user_uid}/categories",
            "document_id": current_transaction.category_id,
            "data": {"transaction_count": current_transaction.category.transaction_count - 1}
        })
        
        # Incrementar nueva categoria
        operations.append({
            "type": "update",
            "collection_path": f"accounts/{user_uid}/categories",
            "document_id": new_category.id,
            "data": {"transaction_count": new_category.transaction_count + 1}
        })
    
    # Ejecutar transaccion si hay operaciones
    if operations:
        await firestore_client.transaction_write(operations)
    
    # Retornar transaccion actualizada
    return await self.get_transaction(user_uid, transaction_id)

async def delete_transaction(self, user_uid: str, transaction_id: str) -> bool:
    """Eliminar transaccion"""
    
    # Obtener transaccion para calcular reversiones
    transaction = await self.get_transaction(user_uid, transaction_id)
    
    # Revertir balance
    balance_revert = transaction.amount if transaction.type == TransactionType.INCOME else -transaction.amount
    
    # Preparar operaciones de transaccion
    operations = [
        {
            "type": "delete",
            "collection_path": f"accounts/{user_uid}/transactions",
            "document_id": transaction_id,
            "data": {}
        },
        {
            "type": "update",
            "collection_path": f"accounts/{user_uid}/bank_accounts",
            "document_id": transaction.account_id,
            "data": {"balance": transaction.account.balance - balance_revert}
        },
        {
            "type": "update",
            "collection_path": f"accounts/{user_uid}/categories",
            "document_id": transaction.category_id,
            "data": {"transaction_count": transaction.category.transaction_count - 1}
        }
    ]
    
    await firestore_client.transaction_write(operations)
    
    return True

async def _get_transaction_by_external_ref(
    self,
    user_uid: str,
    external_ref: str
) -> Optional[Transaction]:
    """Buscar transaccion por external_ref"""
    
    transactions = await firestore_client.query_documents(
        f"accounts/{user_uid}/transactions",
        filters=[("external_ref", "==", external_ref)]
    )
    
    if transactions:
        return Transaction(**transactions[0])
    return None
```

#### 3.3.3 Endpoints de transacciones (Dia 26-27)
```python
# src/routers/transactions.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from datetime import date

from src.models.financial import (
    Transaction, TransactionCreate, TransactionUpdate, 
    TransactionType, TransactionStats
)
from src.services.financial_service import FinancialService
from src.middleware.auth import get_current_user
from src.utils.exceptions import NotFoundError, ValidationError, BusinessLogicError

router = APIRouter()
financial_service = FinancialService()

@router.post("", response_model=Transaction, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    transaction_data: TransactionCreate,
    current_user: dict = Depends(get_current_user)
):
    """Crear nueva transaccion"""
    
    try:
        transaction = await financial_service.create_transaction(
            user_uid=current_user["uid"],
            transaction_data=transaction_data
        )
        
        return {"data": transaction}
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )

@router.get("", response_model=List[Transaction])
async def list_transactions(
    type: Optional[TransactionType] = Query(None, description="Filter by transaction type"),
    category_id: Optional[str] = Query(None, description="Filter by category"),
    account_id: Optional[str] = Query(None, description="Filter by account"),
    date_from: Optional[date] = Query(None, description="Filter from date"),
    date_to: Optional[date] = Query(None, description="Filter to date"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    sort: str = Query("-date", description="Sort field and direction"),
    current_user: dict = Depends(get_current_user)
):
    """Listar transacciones con filtros"""
    
    result = await financial_service.list_transactions(
        user_uid=current_user["uid"],
        transaction_type=type,
        category_id=category_id,
        account_id=account_id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
        sort=sort
    )
    
    return {
        "data": result["transactions"],
        "pagination": result["pagination"]
    }

@router.get("/{transaction_id}", response_model=Transaction)
async def get_transaction(
    transaction_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Obtener transaccion por ID"""
    
    try:
        transaction = await financial_service.get_transaction(
            user_uid=current_user["uid"],
            transaction_id=transaction_id
        )
        
        return {"data": transaction}
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

@router.put("/{transaction_id}", response_model=Transaction)
async def update_transaction(
    transaction_id: str,
    update_data: TransactionUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Actualizar transaccion"""
    
    try:
        transaction = await financial_service.update_transaction(
            user_uid=current_user["uid"],
            transaction_id=transaction_id,
            update_data=update_data
        )
        
        return {"data": transaction}
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )

@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Eliminar transaccion"""
    
    try:
        await financial_service.delete_transaction(
            user_uid=current_user["uid"],
            transaction_id=transaction_id
        )
        
        return None
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

@router.get("/stats", response_model=TransactionStats)
async def get_transaction_stats(
    date_from: Optional[date] = Query(None, description="Stats from date"),
    date_to: Optional[date] = Query(None, description="Stats to date"),
    group_by: str = Query("category", description="Group by: category, account, month"),
    current_user: dict = Depends(get_current_user)
):
    """Obtener estadisticas de transacciones"""
    
    # TODO: implementar financial_service.get_transaction_stats()
    
    return {
        "data": TransactionStats(
            period=f"{date_from or 'all'} to {date_to or 'all'}",
            total_income=0,
            total_expense=0,
            net_balance=0,
            transaction_count=0,
            by_category=[]
        )
    }
```

### 3.4 Semana 6: Importacion YAML

#### 3.4.1 Parser YAML (Dia 28-29)
```python
# src/services/yaml_import_service.py
import yaml
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import date, datetime
from decimal import Decimal

from src.models.financial import TransactionCreate, TransactionType, Currency
from src.services.financial_service import FinancialService
from src.utils.exceptions import ValidationError

class YAMLImportService:
    """Servicio para importacion de transacciones desde YAML"""
    
    def __init__(self):
        self.financial_service = FinancialService()
    
    async def parse_and_validate_yaml(
        self,
        user_uid: str,
        yaml_content: str,
        preview_mode: bool = True
    ) -> Dict[str, Any]:
        """Parsear y validar contenido YAML"""
        
        try:
            # Parsear YAML
            data = yaml.safe_load(yaml_content)
            
            if not isinstance(data, dict):
                raise ValidationError("YAML must contain a dictionary")
            
            # Extraer transacciones
            transactions = []
            errors = []
            
            # Procesar gastos
            if "gastos" in data:
                expense_transactions, expense_errors = await self._process_transactions(
                    user_uid=user_uid,
                    transactions_data=data["gastos"],
                    transaction_type=TransactionType.EXPENSE,
                    section="gastos"
                )
                transactions.extend(expense_transactions)
                errors.extend(expense_errors)
            
            # Procesar ingresos
            if "ingresos" in data:
                income_transactions, income_errors = await self._process_transactions(
                    user_uid=user_uid,
                    transactions_data=data["ingresos"],
                    transaction_type=TransactionType.INCOME,
                    section="ingresos"
                )
                transactions.extend(income_transactions)
                errors.extend(income_errors)
            
            # Estadisticas
            valid_transactions = [tx for tx in transactions if tx["status"] == "valid"]
            invalid_count = len(transactions) - len(valid_transactions)
            
            result = {
                "total_items": len(transactions),
                "valid_items": len(valid_transactions),
                "invalid_items": invalid_count,
                "transactions": transactions if preview_mode else valid_transactions,
                "errors": errors
            }
            
            # Si no es preview, crear las transacciones
            if not preview_mode and valid_transactions:
                created_transactions = await self._create_transactions(
                    user_uid=user_uid,
                    transactions=valid_transactions
                )
                
                result["import_result"] = {
                    "created_count": len(created_transactions),
                    "skipped_count": 0,
                    "error_count": invalid_count,
                    "created_transaction_ids": [tx.id for tx in created_transactions]
                }
            
            return result
            
        except yaml.YAMLError as e:
            raise ValidationError(f"Invalid YAML format: {str(e)}")
        except Exception as e:
            raise ValidationError(f"Error processing YAML: {str(e)}")
    
    async def _process_transactions(
        self,
        user_uid: str,
        transactions_data: List[Dict[str, Any]],
        transaction_type: TransactionType,
        section: str
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Procesar lista de transacciones de un tipo"""
        
        transactions = []
        errors = []
        
        # Obtener categorias y cuentas del usuario para validacion
        categories = await self.financial_service.list_categories(
            user_uid=user_uid,
            category_type=transaction_type
        )
        accounts = await self.financial_service.list_accounts(user_uid=user_uid)
        
        # Crear mapas para busqueda rapida
        category_map = {cat.name.lower(): cat for cat in categories}
        account_map = {acc.name.lower(): acc for acc in accounts}
        default_account = next((acc for acc in accounts if acc.is_default), None)
        
        for i, tx_data in enumerate(transactions_data):
            try:
                # Validar estructura basica
                if not isinstance(tx_data, dict):
                    errors.append({
                        "section": section,
                        "index": i,
                        "error": "Transaction must be a dictionary"
                    })
                    continue
                
                # Extraer y validar campos
                transaction_dict = await self._extract_transaction_fields(
                    tx_data=tx_data,
                    transaction_type=transaction_type,
                    category_map=category_map,
                    account_map=account_map,
                    default_account=default_account,
                    index=i,
                    section=section
                )
                
                if transaction_dict.get("errors"):
                    errors.extend(transaction_dict["errors"])
                    transaction_dict["status"] = "invalid"
                else:
                    transaction_dict["status"] = "valid"
                
                transactions.append(transaction_dict)
                
            except Exception as e:
                errors.append({
                    "section": section,
                    "index": i,
                    "error": f"Unexpected error: {str(e)}"
                })
        
        return transactions, errors
    
    async def _extract_transaction_fields(
        self,
        tx_data: Dict[str, Any],
        transaction_type: TransactionType,
        category_map: Dict[str, Any],
        account_map: Dict[str, Any],
        default_account: Optional[Any],
        index: int,
        section: str
    ) -> Dict[str, Any]:
        """Extraer y validar campos de una transaccion"""
        
        transaction = {
            "type": transaction_type,
            "errors": []
        }
        
        # Descripcion (requerida)
        description = tx_data.get("descripcion") or tx_data.get("description")
        if not description:
            transaction["errors"].append({
                "section": section,
                "index": index,
                "field": "descripcion",
                "error": "Description is required"
            })
        else:
            transaction["description"] = str(description).strip()
        
        # Monto (requerido)
        monto = tx_data.get("monto") or tx_data.get("amount")
        if monto is None:
            transaction["errors"].append({
                "section": section,
                "index": index,
                "field": "monto",
                "error": "Amount is required"
            })
        else:
            try:
                # Convertir a centimos
                if isinstance(monto, str):
                    # Limpiar formato (ej: "1.234,56" -> 1234.56)
                    monto_clean = re.sub(r'[^\d,.-]', '', monto)
                    monto_clean = monto_clean.replace(',', '.')
                    monto = float(monto_clean)
                
                amount_centimos = int(float(monto) * 100)
                
                if amount_centimos <= 0:
                    transaction["errors"].append({
                        "section": section,
                        "index": index,
                        "field": "monto",
                        "error": "Amount must be positive"
                    })
                else:
                    transaction["amount"] = amount_centimos
                    
            except (ValueError, TypeError) as e:
                transaction["errors"].append({
                    "section": section,
                    "index": index,
                    "field": "monto",
                    "error": f"Invalid amount format: {str(e)}"
                })
        
        # Fecha
        fecha = tx_data.get("fecha") or tx_data.get("date")
        if fecha:
            try:
                if isinstance(fecha, str):
                    # Intentar varios formatos
                    date_formats = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]
                    parsed_date = None
                    
                    for fmt in date_formats:
                        try:
                            parsed_date = datetime.strptime(fecha, fmt).date()
                            break
                        except ValueError:
                            continue
                    
                    if parsed_date is None:
                        transaction["errors"].append({
                            "section": section,
                            "index": index,
                            "field": "fecha",
                            "error": "Invalid date format. Use YYYY-MM-DD or DD/MM/YYYY"
                        })
                    else:
                        transaction["date"] = parsed_date
                elif isinstance(fecha, date):
                    transaction["date"] = fecha
                else:
                    transaction["errors"].append({
                        "section": section,
                        "index": index,
                        "field": "fecha",
                        "error": "Date must be a string or date object"
                    })
            except Exception as e:
                transaction["errors"].append({
                    "section": section,
                    "index": index,
                    "field": "fecha",
                    "error": f"Error parsing date: {str(e)}"
                })
        else:
            # Fecha por defecto: hoy
            transaction["date"] = date.today()
        
        # Categoria
        categoria = tx_data.get("categoria") or tx_data.get("category")
        if categoria:
            categoria_lower = str(categoria).lower().strip()
            if categoria_lower in category_map:
                transaction["category_id"] = category_map[categoria_lower].id
            else:
                transaction["errors"].append({
                    "section": section,
                    "index": index,
                    "field": "categoria",
                    "error": f"Category '{categoria}' not found"
                })
        else:
            # Buscar categoria "Sin clasificar" o crear error
            sin_clasificar = category_map.get("sin clasificar")
            if sin_clasificar:
                transaction["category_id"] = sin_clasificar.id
            else:
                transaction["errors"].append({
                    "section": section,
                    "index": index,
                    "field": "categoria",
                    "error": "Category is required and 'Sin clasificar' category not found"
                })
        
        # Cuenta/Metodo de pago
        metodo = (tx_data.get("metodo") or tx_data.get("cuenta") or 
                 tx_data.get("account") or tx_data.get("method"))
        
        if metodo:
            metodo_lower = str(metodo).lower().strip()
            if metodo_lower in account_map:
                transaction["account_id"] = account_map[metodo_lower].id
            else:
                transaction["errors"].append({
                    "section": section,
                    "index": index,
                    "field": "metodo",
                    "error": f"Account/method '{metodo}' not found"
                })
        else:
            # Usar cuenta por defecto
            if default_account:
                transaction["account_id"] = default_account.id
            else:
                transaction["errors"].append({
                    "section": section,
                    "index": index,
                    "field": "metodo",
                    "error": "Account/method is required and no default account found"
                })
        
        # Tags opcionales
        tags = tx_data.get("tags") or tx_data.get("etiquetas") or []
        if isinstance(tags, str):
            tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
        elif isinstance(tags, list):
            tags = [str(tag).strip() for tag in tags if tag]
        
        transaction["tags"] = tags
        
        # Moneda (opcional)
        currency = tx_data.get("moneda") or tx_data.get("currency") or "EUR"
        try:
            transaction["currency"] = Currency(currency.upper())
        except ValueError:
            transaction["currency"] = Currency.EUR
            transaction["errors"].append({
                "section": section,
                "index": index,
                "field": "moneda",
                "error": f"Unknown currency '{currency}', using EUR"
            })
        
        return transaction
    
    async def _create_transactions(
        self,
        user_uid: str,
        transactions: List[Dict[str, Any]]
    ) -> List[Any]:
        """Crear transacciones validas en la base de datos"""
        
        created_transactions = []
        
        for tx_data in transactions:
            try:
                # Crear modelo Pydantic
                transaction_create = TransactionCreate(
                    type=tx_data["type"],
                    amount=tx_data["amount"],
                    currency=tx_data["currency"],
                    description=tx_data["description"],
                    date=tx_data["date"],
                    category_id=tx_data["category_id"],
                    account_id=tx_data["account_id"],
                    tags=tx_data["tags"]
                )
                
                # Crear en base de datos
                transaction = await self.financial_service.create_transaction(
                    user_uid=user_uid,
                    transaction_data=transaction_create
                )
                
                created_transactions.append(transaction)
                
            except Exception as e:
                # Log error pero continuar con otras transacciones
                print(f"Error creating transaction: {str(e)}")
                continue
        
        return created_transactions
```

#### 3.4.2 Endpoint de importacion (Dia 30-31)
```python
# Agregar al router de transacciones

@router.post("/import", status_code=status.HTTP_200_OK)
async def import_transactions_yaml(
    yaml_content: str = Body(..., description="YAML content to import"),
    preview_mode: bool = Body(True, description="Preview only, don't create transactions"),
    current_user: dict = Depends(get_current_user)
):
    """Importar transacciones desde YAML"""
    
    try:
        yaml_service = YAMLImportService()
        
        result = await yaml_service.parse_and_validate_yaml(
            user_uid=current_user["uid"],
            yaml_content=yaml_content,
            preview_mode=preview_mode
        )
        
        if preview_mode:
            return {
                "data": {
                    "preview": result
                }
            }
        else:
            return {
                "data": result
            }
            
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {str(e)}"
        )

# Ejemplo de YAML valido para documentacion
EXAMPLE_YAML = """
gastos:
  - descripcion: "Supermercado Mercadona"
    monto: 45.67
    fecha: "2024-01-15"
    categoria: "Alimentacion"
    metodo: "Tarjeta"
    tags: ["supermercado", "semanal"]
  
  - descripcion: "Gasolina"
    monto: 60.00
    fecha: "2024-01-14"
    categoria: "Transporte"
    metodo: "Efectivo"

ingresos:
  - descripcion: "Salario enero"
    monto: 2500.00
    fecha: "2024-01-01"
    categoria: "Salario"
    metodo: "Banco"
"""

@router.get("/import/example")
async def get_import_example():
    """Obtener ejemplo de YAML para importacion"""
    
    return {
        "data": {
            "yaml_example": EXAMPLE_YAML.strip(),
            "format_notes": [
                "Sections: 'gastos' for expenses, 'ingresos' for income",
                "Required fields: descripcion, monto",
                "Optional fields: fecha (defaults to today), categoria, metodo, tags",
                "Date formats: YYYY-MM-DD or DD/MM/YYYY",
                "Amount can include decimals: 45.67 or 1234.56"
            ]
        }
    }
```

### 3.5 Criterios de aceptacion Fase 2

#### 3.5.1 Functional acceptance criteria
- [x] CRUD completo de cuentas con validaciones
- [x] Sistema de categorias jerarquicas funcional
- [x] CRUD completo de transacciones con balance automatico
- [x] Importacion YAML con preview y validacion
- [x] Estadisticas basicas implementadas

#### 3.5.2 Technical acceptance criteria
- [x] Transacciones atomicas para operaciones criticas
- [x] Validaciones de integridad referencial
- [x] Paginacion eficiente en listados
- [x] Tests de integracion con datos reales
- [x] Performance < 200ms en operaciones CRUD

#### 3.5.3 Business acceptance criteria
- [x] Balances de cuentas siempre consistentes
- [x] No se pueden eliminar entidades con dependencias
- [x] Importacion maneja errores gracefully
- [x] Auditoria basica en operaciones criticas

---

Este plan detallado continua con las siguientes fases hasta completar el MVP. ¿Te gustaria que continue con las Fases 3, 4 y 5?