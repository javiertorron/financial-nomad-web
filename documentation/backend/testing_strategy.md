# Estrategia de Testing — Backend Financial Nomad

> **Ambito**: estrategia completa de testing para backend FastAPI  
> **Enfoque**: quality-first, testing pyramid, CI/CD integrado  
> **Herramientas**: pytest, Firestore emulator, testcontainers, coverage

---

## 1. Filosofia y principios de testing

### 1.1 Principios fundamentales
- **Testing Pyramid**: mayoría unit tests, menos integration, mínimos e2e
- **Shift-left**: encontrar bugs lo antes posible en el ciclo de desarrollo
- **Fast feedback**: tests rápidos que no bloqueen el desarrollo
- **Deterministic**: tests predecibles y repetibles
- **Isolated**: cada test independiente, sin efectos secundarios
- **Clear naming**: nombres descriptivos que expliquen qué se testea

### 1.2 Objetivos de calidad
- **Coverage mínimo**: 85% de líneas de código
- **Performance**: suite completa en < 5 minutos
- **Reliability**: < 1% de tests flaky
- **Security**: validación de vulnerabilidades conocidas
- **Documentation**: tests como documentación viva del comportamiento

### 1.3 Estrategia por capas
```
                 E2E Tests (5%)
               Integration Tests (20%)
              Unit Tests (75%)
```

---

## 2. Arquitectura de testing

### 2.1 Estructura de directorios
```
tests/
├── unit/                           # Tests unitarios (75%)
│   ├── models/                     # Tests de modelos Pydantic
│   │   ├── test_user.py
│   │   ├── test_financial.py
│   │   ├── test_budgets.py
│   │   └── test_asana.py
│   ├── services/                   # Tests de logica de negocio
│   │   ├── test_auth_service.py
│   │   ├── test_financial_service.py
│   │   ├── test_asana_service.py
│   │   └── test_export_service.py
│   ├── routers/                    # Tests de endpoints
│   │   ├── test_auth_router.py
│   │   ├── test_transactions_router.py
│   │   ├── test_asana_router.py
│   │   └── test_exports_router.py
│   └── utils/                      # Tests de utilidades
│       ├── test_validators.py
│       ├── test_formatters.py
│       └── test_encryption.py
├── integration/                    # Tests de integracion (20%)
│   ├── test_auth_flow.py          # Flujo completo autenticacion
│   ├── test_transaction_flow.py   # CRUD transacciones con DB
│   ├── test_asana_sync_flow.py    # Sincronizacion completa Asana
│   ├── test_export_flow.py        # Generacion y descarga exports
│   ├── test_import_yaml_flow.py   # Importacion YAML completa
│   └── test_backup_flow.py        # Proceso de backup
├── e2e/                           # Tests end-to-end (5%)
│   ├── test_user_journey.py       # Journey completo de usuario
│   ├── test_admin_journey.py      # Journey de administrador
│   └── test_asana_integration.py  # Integracion real con Asana
├── fixtures/                      # Datos de prueba
│   ├── users.json
│   ├── transactions.yaml
│   ├── asana_responses.json
│   └── export_samples/
├── factories/                     # Factories para generar datos
│   ├── user_factory.py
│   ├── transaction_factory.py
│   └── asana_factory.py
├── mocks/                         # Mocks reutilizables
│   ├── firestore_mock.py
│   ├── asana_mock.py
│   └── google_auth_mock.py
└── conftest.py                    # Configuracion global pytest
```

### 2.2 Configuracion pytest (pytest.ini)
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --strict-markers
    --cov=src
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=85
    --durations=10
    --tb=short
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Slow tests (> 1s)
    external: Tests that require external services
    security: Security-focused tests
filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
```

---

## 3. Tests unitarios (75%)

### 3.1 Tests de modelos Pydantic
```python
# tests/unit/models/test_user.py
import pytest
from pydantic import ValidationError
from src.models.user import User, SavingsConfig

class TestUser:
    def test_user_creation_valid(self):
        """Test creacion de usuario con datos validos"""
        user = User(
            uid="user_123",
            email="test@example.com",
            display_name="Test User",
            role="user"
        )
        assert user.uid == "user_123"
        assert user.email == "test@example.com"
        assert user.role == "user"

    def test_user_invalid_email(self):
        """Test validacion de email invalido"""
        with pytest.raises(ValidationError) as exc_info:
            User(
                uid="user_123",
                email="invalid-email",
                display_name="Test User",
                role="user"
            )
        assert "email" in str(exc_info.value)

    def test_savings_config_validation(self):
        """Test validacion configuracion ahorro"""
        # Ambos a cero no permitido
        with pytest.raises(ValidationError):
            SavingsConfig(
                minimum_fixed_amount=0,
                target_percentage=0
            )
        
        # Al menos uno debe ser > 0
        config = SavingsConfig(
            minimum_fixed_amount=50000,
            target_percentage=0
        )
        assert config.minimum_fixed_amount == 50000

    @pytest.mark.parametrize("role", ["admin", "user"])
    def test_user_valid_roles(self, role):
        """Test roles validos de usuario"""
        user = User(
            uid="user_123",
            email="test@example.com",
            display_name="Test User",
            role=role
        )
        assert user.role == role

    def test_user_invalid_role(self):
        """Test rol invalido de usuario"""
        with pytest.raises(ValidationError):
            User(
                uid="user_123",
                email="test@example.com",
                display_name="Test User",
                role="invalid_role"
            )
```

### 3.2 Tests de servicios
```python
# tests/unit/services/test_financial_service.py
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import date, datetime
from src.services.financial_service import FinancialService
from src.models.financial import Transaction, TransactionCreate
from tests.factories.transaction_factory import TransactionFactory

