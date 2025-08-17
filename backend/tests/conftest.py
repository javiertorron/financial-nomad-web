"""
Global pytest configuration and fixtures.
"""

import os
import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import patch, MagicMock
import pytest.mock

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from src.config import Settings, get_settings


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Test settings configuration."""
    return Settings(
        app_name="financial-nomad-api-test",
        version="1.0.0-test",
        debug=True,
        environment="testing",
        
        # Security
        secret_key="test-secret-key-change-in-production",
        google_client_id="test-google-client-id",
        session_expire_hours=1,  # Short for testing
        
        # Database
        firestore_project_id="test-project",
        firestore_database="(default)",
        use_firestore_emulator=True,
        firestore_emulator_host="localhost:8081",  # Different port
        
        # API
        api_prefix="/api/v1",
        cors_origins=["http://localhost:3000"],
        rate_limit_per_minute=1000,  # High limit for testing
        
        # External
        google_auth_url="https://oauth2.googleapis.com/tokeninfo",
        
        # Monitoring
        log_level="DEBUG",
        sentry_dsn=None,
        
        # Server
        host="127.0.0.1",
        port=8081,
        workers=1
    )


@pytest.fixture(scope="session")
def app_with_test_settings(test_settings):
    """FastAPI app with test settings."""
    with patch('src.config.settings', test_settings):
        from src.main import create_app
        return create_app()


@pytest.fixture
def client(app_with_test_settings) -> TestClient:
    """Synchronous test client."""
    return TestClient(app_with_test_settings)


@pytest.fixture
async def async_client(app_with_test_settings) -> AsyncGenerator[AsyncClient, None]:
    """Asynchronous test client."""
    async with AsyncClient(
        app=app_with_test_settings,
        base_url="http://testserver"
    ) as ac:
        yield ac


@pytest.fixture
def mock_firestore():
    """Mock Firestore client."""
    with patch('src.infrastructure.firestore_client.FirestoreClient') as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        
        # Configure common mock methods
        mock_instance.initialize = MagicMock()
        mock_instance.create_document = MagicMock()
        mock_instance.get_document = MagicMock()
        mock_instance.update_document = MagicMock()
        mock_instance.delete_document = MagicMock()
        mock_instance.query_documents = MagicMock()
        mock_instance.transaction_write = MagicMock()
        
        yield mock_instance


@pytest.fixture
def mock_google_auth():
    """Mock Google auth client."""
    with patch('src.infrastructure.auth_client.GoogleAuthClient') as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        
        # Default successful verification
        mock_instance.verify_id_token.return_value = {
            "sub": "google_user_123",
            "email": "test@example.com",
            "email_verified": True,
            "name": "Test User",
            "picture": "https://example.com/avatar.jpg"
        }
        
        yield mock_instance


@pytest.fixture
def mock_auth_middleware():
    """Mock authentication middleware."""
    with patch('src.middleware.auth.get_current_user') as mock:
        mock.return_value = {
            "uid": "test_user_123",
            "email": "test@example.com",
            "role": "user"
        }
        yield mock


@pytest.fixture
def mock_admin_auth_middleware():
    """Mock admin authentication middleware."""
    with patch('src.middleware.auth.get_current_user') as mock:
        mock.return_value = {
            "uid": "test_admin_123",
            "email": "admin@example.com",
            "role": "admin"
        }
        yield mock


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "uid": "test_user_123",
        "email": "test@example.com",
        "display_name": "Test User",
        "role": "user",
        "preferences": {
            "language": "es",
            "currency": "EUR",
            "timezone": "Europe/Madrid"
        },
        "savings_config": {
            "minimum_fixed_amount": 50000,  # 500 euros in centimos
            "target_percentage": 20
        },
        "is_active": True,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "last_login": None
    }


@pytest.fixture
def sample_invitation_data():
    """Sample invitation data for testing."""
    return {
        "code": "INV_TEST123",
        "email": "newuser@example.com",
        "issued_by": "test_admin_123",
        "status": "pending",
        "expires_at": "2024-12-31T23:59:59Z",
        "consumed_by": None,
        "consumed_at": None,
        "created_at": "2024-01-01T00:00:00Z"
    }


@pytest.fixture
def sample_account_data():
    """Sample account data for testing."""
    return {
        "id": "acc_test123",
        "name": "Test Account",
        "type": "bank",
        "bank_name": "Test Bank",
        "last_four_digits": "1234",
        "currency": "EUR",
        "balance": 100000,  # 1000 euros in centimos
        "is_default": True,
        "is_active": True,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
    }


@pytest.fixture
def sample_category_data():
    """Sample category data for testing."""
    return {
        "id": "cat_test123",
        "name": "Test Category",
        "type": "expense",
        "parent_id": None,
        "icon": "folder",
        "color": "#FF5722",
        "is_active": True,
        "transaction_count": 0,
        "created_at": "2024-01-01T00:00:00Z"
    }


@pytest.fixture
def sample_transaction_data():
    """Sample transaction data for testing."""
    return {
        "id": "txn_test123",
        "type": "expense",
        "amount": 2550,  # 25.50 euros in centimos
        "currency": "EUR",
        "description": "Test Transaction",
        "date": "2024-01-15",
        "category_id": "cat_test123",
        "account_id": "acc_test123",
        "tags": ["test", "sample"],
        "external_ref": None,
        "attachments": [],
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-15T10:30:00Z"
    }


@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment variables after each test."""
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)


# Pytest markers
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "slow: Slow tests (>1s)")
    config.addinivalue_line("markers", "external: Tests requiring external services")
    config.addinivalue_line("markers", "security: Security-focused tests")


# Test utilities
class TestDatabase:
    """Utilities for database testing."""
    
    def __init__(self, firestore_mock):
        self.firestore = firestore_mock
        self.collections = {}
    
    def create_document(self, collection: str, data: dict, doc_id: str = None):
        """Create a document in mock database."""
        if collection not in self.collections:
            self.collections[collection] = {}
        
        doc_id = doc_id or f"doc_{len(self.collections[collection])}"
        self.collections[collection][doc_id] = {**data, "id": doc_id}
        
        return doc_id
    
    def get_document(self, collection: str, doc_id: str):
        """Get a document from mock database."""
        return self.collections.get(collection, {}).get(doc_id)
    
    def query_documents(self, collection: str, filters=None):
        """Query documents from mock database."""
        docs = list(self.collections.get(collection, {}).values())
        
        if filters:
            for field, operator, value in filters:
                if operator == "==":
                    docs = [doc for doc in docs if doc.get(field) == value]
                elif operator == ">":
                    docs = [doc for doc in docs if doc.get(field, 0) > value]
                elif operator == "<":
                    docs = [doc for doc in docs if doc.get(field, 0) < value]
        
        return docs
    
    def clear_collection(self, collection: str):
        """Clear a collection in mock database."""
        if collection in self.collections:
            self.collections[collection].clear()
    
    def clear_all(self):
        """Clear all collections in mock database."""
        self.collections.clear()


@pytest.fixture
def test_db(mock_firestore):
    """Test database utilities."""
    db = TestDatabase(mock_firestore)
    
    # Configure mock to use test database
    mock_firestore.create_document.side_effect = db.create_document
    mock_firestore.get_document.side_effect = db.get_document
    mock_firestore.query_documents.side_effect = db.query_documents
    
    yield db
    
    # Cleanup
    db.clear_all()