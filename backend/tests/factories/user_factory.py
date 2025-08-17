"""
Factory for User model testing.
"""

import factory
from datetime import datetime, timedelta
from faker import Faker

fake = Faker()


class UserPreferencesFactory(factory.DictFactory):
    """Factory for user preferences."""
    
    language = factory.Iterator(["es", "en"])
    currency = factory.Iterator(["EUR", "USD"])
    timezone = "Europe/Madrid"


class SavingsConfigFactory(factory.DictFactory):
    """Factory for savings configuration."""
    
    minimum_fixed_amount = factory.LazyFunction(lambda: fake.random_int(min=10000, max=100000))
    target_percentage = factory.LazyFunction(lambda: fake.random_int(min=10, max=50))


class UserFactory(factory.DictFactory):
    """Factory for User model."""
    
    uid = factory.Sequence(lambda n: f"user_{n:04d}")
    email = factory.LazyAttribute(lambda obj: f"{obj.uid}@example.com")
    display_name = factory.Faker("name")
    role = "user"
    preferences = factory.SubFactory(UserPreferencesFactory)
    savings_config = factory.SubFactory(SavingsConfigFactory)
    is_active = True
    created_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())
    updated_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())
    last_login = None


class AdminUserFactory(UserFactory):
    """Factory for admin user."""
    
    uid = factory.Sequence(lambda n: f"admin_{n:04d}")
    role = "admin"
    display_name = "Admin User"


class InvitationFactory(factory.DictFactory):
    """Factory for Invitation model."""
    
    code = factory.Sequence(lambda n: f"INV_{n:08X}")
    email = factory.Faker("email")
    issued_by = factory.LazyFunction(lambda: f"admin_{fake.random_int(min=1, max=999):04d}")
    status = "pending"
    expires_at = factory.LazyFunction(
        lambda: (datetime.utcnow() + timedelta(days=7)).isoformat()
    )
    consumed_by = None
    consumed_at = None
    created_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())