class TestFinancialService:
    
    @pytest.fixture
    def mock_firestore(self):
        """Mock del cliente Firestore"""
        with patch('src.infrastructure.firestore_client.FirestoreClient') as mock:
            yield mock

    @pytest.fixture
    def financial_service(self, mock_firestore):
        """Instancia del servicio con mocks"""
        return FinancialService(firestore_client=mock_firestore)

    async def test_create_transaction_success(self, financial_service, mock_firestore):
        """Test creacion exitosa de transaccion"""
        # Arrange
        transaction_data = TransactionCreate(
            type="expense",
            amount=2550,
            description="Test transaction",
            date=date.today(),
            category_id="cat_123",
            account_id="acc_123"
        )
        user_uid = "user_123"
        
        mock_firestore.create_document.return_value = "txn_456"
        
        # Act
        result = await financial_service.create_transaction(
            user_uid=user_uid,
            transaction_data=transaction_data
        )
        
        # Assert
        assert result.id == "txn_456"
        assert result.type == "expense"
        assert result.amount == 2550
        mock_firestore.create_document.assert_called_once()

    async def test_create_transaction_duplicate_external_ref(self, financial_service, mock_firestore):
        """Test error por external_ref duplicado"""
        # Arrange
        transaction_data = TransactionCreate(
            type="expense",
            amount=2550,
            description="Test transaction",
            date=date.today(),
            category_id="cat_123",
            account_id="acc_123",
            external_ref="asana_task_123"
        )
        
        # Simular que ya existe una transaccion con ese external_ref
        mock_firestore.query_documents.return_value = [{"id": "existing_txn"}]
        
        # Act & Assert
        with pytest.raises(DuplicateTransactionError) as exc_info:
            await financial_service.create_transaction(
                user_uid="user_123",
                transaction_data=transaction_data
            )
        
        assert "asana_task_123" in str(exc_info.value)

    @pytest.mark.parametrize("account_exists,category_exists,should_raise", [
        (True, True, False),    # Todo OK
        (False, True, True),    # Cuenta no existe
        (True, False, True),    # Categoria no existe
        (False, False, True),   # Ninguno existe
    ])
    async def test_validate_transaction_references(
        self, financial_service, mock_firestore,
        account_exists, category_exists, should_raise
    ):
        """Test validacion de referencias de transaccion"""
        # Arrange
        mock_firestore.get_document.side_effect = [
            {"id": "acc_123"} if account_exists else None,
            {"id": "cat_123"} if category_exists else None
        ]
        
        transaction_data = TransactionCreate(
            type="expense",
            amount=2550,
            description="Test",
            date=date.today(),
            category_id="cat_123",
            account_id="acc_123"
        )
        
        # Act & Assert
        if should_raise:
            with pytest.raises(ValidationError):
                await financial_service.create_transaction(
                    user_uid="user_123",
                    transaction_data=transaction_data
                )
        else:
            # No deberia lanzar excepcion
            mock_firestore.create_document.return_value = "txn_123"
            result = await financial_service.create_transaction(
                user_uid="user_123",
                transaction_data=transaction_data
            )
            assert result.id == "txn_123"

    async def test_calculate_monthly_stats(self, financial_service, mock_firestore):
        """Test calculo de estadisticas mensuales"""
        # Arrange
        transactions = TransactionFactory.build_batch(
            10,
            date=date(2024, 1, 15),
            type="expense",
            amount=lambda: random.randint(1000, 5000)
        )
        
        mock_firestore.query_documents.return_value = [
            t.dict() for t in transactions
        ]
        
        # Act
        stats = await financial_service.get_monthly_stats(
            user_uid="user_123",
            year=2024,
            month=1
        )
        
        # Assert
        assert stats.period == "2024-01"
        assert stats.total_expense > 0
        assert stats.transaction_count == 10
        assert len(stats.by_category) > 0
```

### 3.3 Tests de routers/endpoints
```python
# tests/unit/routers/test_transactions_router.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from src.main import app
from src.models.financial import Transaction
from tests.factories.transaction_factory import TransactionFactory

