"""
Unit tests for backup service.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.services.backup import BackupService, get_backup_service
from src.models.backup import (
    BackupConfiguration,
    BackupType,
    BackupDestination,
    BackupStatus,
    BackupTriggerRequest
)
from src.utils.exceptions import NotFoundError, ValidationError as AppValidationError


class TestBackupService:
    """Test cases for BackupService."""
    
    @pytest.fixture
    def backup_service(self, mock_firestore):
        """Create backup service with mocked dependencies."""
        with patch('src.services.backup.get_firestore', return_value=mock_firestore):
            with patch('src.services.backup.get_settings') as mock_settings:
                mock_settings.return_value.backup_encryption_key = 'test-encryption-key-32-characters'
                return BackupService()
    
    @pytest.fixture
    def sample_backup_config(self):
        """Sample backup configuration."""
        return {
            'auto_backup_enabled': True,
            'backup_frequency': BackupType.SCHEDULED_WEEKLY,
            'destinations': [BackupDestination.LOCAL_STORAGE],
            'retention_days': 30,
            'include_attachments': True,
            'encryption_enabled': True
        }
    
    @pytest.fixture
    def sample_trigger_request(self):
        """Sample backup trigger request."""
        return BackupTriggerRequest(
            backup_type=BackupType.MANUAL,
            destinations=[BackupDestination.LOCAL_STORAGE],
            include_attachments=True,
            notify_on_completion=False
        )
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_backup_configuration_exists(self, backup_service, mock_firestore, sample_backup_config):
        """Test getting existing backup configuration."""
        # Setup
        config_data = {
            'id': 'config_123',
            'user_id': 'user_123',
            **sample_backup_config,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        mock_firestore.query_documents.return_value = [BackupConfiguration(**config_data)]
        
        # Execute
        result = await backup_service.get_backup_configuration('user_123')
        
        # Assert
        assert result is not None
        assert result.id == 'config_123'
        assert result.user_id == 'user_123'
        assert result.auto_backup_enabled is True
        mock_firestore.query_documents.assert_called_once()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_backup_configuration_not_exists(self, backup_service, mock_firestore):
        """Test getting non-existent backup configuration."""
        # Setup
        mock_firestore.query_documents.return_value = []
        
        # Execute
        result = await backup_service.get_backup_configuration('user_123')
        
        # Assert
        assert result is None
        mock_firestore.query_documents.assert_called_once()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_backup_configuration(self, backup_service, mock_firestore, sample_backup_config):
        """Test creating new backup configuration."""
        # Setup
        mock_firestore.query_documents.return_value = []  # No existing config
        mock_firestore.create_document = AsyncMock()
        
        # Execute
        result = await backup_service.create_or_update_backup_configuration('user_123', sample_backup_config)
        
        # Assert
        assert result is not None
        assert result.user_id == 'user_123'
        assert result.auto_backup_enabled is True
        mock_firestore.create_document.assert_called_once()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_backup_configuration(self, backup_service, mock_firestore, sample_backup_config):
        """Test updating existing backup configuration."""
        # Setup - existing config
        existing_config_data = {
            'id': 'config_123',
            'user_id': 'user_123',
            **sample_backup_config,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        # Mock the get_backup_configuration call
        with patch.object(backup_service, 'get_backup_configuration') as mock_get:
            from src.models.backup import BackupConfigurationResponse
            mock_get.return_value = BackupConfigurationResponse(**existing_config_data)
            
            mock_firestore.update_document = AsyncMock()
            
            # Execute
            updated_config = {**sample_backup_config, 'retention_days': 60}
            result = await backup_service.create_or_update_backup_configuration('user_123', updated_config)
            
            # Assert
            mock_firestore.update_document.assert_called_once()
            mock_get.assert_called()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_trigger_backup_success(self, backup_service, mock_firestore, sample_trigger_request):
        """Test successful backup trigger."""
        # Setup
        mock_firestore.create_document = AsyncMock()
        mock_firestore.update_document = AsyncMock()
        
        # Mock backup configuration
        with patch.object(backup_service, 'get_backup_configuration') as mock_get_config:
            from src.models.backup import BackupConfigurationResponse
            mock_get_config.return_value = BackupConfigurationResponse(
                id='config_123',
                user_id='user_123',
                auto_backup_enabled=True,
                backup_frequency=BackupType.SCHEDULED_WEEKLY,
                destinations=[BackupDestination.LOCAL_STORAGE],
                retention_days=30,
                include_attachments=True,
                encryption_enabled=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # Mock data collection
            with patch.object(backup_service, '_collect_user_data') as mock_collect:
                mock_collect.return_value = {'user_id': 'user_123', 'data': {}}
                
                # Mock metadata generation
                with patch.object(backup_service, '_generate_backup_metadata') as mock_metadata:
                    from src.models.backup import BackupMetadata
                    mock_metadata.return_value = BackupMetadata(
                        users_count=1,
                        accounts_count=2,
                        transactions_count=10,
                        categories_count=5,
                        budgets_count=3
                    )
                    
                    # Mock backup storage
                    with patch.object(backup_service, '_store_backup') as mock_store:
                        mock_store.return_value = '/tmp/backup_test.gz'
                        
                        # Mock checksum
                        with patch.object(backup_service, '_generate_file_checksum') as mock_checksum:
                            mock_checksum.return_value = 'abc123def456'
                            
                            # Execute
                            result = await backup_service.trigger_backup('user_123', sample_trigger_request)
                            
                            # Assert
                            assert result is not None
                            assert result.user_id == 'user_123'
                            assert result.backup_type == BackupType.MANUAL
                            assert result.status == BackupStatus.COMPLETED
                            mock_firestore.create_document.assert_called_once()
                            mock_firestore.update_document.assert_called_once()
                            mock_collect.assert_called_once()
                            mock_store.assert_called_once()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_trigger_backup_failure(self, backup_service, mock_firestore, sample_trigger_request):
        """Test backup trigger failure handling."""
        # Setup
        mock_firestore.create_document = AsyncMock()
        mock_firestore.update_document = AsyncMock()
        
        # Mock backup configuration
        with patch.object(backup_service, 'get_backup_configuration') as mock_get_config:
            from src.models.backup import BackupConfigurationResponse
            mock_get_config.return_value = BackupConfigurationResponse(
                id='config_123',
                user_id='user_123',
                auto_backup_enabled=True,
                backup_frequency=BackupType.SCHEDULED_WEEKLY,
                destinations=[BackupDestination.LOCAL_STORAGE],
                retention_days=30,
                include_attachments=True,
                encryption_enabled=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # Mock data collection failure
            with patch.object(backup_service, '_collect_user_data') as mock_collect:
                mock_collect.side_effect = Exception("Data collection failed")
                
                # Execute & Assert
                with pytest.raises(AppValidationError) as exc_info:
                    await backup_service.trigger_backup('user_123', sample_trigger_request)
                
                assert "Failed to complete backup" in str(exc_info.value.message)
                mock_firestore.update_document.assert_called_once()  # Called for error update
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_backups(self, backup_service, mock_firestore):
        """Test listing user backups."""
        # Setup
        from src.models.backup import BackupRecord
        backup_records = [
            BackupRecord(
                id=f'backup_{i}',
                user_id='user_123',
                backup_type=BackupType.MANUAL,
                destinations=[BackupDestination.LOCAL_STORAGE],
                status=BackupStatus.COMPLETED,
                started_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=30),
                created_at=datetime.utcnow()
            )
            for i in range(3)
        ]
        mock_firestore.query_documents.return_value = backup_records
        
        # Execute
        result = await backup_service.list_backups('user_123')
        
        # Assert
        assert len(result) == 3
        assert all(r.user_id == 'user_123' for r in result)
        mock_firestore.query_documents.assert_called_once()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_delete_backup_success(self, backup_service, mock_firestore):
        """Test successful backup deletion."""
        # Setup
        from src.models.backup import BackupRecord
        backup_record = BackupRecord(
            id='backup_123',
            user_id='user_123',
            backup_type=BackupType.MANUAL,
            destinations=[BackupDestination.LOCAL_STORAGE],
            status=BackupStatus.COMPLETED,
            file_paths={BackupDestination.LOCAL_STORAGE.value: '/tmp/backup_test.gz'},
            started_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=30),
            created_at=datetime.utcnow()
        )
        mock_firestore.get_document.return_value = backup_record
        mock_firestore.delete_document = AsyncMock()
        
        # Mock file deletion
        with patch.object(backup_service, '_delete_backup_file') as mock_delete_file:
            mock_delete_file.return_value = None
            
            # Execute
            await backup_service.delete_backup('user_123', 'backup_123')
            
            # Assert
            mock_firestore.get_document.assert_called_once()
            mock_firestore.delete_document.assert_called_once()
            mock_delete_file.assert_called_once()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_delete_backup_not_found(self, backup_service, mock_firestore):
        """Test backup deletion when backup not found."""
        # Setup
        mock_firestore.get_document.return_value = None
        
        # Execute & Assert
        with pytest.raises(NotFoundError) as exc_info:
            await backup_service.delete_backup('user_123', 'nonexistent_backup')
        
        assert exc_info.value.resource_type == "backup"
        assert exc_info.value.resource_id == "nonexistent_backup"
        mock_firestore.get_document.assert_called_once()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_collect_user_data(self, backup_service, mock_firestore):
        """Test user data collection for backup."""
        # Setup mock data
        from src.models.auth import User
        from src.models.financial import Account, Category, Transaction, Budget, RecurringTransaction
        
        user_data = User(
            id='user_123',
            email='test@example.com',
            name='Test User',
            password_hash='hashed_password'
        )
        
        accounts_data = [
            Account(
                id='acc_1',
                user_id='user_123',
                account_name='Test Account',
                account_type='checking',
                balance=10000
            )
        ]
        
        mock_firestore.get_document.return_value = user_data
        mock_firestore.query_documents.side_effect = [
            accounts_data,  # accounts
            [],  # categories
            [],  # transactions
            [],  # budgets
            []   # recurring_transactions
        ]
        
        # Execute
        result = await backup_service._collect_user_data('user_123')
        
        # Assert
        assert result['user_id'] == 'user_123'
        assert 'backup_timestamp' in result
        assert 'data' in result
        assert 'user' in result['data']
        assert 'bank_accounts' in result['data']
        assert len(result['data']['bank_accounts']) == 1
        
        # Verify all collections were queried
        assert mock_firestore.query_documents.call_count == 5
    
    @pytest.mark.unit
    def test_generate_backup_metadata(self, backup_service):
        """Test backup metadata generation."""
        # Setup
        backup_data = {
            'user_id': 'user_123',
            'data': {
                'bank_accounts': [{'id': 'acc_1'}, {'id': 'acc_2'}],
                'categories': [{'id': 'cat_1'}],
                'transactions': [
                    {'transaction_date': '2024-01-01'},
                    {'transaction_date': '2024-01-15'},
                    {'transaction_date': '2024-02-01'}
                ],
                'budgets': []
            }
        }
        
        # Execute
        result = asyncio.run(backup_service._generate_backup_metadata(backup_data))
        
        # Assert
        assert result.users_count == 1
        assert result.accounts_count == 2
        assert result.transactions_count == 3
        assert result.categories_count == 1
        assert result.budgets_count == 0
        assert result.date_range_start == '2024-01-01'
        assert result.date_range_end == '2024-02-01'
    
    @pytest.mark.unit
    def test_get_backup_service_singleton(self):
        """Test backup service singleton pattern."""
        # Execute
        service1 = get_backup_service()
        service2 = get_backup_service()
        
        # Assert
        assert service1 is service2
        assert isinstance(service1, BackupService)


@pytest.mark.unit
class TestBackupServiceIntegration:
    """Integration tests for backup service with real-like scenarios."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_backup_workflow(self, mock_firestore):
        """Test complete backup workflow."""
        with patch('src.services.backup.get_firestore', return_value=mock_firestore):
            with patch('src.services.backup.get_settings') as mock_settings:
                mock_settings.return_value.backup_encryption_key = 'test-encryption-key-32-characters'
                
                backup_service = BackupService()
                
                # Step 1: Create configuration
                config_data = {
                    'auto_backup_enabled': True,
                    'backup_frequency': BackupType.SCHEDULED_DAILY,
                    'destinations': [BackupDestination.LOCAL_STORAGE],
                    'retention_days': 7,
                    'encryption_enabled': True
                }
                
                mock_firestore.query_documents.return_value = []  # No existing config
                mock_firestore.create_document = AsyncMock()
                
                config = await backup_service.create_or_update_backup_configuration('user_123', config_data)
                assert config.auto_backup_enabled is True
                
                # Step 2: Trigger backup
                trigger_request = BackupTriggerRequest(
                    backup_type=BackupType.MANUAL,
                    destinations=[BackupDestination.LOCAL_STORAGE],
                    include_attachments=False
                )
                
                # Mock all required methods for backup
                with patch.object(backup_service, 'get_backup_configuration') as mock_get_config:
                    mock_get_config.return_value = config
                    
                    with patch.object(backup_service, '_collect_user_data') as mock_collect:
                        mock_collect.return_value = {'user_id': 'user_123', 'data': {'transactions': []}}
                        
                        with patch.object(backup_service, '_generate_backup_metadata') as mock_metadata:
                            from src.models.backup import BackupMetadata
                            mock_metadata.return_value = BackupMetadata(
                                users_count=1,
                                accounts_count=0,
                                transactions_count=0,
                                categories_count=0,
                                budgets_count=0
                            )
                            
                            with patch.object(backup_service, '_store_backup') as mock_store:
                                mock_store.return_value = '/tmp/backup_user_123.gz'
                                
                                with patch.object(backup_service, '_generate_file_checksum') as mock_checksum:
                                    mock_checksum.return_value = 'checksum123'
                                    
                                    mock_firestore.update_document = AsyncMock()
                                    
                                    # Execute backup
                                    backup_result = await backup_service.trigger_backup('user_123', trigger_request)
                                    
                                    # Verify backup completed
                                    assert backup_result.status == BackupStatus.COMPLETED
                                    assert backup_result.user_id == 'user_123'
                                    assert backup_result.backup_type == BackupType.MANUAL
                
                # Step 3: List backups
                from src.models.backup import BackupRecord
                mock_firestore.query_documents.return_value = [
                    BackupRecord(
                        id=backup_result.id,
                        user_id='user_123',
                        backup_type=BackupType.MANUAL,
                        destinations=[BackupDestination.LOCAL_STORAGE],
                        status=BackupStatus.COMPLETED,
                        started_at=datetime.utcnow(),
                        expires_at=datetime.utcnow() + timedelta(days=7),
                        created_at=datetime.utcnow()
                    )
                ]
                
                backups = await backup_service.list_backups('user_123')
                assert len(backups) == 1
                assert backups[0].user_id == 'user_123'