class TestTransactionsRouter:
    
    @pytest.fixture
    def client(self):
        """Cliente de prueba FastAPI"""
        return TestClient(app)

    @pytest.fixture
    def mock_auth_middleware(self):
        """Mock del middleware de autenticacion"""
        with patch('src.middleware.auth.verify_session') as mock:
            mock.return_value = {
                "uid": "user_123",
                "email": "test@example.com",
                "role": "user"
            }
            yield mock

    @pytest.fixture
    def mock_financial_service(self):
        """Mock del servicio financiero"""
        with patch('src.services.financial_service.FinancialService') as mock:
            yield mock

    def test_get_transactions_success(
        self, client, mock_auth_middleware, mock_financial_service
    ):
        """Test obtener lista de transacciones"""
        # Arrange
        transactions = TransactionFactory.build_batch(5)
        mock_financial_service.get_transactions.return_value = {
            "transactions": transactions,
            "total_count": 5,
            "has_next": False
        }
        
        # Act
        response = client.get("/api/v1/transactions?page=1&page_size=20")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 5
        assert data["pagination"]["total_count"] == 5
        assert data["pagination"]["has_next"] is False

    def test_create_transaction_success(
        self, client, mock_auth_middleware, mock_financial_service
    ):
        """Test crear transaccion exitosamente"""
        # Arrange
        transaction_data = {
            "type": "expense",
            "amount": 2550,
            "description": "Test transaction",
            "date": "2024-01-15",
            "category_id": "cat_123",
            "account_id": "acc_123"
        }
        
        created_transaction = TransactionFactory.build(**transaction_data)
        mock_financial_service.create_transaction.return_value = created_transaction
        
        # Act
        response = client.post(
            "/api/v1/transactions",
            json=transaction_data,
            headers={"Authorization": "Bearer valid_token"}
        )
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["data"]["type"] == "expense"
        assert data["data"]["amount"] == 2550

    @pytest.mark.parametrize("invalid_data,expected_error", [
        ({"type": "invalid"}, "type"),
        ({"amount": -100}, "amount"),
        ({"date": "invalid-date"}, "date"),
        ({}, "required"),
    ])
    def test_create_transaction_validation_errors(
        self, client, mock_auth_middleware, invalid_data, expected_error
    ):
        """Test errores de validacion al crear transaccion"""
        # Arrange
        base_data = {
            "type": "expense",
            "amount": 2550,
            "description": "Test",
            "date": "2024-01-15",
            "category_id": "cat_123",
            "account_id": "acc_123"
        }
        base_data.update(invalid_data)
        
        # Act
        response = client.post(
            "/api/v1/transactions",
            json=base_data,
            headers={"Authorization": "Bearer valid_token"}
        )
        
        # Assert
        assert response.status_code == 422
        error_data = response.json()
        assert expected_error in str(error_data["error"]["details"])

    def test_get_transaction_not_found(
        self, client, mock_auth_middleware, mock_financial_service
    ):
        """Test obtener transaccion inexistente"""
        # Arrange
        mock_financial_service.get_transaction.side_effect = NotFoundError("Transaction not found")
        
        # Act
        response = client.get("/api/v1/transactions/nonexistent_id")
        
        # Assert
        assert response.status_code == 404
        error_data = response.json()
        assert "not found" in error_data["error"]["message"].lower()

    def test_unauthorized_request(self, client):
        """Test request sin autenticacion"""
        # Act
        response = client.get("/api/v1/transactions")
        
        # Assert
        assert response.status_code == 401
```

---

## 4. Tests de integracion (20%)

### 4.1 Configuracion de entorno de integracion
```python
# tests/conftest.py
import pytest
import asyncio
from testcontainers.firebase import FirebaseEmulatorContainer
from testcontainers.compose import DockerCompose
from src.infrastructure.firestore_client import FirestoreClient
from src.config import get_settings

@pytest.fixture(scope="session")
def event_loop():
    """Event loop para tests async"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def firestore_emulator():
    """Firestore emulator para tests de integracion"""
    with FirebaseEmulatorContainer() as emulator:
        # Configurar variables de entorno para emulator
        os.environ["FIRESTORE_EMULATOR_HOST"] = emulator.get_firestore_host()
        os.environ["FIREBASE_PROJECT_ID"] = "test-project"
        yield emulator

@pytest.fixture
async def firestore_client(firestore_emulator):
    """Cliente Firestore configurado para testing"""
    settings = get_settings()
    settings.firestore_project_id = "test-project"
    settings.use_emulator = True
    
    client = FirestoreClient(settings)
    await client.initialize()
    
    yield client
    
    # Cleanup: limpiar todas las colecciones
    await client.clear_all_collections()

@pytest.fixture
async def sample_user(firestore_client):
    """Usuario de ejemplo para tests"""
    user_data = {
        "uid": "test_user_123",
        "email": "test@example.com",
        "display_name": "Test User",
        "role": "user",
        "preferences": {
            "language": "es",
            "currency": "EUR"
        },
        "savings_config": {
            "minimum_fixed_amount": 50000,
            "target_percentage": 20
        }
    }
    
    await firestore_client.create_document(
        collection="users",
        document_id="test_user_123",
        data=user_data
    )
    
    return user_data

@pytest.fixture
async def sample_categories(firestore_client):
    """Categorias de ejemplo"""
    categories = [
        {
            "id": "cat_food",
            "name": "Alimentacion",
            "type": "expense",
            "icon": "restaurant",
            "color": "#FF5722"
        },
        {
            "id": "cat_salary",
            "name": "Salario",
            "type": "income",
            "icon": "work",
            "color": "#4CAF50"
        }
    ]
    
    for cat in categories:
        await firestore_client.create_document(
            collection=f"accounts/test_user_123/categories",
            document_id=cat["id"],
            data=cat
        )
    
    return categories
```

### 4.2 Tests de flujos completos
```python
# tests/integration/test_transaction_flow.py
import pytest
from datetime import date
from src.services.financial_service import FinancialService
from src.models.financial import TransactionCreate

@pytest.mark.integration
class TestTransactionFlow:
    
    @pytest.fixture
    async def financial_service(self, firestore_client):
        """Servicio financiero con DB real"""
        return FinancialService(firestore_client=firestore_client)

    async def test_complete_transaction_lifecycle(
        self, financial_service, sample_user, sample_categories
    ):
        """Test ciclo completo de vida de transaccion"""
        user_uid = sample_user["uid"]
        
        # 1. Crear cuenta
        account_data = {
            "name": "Cuenta Test",
            "type": "bank",
            "currency": "EUR",
            "initial_balance": 100000
        }
        account = await financial_service.create_account(user_uid, account_data)
        
        # 2. Crear transaccion
        transaction_data = TransactionCreate(
            type="expense",
            amount=2550,
            description="Compra supermercado",
            date=date.today(),
            category_id="cat_food",
            account_id=account.id
        )
        
        transaction = await financial_service.create_transaction(
            user_uid=user_uid,
            transaction_data=transaction_data
        )
        
        # 3. Verificar transaccion creada
        assert transaction.id is not None
        assert transaction.amount == 2550
        assert transaction.type == "expense"
        
        # 4. Verificar balance actualizado
        updated_account = await financial_service.get_account(user_uid, account.id)
        expected_balance = 100000 - 2550  # Balance inicial - gasto
        assert updated_account.balance == expected_balance
        
        # 5. Actualizar transaccion
        update_data = {"amount": 3000, "description": "Compra actualizada"}
        updated_transaction = await financial_service.update_transaction(
            user_uid=user_uid,
            transaction_id=transaction.id,
            update_data=update_data
        )
        
        assert updated_transaction.amount == 3000
        assert updated_transaction.description == "Compra actualizada"
        
        # 6. Verificar balance actualizado tras edicion
        final_account = await financial_service.get_account(user_uid, account.id)
        expected_final_balance = 100000 - 3000
        assert final_account.balance == expected_final_balance
        
        # 7. Eliminar transaccion
        await financial_service.delete_transaction(user_uid, transaction.id)
        
        # 8. Verificar que no existe
        with pytest.raises(NotFoundError):
            await financial_service.get_transaction(user_uid, transaction.id)
        
        # 9. Verificar balance restaurado
        restored_account = await financial_service.get_account(user_uid, account.id)
        assert restored_account.balance == 100000

    async def test_transaction_statistics_calculation(
        self, financial_service, sample_user, sample_categories
    ):
        """Test calculo de estadisticas con transacciones reales"""
        user_uid = sample_user["uid"]
        
        # Crear cuenta
        account = await financial_service.create_account(user_uid, {
            "name": "Test Account",
            "type": "bank",
            "currency": "EUR",
            "initial_balance": 0
        })
        
        # Crear multiple transacciones
        transactions_data = [
            {"type": "expense", "amount": 2500, "category_id": "cat_food"},
            {"type": "expense", "amount": 1500, "category_id": "cat_food"},
            {"type": "income", "amount": 200000, "category_id": "cat_salary"},
            {"type": "expense", "amount": 3000, "category_id": "cat_food"},
        ]
        
        for tx_data in transactions_data:
            tx_data.update({
                "description": f"Test {tx_data['type']}",
                "date": date.today(),
                "account_id": account.id
            })
            await financial_service.create_transaction(
                user_uid=user_uid,
                transaction_data=TransactionCreate(**tx_data)
            )
        
        # Obtener estadisticas
        stats = await financial_service.get_monthly_stats(
            user_uid=user_uid,
            year=date.today().year,
            month=date.today().month
        )
        
        # Verificar calculos
        assert stats.total_income == 200000
        assert stats.total_expense == 7000  # 2500 + 1500 + 3000
        assert stats.net_balance == 193000  # 200000 - 7000
        assert stats.transaction_count == 4
        
        # Verificar agrupacion por categoria
        food_category = next(
            (cat for cat in stats.by_category if cat.category_id == "cat_food"),
            None
        )
        assert food_category is not None
        assert food_category.amount == 7000
        assert food_category.transaction_count == 3
```

### 4.3 Tests de integracion con Asana
```python
# tests/integration/test_asana_sync_flow.py
import pytest
from unittest.mock import patch, AsyncMock
from src.services.asana_service import AsanaService
from tests.mocks.asana_mock import AsanaMockClient

@pytest.mark.integration
@pytest.mark.external
class TestAsanaSyncFlow:
    
    @pytest.fixture
    def mock_asana_client(self):
        """Mock cliente Asana con respuestas realistas"""
        return AsanaMockClient()

    @pytest.fixture
    async def asana_service(self, firestore_client, mock_asana_client):
        """Servicio Asana con mocks"""
        return AsanaService(
            firestore_client=firestore_client,
            asana_client=mock_asana_client
        )

    async def test_complete_asana_sync_flow(
        self, asana_service, sample_user, sample_categories
    ):
        """Test flujo completo de sincronizacion Asana"""
        user_uid = sample_user["uid"]
        
        # 1. Configurar integracion Asana
        config = {
            "project_gid": "project_123",
            "sections_mapping": {
                "expenses_pending": "section_101",
                "expenses_processed": "section_102",
                "incomes_pending": "section_103",
                "incomes_processed": "section_104"
            },
            "field_mapping": {
                "amount_field": "custom_field_amount",
                "category_extraction": "tags"
            }
        }
        
        await asana_service.save_configuration(user_uid, config)
        
        # 2. Mock tareas pendientes en Asana
        pending_tasks = [
            {
                "gid": "task_001",
                "name": "Supermercado 25.50€",
                "notes": "Compra semanal",
                "due_date": "2024-01-15",
                "memberships": [{"section": {"gid": "section_101"}}],
                "tags": [{"name": "alimentacion"}]
            },
            {
                "gid": "task_002", 
                "name": "Freelance project €500",
                "due_date": "2024-01-15",
                "memberships": [{"section": {"gid": "section_103"}}],
                "tags": [{"name": "trabajo"}]
            }
        ]
        
        asana_service.asana_client.set_pending_tasks(pending_tasks)
        
        # 3. Ejecutar sincronizacion
        sync_result = await asana_service.sync_tasks(user_uid)
        
        # 4. Verificar resultados de sync
        assert sync_result.tasks_read == 2
        assert sync_result.expenses_created == 1
        assert sync_result.incomes_created == 1
        assert sync_result.tasks_moved == 2
        assert sync_result.errors == 0
        
        # 5. Verificar transacciones creadas en DB
        transactions = await asana_service.get_transactions_by_external_ref(
            user_uid, ["task_001", "task_002"]
        )
        
        assert len(transactions) == 2
        
        expense_tx = next(tx for tx in transactions if tx.external_ref == "task_001")
        assert expense_tx.type == "expense"
        assert expense_tx.amount == 2550  # 25.50€ en centimos
        assert "Supermercado" in expense_tx.description
        
        income_tx = next(tx for tx in transactions if tx.external_ref == "task_002")
        assert income_tx.type == "income"
        assert income_tx.amount == 50000  # 500€ en centimos
        
        # 6. Verificar que tareas se movieron en Asana
        moved_tasks = asana_service.asana_client.get_moved_tasks()
        assert len(moved_tasks) == 2
        assert moved_tasks[0]["from_section"] == "section_101"
        assert moved_tasks[0]["to_section"] == "section_102"
        assert moved_tasks[1]["from_section"] == "section_103"
        assert moved_tasks[1]["to_section"] == "section_104"

    async def test_sync_idempotency(
        self, asana_service, sample_user
    ):
        """Test que sync es idempotente"""
        user_uid = sample_user["uid"]
        
        # Configurar y ejecutar primera sync
        await asana_service.save_configuration(user_uid, {
            "project_gid": "project_123",
            "sections_mapping": {
                "expenses_pending": "section_101",
                "expenses_processed": "section_102"
            }
        })
        
        # Mock tarea pendiente
        pending_task = {
            "gid": "task_duplicate",
            "name": "Test 10€",
            "memberships": [{"section": {"gid": "section_101"}}]
        }
        asana_service.asana_client.set_pending_tasks([pending_task])
        
        # Primera sync
        result1 = await asana_service.sync_tasks(user_uid)
        assert result1.expenses_created == 1
        
        # Segunda sync con misma tarea (deberia detectar duplicado)
        result2 = await asana_service.sync_tasks(user_uid)
        assert result2.expenses_created == 0  # No crear duplicado
        assert result2.skipped == 1  # Tarea ya procesada
        
        # Verificar solo una transaccion en DB
        transactions = await asana_service.get_transactions_by_external_ref(
            user_uid, ["task_duplicate"]
        )
        assert len(transactions) == 1
```

---

## 5. Tests end-to-end (5%)

### 5.1 Journey completo de usuario
```python
# tests/e2e/test_user_journey.py
import pytest
import asyncio
from fastapi.testclient import TestClient
from src.main import app

@pytest.mark.e2e
@pytest.mark.slow
class TestUserJourney:
    
    @pytest.fixture(scope="class")
    def client(self):
        """Cliente E2E con app completa"""
        return TestClient(app)

    def test_complete_user_journey(self, client):
        """Test journey completo: login -> crear datos -> asana -> export"""
        
        # 1. Login con Google (mock)
        login_response = client.post("/api/v1/auth/login", json={
            "google_id_token": "mock_valid_token",
            "invitation_code": "VALID_INVITE_123"
        })
        assert login_response.status_code == 200
        
        session_cookie = login_response.cookies.get("session")
        headers = {"Cookie": f"session={session_cookie}"}
        
        # 2. Verificar perfil de usuario
        profile_response = client.get("/api/v1/auth/profile", headers=headers)
        assert profile_response.status_code == 200
        user_data = profile_response.json()["data"]
        
        # 3. Crear categorias
        category_response = client.post("/api/v1/categories", 
            headers=headers,
            json={
                "name": "Alimentacion",
                "type": "expense",
                "icon": "restaurant",
                "color": "#FF5722"
            }
        )
        assert category_response.status_code == 201
        category = category_response.json()["data"]
        
        # 4. Crear cuenta
        account_response = client.post("/api/v1/accounts",
            headers=headers,
            json={
                "name": "Cuenta Principal",
                "type": "bank",
                "currency": "EUR",
                "initial_balance": 100000
            }
        )
        assert account_response.status_code == 201
        account = account_response.json()["data"]
        
        # 5. Crear transaccion
        transaction_response = client.post("/api/v1/transactions",
            headers=headers,
            json={
                "type": "expense",
                "amount": 2550,
                "description": "Supermercado",
                "date": "2024-01-15",
                "category_id": category["id"],
                "account_id": account["id"]
            }
        )
        assert transaction_response.status_code == 201
        
        # 6. Obtener estadisticas
        stats_response = client.get("/api/v1/transactions/stats", headers=headers)
        assert stats_response.status_code == 200
        stats = stats_response.json()["data"]
        assert stats["summary"]["total_expense"] == 2550
        
        # 7. Configurar Asana (mock)
        asana_config_response = client.put("/api/v1/asana/config",
            headers=headers,
            json={
                "project_gid": "mock_project_123",
                "sections_mapping": {
                    "expenses_pending": "section_101",
                    "expenses_processed": "section_102"
                }
            }
        )
        assert asana_config_response.status_code == 200
        
        # 8. Ejecutar sync Asana
        sync_response = client.post("/api/v1/asana/sync", 
            headers=headers,
            json={"dry_run": False}
        )
        assert sync_response.status_code == 200
        
        # 9. Crear export para LLM
        export_response = client.post("/api/v1/exports",
            headers=headers,
            json={
                "name": "Export Test",
                "date_from": "2024-01-01",
                "date_to": "2024-01-31",
                "include_types": ["transactions", "categories"],
                "anonymize": True
            }
        )
        assert export_response.status_code == 201
        export_data = export_response.json()["data"]
        
        # 10. Esperar procesamiento y descargar
        # En test real, polling hasta status = "ready"
        download_response = client.get(
            f"/api/v1/exports/{export_data['export_id']}/download",
            headers=headers
        )
        assert download_response.status_code == 200
        assert download_response.headers["content-type"] == "application/zip"
        
        # 11. Logout
        logout_response = client.post("/api/v1/auth/logout", headers=headers)
        assert logout_response.status_code == 204
```

---

## 6. Mocking y fixtures

### 6.1 Factories para datos de prueba
```python
# tests/factories/transaction_factory.py
import factory
from datetime import date, timedelta
import random
from src.models.financial import Transaction, TransactionType

class TransactionFactory(factory.Factory):
    class Meta:
        model = Transaction
    
    id = factory.Sequence(lambda n: f"txn_{n:03d}")
    type = factory.Iterator([TransactionType.EXPENSE, TransactionType.INCOME])
    amount = factory.LazyFunction(lambda: random.randint(1000, 10000))
    currency = "EUR"
    description = factory.Faker("sentence", nb_words=3)
    date = factory.LazyFunction(lambda: date.today() - timedelta(days=random.randint(0, 30)))
    category_id = factory.Sequence(lambda n: f"cat_{n:03d}")
    account_id = factory.Sequence(lambda n: f"acc_{n:03d}")
    tags = factory.LazyFunction(lambda: [f"tag_{i}" for i in range(random.randint(0, 3))])
    external_ref = None
    created_at = factory.Faker("date_time_this_month")
    updated_at = factory.LazyAttribute(lambda obj: obj.created_at)

class ExpenseTransactionFactory(TransactionFactory):
    type = TransactionType.EXPENSE
    amount = factory.LazyFunction(lambda: random.randint(1000, 5000))

class IncomeTransactionFactory(TransactionFactory):
    type = TransactionType.INCOME
    amount = factory.LazyFunction(lambda: random.randint(50000, 200000))

class AsanaTransactionFactory(TransactionFactory):
    external_ref = factory.Sequence(lambda n: f"asana_task_{n:03d}")
    description = factory.LazyAttribute(lambda obj: f"Asana: {obj.description}")
```

### 6.2 Mocks para servicios externos
```python
# tests/mocks/asana_mock.py
from typing import List, Dict, Any
from unittest.mock import AsyncMock

class AsanaMockClient:
    """Mock del cliente Asana para testing"""
    
    def __init__(self):
        self.pending_tasks = []
        self.moved_tasks = []
        self.projects = []
        self.oauth_tokens = {}
    
    def set_pending_tasks(self, tasks: List[Dict[str, Any]]):
        """Configurar tareas pendientes mock"""
        self.pending_tasks = tasks
    
    async def get_tasks_from_section(self, section_gid: str) -> List[Dict[str, Any]]:
        """Mock obtener tareas de seccion"""
        return [
            task for task in self.pending_tasks 
            if any(
                membership.get("section", {}).get("gid") == section_gid 
                for membership in task.get("memberships", [])
            )
        ]
    
    async def move_task_to_section(self, task_gid: str, section_gid: str):
        """Mock mover tarea a seccion"""
        # Encontrar tarea y seccion actual
        task = next((t for t in self.pending_tasks if t["gid"] == task_gid), None)
        if task:
            current_section = task["memberships"][0]["section"]["gid"]
            self.moved_tasks.append({
                "task_gid": task_gid,
                "from_section": current_section,
                "to_section": section_gid
            })
            # Actualizar seccion en mock
            task["memberships"][0]["section"]["gid"] = section_gid
    
    async def get_projects(self, workspace_gid: str = None) -> List[Dict[str, Any]]:
        """Mock obtener proyectos"""
        return self.projects
    
    def get_moved_tasks(self) -> List[Dict[str, Any]]:
        """Obtener historial de tareas movidas"""
        return self.moved_tasks

# tests/mocks/firestore_mock.py
class FirestoreMock:
    """Mock simple de Firestore para unit tests"""
    
    def __init__(self):
        self.collections = {}
        self.call_history = []
    
    def create_document(self, collection: str, data: Dict[str, Any], document_id: str = None):
        """Mock crear documento"""
        self.call_history.append(("create", collection, data))
        
        if collection not in self.collections:
            self.collections[collection] = {}
        
        doc_id = document_id or f"doc_{len(self.collections[collection])}"
        self.collections[collection][doc_id] = {**data, "id": doc_id}
        
        return doc_id
    
    def get_document(self, collection: str, document_id: str):
        """Mock obtener documento"""
        self.call_history.append(("get", collection, document_id))
        return self.collections.get(collection, {}).get(document_id)
    
    def query_documents(self, collection: str, filters: List = None):
        """Mock consultar documentos"""
        self.call_history.append(("query", collection, filters))
        return list(self.collections.get(collection, {}).values())
    
    def update_document(self, collection: str, document_id: str, data: Dict[str, Any]):
        """Mock actualizar documento"""
        self.call_history.append(("update", collection, document_id, data))
        if collection in self.collections and document_id in self.collections[collection]:
            self.collections[collection][document_id].update(data)
            return True
        return False
    
    def delete_document(self, collection: str, document_id: str):
        """Mock eliminar documento"""
        self.call_history.append(("delete", collection, document_id))
        if collection in self.collections and document_id in self.collections[collection]:
            del self.collections[collection][document_id]
            return True
        return False
```

---

## 7. Metricas de calidad y CI/CD

### 7.1 Pipeline de CI/CD
```yaml
# .github/workflows/test.yml
name: Test Suite

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      firestore:
        image: gcr.io/google.com/cloudsdktool/cloud-sdk:emulators
        ports:
          - 8080:8080
        env:
          FIRESTORE_PROJECT_ID: test-project
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-test.txt
    
    - name: Start Firestore emulator
      run: |
        gcloud emulators firestore start --host-port=localhost:8080 &
        sleep 10
    
    - name: Run linting
      run: |
        ruff check src tests
        black --check src tests
        mypy src
    
    - name: Run security scan
      run: bandit -r src
    
    - name: Run unit tests
      run: |
        pytest tests/unit -v --cov=src --cov-report=xml
        
    - name: Run integration tests
      run: |
        pytest tests/integration -v --cov=src --cov-append
        
    - name: Run E2E tests
      run: |
        pytest tests/e2e -v --cov=src --cov-append
        
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
    
    - name: Check coverage threshold
      run: |
        coverage report --fail-under=85
```

### 7.2 Metricas de calidad
```python
# scripts/quality_check.py
"""Script para verificar metricas de calidad"""

import subprocess
import sys
from pathlib import Path

def run_command(cmd: str) -> tuple[int, str]:
    """Ejecutar comando y retornar codigo y output"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr

def check_coverage():
    """Verificar cobertura minima"""
    code, output = run_command("coverage report --show-missing")
    
    # Extraer porcentaje total
    lines = output.strip().split('\n')
    total_line = [line for line in lines if 'TOTAL' in line]
    
    if total_line:
        total_coverage = int(total_line[0].split()[-1].replace('%', ''))
        print(f"Coverage total: {total_coverage}%")
        
        if total_coverage < 85:
            print("❌ Coverage below minimum threshold (85%)")
            return False
        else:
            print("✅ Coverage meets threshold")
            return True
    
    print("❌ Could not determine coverage")
    return False

def check_test_performance():
    """Verificar performance de tests"""
    code, output = run_command("pytest --durations=10 -q")
    
    # Buscar tests lentos (> 1s)
    slow_tests = []
    for line in output.split('\n'):
        if 's call' in line and 'test_' in line:
            parts = line.split()
            duration = float(parts[0].replace('s', ''))
            if duration > 1.0:
                slow_tests.append((parts[-1], duration))
    
    if slow_tests:
        print(f"⚠️  Found {len(slow_tests)} slow tests (>1s):")
        for test_name, duration in slow_tests[:5]:  # Top 5
            print(f"  - {test_name}: {duration}s")
    else:
        print("✅ No slow tests detected")
    
    return True

def check_flaky_tests():
    """Verificar tests flaky ejecutando 3 veces"""
    print("Checking for flaky tests (3 runs)...")
    
    for i in range(3):
        code, output = run_command("pytest tests/unit tests/integration -x -q")
        if code != 0:
            print(f"❌ Test run {i+1} failed - possible flaky test")
            print(output[-500:])  # Last 500 chars
            return False
    
    print("✅ No flaky tests detected")
    return True

def main():
    """Ejecutar todas las verificaciones"""
    checks = [
        ("Coverage", check_coverage),
        ("Performance", check_test_performance),
        ("Flaky tests", check_flaky_tests),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n🔍 Checking {name}...")
        results.append(check_func())
    
    if all(results):
        print("\n✅ All quality checks passed!")
        sys.exit(0)
    else:
        print("\n❌ Some quality checks failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

### 7.3 Configuracion de herramientas
```toml
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "--strict-markers",
    "--strict-config",
    "--cov=src",
    "--cov-report=term-missing",
    "--cov-report=html:htmlcov",
    "--cov-report=xml",
    "--cov-fail-under=85",
]
markers = [
    "unit: Unit tests",
    "integration: Integration tests", 
    "e2e: End-to-end tests",
    "slow: Slow tests (>1s)",
    "external: Tests requiring external services",
    "security: Security-focused tests",
]

[tool.coverage.run]
source = ["src"]
omit = [
    "*/tests/*",
    "*/venv/*",
    "*/__pycache__/*",
    "*/migrations/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
]

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true

[tool.ruff]
target-version = "py311"
line-length = 88
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings  
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "UP",  # pyupgrade
]
ignore = ["E501"]  # line too long (handled by black)

[tool.black]
line-length = 88
target-version = ['py311']
include = '\.pyi?$'
```

---

## 8. Mejores practicas y guidelines

### 8.1 Naming conventions
```python
# ✅ Buenos nombres de tests
def test_create_transaction_with_valid_data_should_return_transaction():
    """Test descriptivo que explica comportamiento esperado"""
    pass

def test_create_transaction_with_duplicate_external_ref_should_raise_error():
    """Test de caso de error especifico"""
    pass

def test_calculate_monthly_stats_with_multiple_transactions_should_group_by_category():
    """Test de comportamiento complejo"""
    pass

# ❌ Malos nombres
def test_transaction():  # Muy generico
    pass

def test_create():  # No especifica que se crea
    pass

def test_error():  # No especifica que error
    pass
```

### 8.2 Estructura de tests (AAA pattern)
```python
def test_create_transaction_success(self, financial_service, mock_firestore):
    """Test creation of transaction with valid data"""
    
    # Arrange - Preparar datos y mocks
    transaction_data = TransactionCreate(
        type="expense",
        amount=2550,
        description="Test transaction",
        date=date.today(),
        category_id="cat_123",
        account_id="acc_123"
    )
    user_uid = "user_123"
    
    mock_firestore.create_document.return_value = "txn_456"
    mock_firestore.get_document.side_effect = [
        {"id": "acc_123"},  # Account exists
        {"id": "cat_123"}   # Category exists
    ]
    
    # Act - Ejecutar la accion a testear
    result = await financial_service.create_transaction(
        user_uid=user_uid,
        transaction_data=transaction_data
    )
    
    # Assert - Verificar resultados
    assert result.id == "txn_456"
    assert result.type == "expense"
    assert result.amount == 2550
    assert result.description == "Test transaction"
    
    # Verificar llamadas a dependencias
    mock_firestore.create_document.assert_called_once()
    assert mock_firestore.get_document.call_count == 2
```

### 8.3 Parametrized tests
```python
@pytest.mark.parametrize("amount,expected_error", [
    (-100, "Amount must be positive"),
    (0, "Amount must be positive"), 
    (999999999999, "Amount too large"),
])
def test_transaction_amount_validation(amount, expected_error):
    """Test various invalid amounts"""
    with pytest.raises(ValidationError) as exc_info:
        TransactionCreate(
            type="expense",
            amount=amount,
            description="Test",
            date=date.today(),
            category_id="cat_123",
            account_id="acc_123"
        )
    assert expected_error in str(exc_info.value)

@pytest.mark.parametrize("transaction_type,category_type,should_pass", [
    ("expense", "expense", True),
    ("income", "income", True),
    ("expense", "income", False),
    ("income", "expense", False),
])
def test_transaction_category_type_matching(transaction_type, category_type, should_pass):
    """Test transaction type must match category type"""
    # Test implementation...
```

### 8.4 Fixtures efectivos
```python
@pytest.fixture(scope="session")
def app():
    """App instance for testing (session scope for performance)"""
    return create_app(testing=True)

@pytest.fixture(scope="function")  # Reset per test
def clean_database(firestore_client):
    """Clean database before each test"""
    yield firestore_client
    # Cleanup after test
    asyncio.run(firestore_client.clear_all_collections())

@pytest.fixture
def authenticated_user(app, firestore_client):
    """Pre-authenticated user for tests"""
    user_data = UserFactory.build()
    
    # Create user in database
    firestore_client.create_document(
        "users", user_data.dict(), user_data.uid
    )
    
    # Mock authentication
    with patch('src.middleware.auth.get_current_user') as mock_auth:
        mock_auth.return_value = user_data
        yield user_data
```

---

## 9. Monitoring y metricas de tests

### 9.1 Dashboard de metricas
```python
# scripts/test_metrics.py
"""Generar reporte de metricas de testing"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime

def parse_coverage_xml():
    """Parsear reporte de coverage XML"""
    tree = ET.parse('coverage.xml')
    root = tree.getroot()
    
    total_lines = int(root.attrib['lines-valid'])
    covered_lines = int(root.attrib['lines-covered'])
    coverage_percentage = (covered_lines / total_lines) * 100
    
    return {
        'total_lines': total_lines,
        'covered_lines': covered_lines,
        'coverage_percentage': round(coverage_percentage, 2),
        'missing_lines': total_lines - covered_lines
    }

def parse_pytest_json():
    """Parsear reporte de pytest JSON"""
    with open('.pytest_cache/v/cache/nodeids') as f:
        test_nodeids = f.read().strip().split('\n')
    
    unit_tests = len([t for t in test_nodeids if '/unit/' in t])
    integration_tests = len([t for t in test_nodeids if '/integration/' in t])
    e2e_tests = len([t for t in test_nodeids if '/e2e/' in t])
    
    return {
        'total_tests': len(test_nodeids),
        'unit_tests': unit_tests,
        'integration_tests': integration_tests,
        'e2e_tests': e2e_tests,
        'pyramid_ratio': {
            'unit': round((unit_tests / len(test_nodeids)) * 100, 1),
            'integration': round((integration_tests / len(test_nodeids)) * 100, 1),
            'e2e': round((e2e_tests / len(test_nodeids)) * 100, 1)
        }
    }

def generate_report():
    """Generar reporte completo"""
    coverage_data = parse_coverage_xml()
    test_data = parse_pytest_json()
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'coverage': coverage_data,
        'tests': test_data,
        'quality_gates': {
            'coverage_threshold': 85,
            'coverage_passed': coverage_data['coverage_percentage'] >= 85,
            'pyramid_compliance': test_data['pyramid_ratio']['unit'] >= 70
        }
    }
    
    # Guardar reporte
    with open('test_metrics.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    # Mostrar resumen
    print(f"📊 Test Metrics Report")
    print(f"Coverage: {coverage_data['coverage_percentage']}%")
    print(f"Total Tests: {test_data['total_tests']}")
    print(f"Unit: {test_data['unit_tests']} ({test_data['pyramid_ratio']['unit']}%)")
    print(f"Integration: {test_data['integration_tests']} ({test_data['pyramid_ratio']['integration']}%)")
    print(f"E2E: {test_data['e2e_tests']} ({test_data['pyramid_ratio']['e2e']}%)")
    
    return report

if __name__ == "__main__":
    generate_report()
```

### 9.2 Alertas de calidad
```python
# scripts/quality_alerts.py
"""Sistema de alertas para metricas de calidad"""

def check_quality_degradation():
    """Verificar degradacion de calidad vs baseline"""
    
    # Cargar metricas actuales y baseline
    with open('test_metrics.json') as f:
        current = json.load(f)
    
    try:
        with open('baseline_metrics.json') as f:
            baseline = json.load(f)
    except FileNotFoundError:
        print("⚠️  No baseline found, creating one")
        with open('baseline_metrics.json', 'w') as f:
            json.dump(current, f, indent=2)
        return
    
    alerts = []
    
    # Check coverage degradation
    coverage_diff = current['coverage']['coverage_percentage'] - baseline['coverage']['coverage_percentage']
    if coverage_diff < -2:  # More than 2% drop
        alerts.append(f"Coverage dropped by {abs(coverage_diff):.1f}% (now {current['coverage']['coverage_percentage']}%)")
    
    # Check test count growth
    test_diff = current['tests']['total_tests'] - baseline['tests']['total_tests']
    if test_diff < 0:
        alerts.append(f"Test count decreased by {abs(test_diff)} tests")
    
    # Check pyramid ratios
    unit_diff = current['tests']['pyramid_ratio']['unit'] - baseline['tests']['pyramid_ratio']['unit']
    if unit_diff < -5:  # More than 5% drop in unit test ratio
        alerts.append(f"Unit test ratio dropped by {abs(unit_diff):.1f}%")
    
    if alerts:
        print("🚨 Quality Alerts:")
        for alert in alerts:
            print(f"  - {alert}")
        return False
    else:
        print("✅ No quality degradation detected")
        return True
```

---

Esta estrategia de testing proporciona una base solida para garantizar la calidad del backend, con enfoque en automatizacion, metricas claras y integracion con CI/CD, manteniendo coherencia con la arquitectura y principios de seguridad establecidos.