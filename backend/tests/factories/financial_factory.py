"""
Factory for Financial model testing.
"""

import factory
from datetime import date, datetime, timedelta
from faker import Faker

fake = Faker()


class AccountFactory(factory.DictFactory):
    """Factory for Account model."""
    
    id = factory.Sequence(lambda n: f"acc_{n:06d}")
    name = factory.Faker("company")
    type = factory.Iterator(["bank", "cash", "card"])
    bank_name = factory.LazyAttribute(
        lambda obj: fake.company() if obj.type == "bank" else None
    )
    last_four_digits = factory.LazyAttribute(
        lambda obj: f"{fake.random_int(min=1000, max=9999)}" if obj.type in ["bank", "card"] else None
    )
    currency = "EUR"
    balance = factory.LazyFunction(lambda: fake.random_int(min=0, max=1000000))
    is_default = False
    is_active = True
    created_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())
    updated_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())


class CategoryFactory(factory.DictFactory):
    """Factory for Category model."""
    
    id = factory.Sequence(lambda n: f"cat_{n:06d}")
    name = factory.Faker("word")
    type = factory.Iterator(["income", "expense"])
    parent_id = None
    icon = factory.Iterator(["folder", "shopping_cart", "restaurant", "work", "home"])
    color = factory.LazyFunction(lambda: fake.hex_color())
    is_active = True
    transaction_count = 0
    created_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())


class TransactionFactory(factory.DictFactory):
    """Factory for Transaction model."""
    
    id = factory.Sequence(lambda n: f"txn_{n:06d}")
    type = factory.Iterator(["income", "expense"])
    amount = factory.LazyFunction(lambda: fake.random_int(min=100, max=100000))
    currency = "EUR"
    description = factory.Faker("sentence", nb_words=3)
    date = factory.LazyFunction(
        lambda: (date.today() - timedelta(days=fake.random_int(min=0, max=30))).isoformat()
    )
    category_id = factory.Sequence(lambda n: f"cat_{n:06d}")
    account_id = factory.Sequence(lambda n: f"acc_{n:06d}")
    tags = factory.LazyFunction(
        lambda: [fake.word() for _ in range(fake.random_int(min=0, max=3))]
    )
    external_ref = None
    attachments = []
    created_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())
    updated_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())


class ExpenseTransactionFactory(TransactionFactory):
    """Factory for expense transactions."""
    
    type = "expense"
    amount = factory.LazyFunction(lambda: fake.random_int(min=500, max=20000))


class IncomeTransactionFactory(TransactionFactory):
    """Factory for income transactions."""
    
    type = "income"
    amount = factory.LazyFunction(lambda: fake.random_int(min=50000, max=500000))


class AsanaTransactionFactory(TransactionFactory):
    """Factory for transactions from Asana."""
    
    external_ref = factory.Sequence(lambda n: f"asana_task_{n:06d}")
    description = factory.LazyAttribute(lambda obj: f"Asana: {fake.sentence(nb_words=3)}")


class BudgetFactory(factory.DictFactory):
    """Factory for Budget model."""
    
    id = factory.Sequence(lambda n: f"bud_{n:06d}")
    category_id = factory.Sequence(lambda n: f"cat_{n:06d}")
    period = factory.LazyFunction(lambda: date.today().strftime("%Y-%m"))
    period_type = "monthly"
    limit_amount = factory.LazyFunction(lambda: fake.random_int(min=10000, max=100000))
    spent_amount = factory.LazyFunction(lambda: fake.random_int(min=0, max=50000))
    is_active = True
    created_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())


class FixedItemFactory(factory.DictFactory):
    """Factory for Fixed Item model."""
    
    id = factory.Sequence(lambda n: f"fix_{n:06d}")
    name = factory.Faker("sentence", nb_words=2)
    type = factory.Iterator(["income", "expense"])
    amount = factory.LazyFunction(lambda: fake.random_int(min=10000, max=200000))
    currency = "EUR"
    frequency = factory.Iterator(["weekly", "monthly", "yearly"])
    start_date = factory.LazyFunction(lambda: date.today().isoformat())
    end_date = None
    next_occurrence = factory.LazyFunction(
        lambda: (date.today() + timedelta(days=30)).isoformat()
    )
    category_id = factory.Sequence(lambda n: f"cat_{n:06d}")
    account_id = factory.Sequence(lambda n: f"acc_{n:06d}")
    is_active = True
    created_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())


class SavingsProjectFactory(factory.DictFactory):
    """Factory for Savings Project model."""
    
    id = factory.Sequence(lambda n: f"sav_{n:06d}")
    name = factory.Faker("sentence", nb_words=2)
    description = factory.Faker("text", max_nb_chars=200)
    target_amount = factory.LazyFunction(lambda: fake.random_int(min=100000, max=1000000))
    current_amount = factory.LazyFunction(lambda: fake.random_int(min=0, max=50000))
    priority = factory.Iterator([1, 2, 3])
    target_date = factory.LazyFunction(
        lambda: (date.today() + timedelta(days=365)).isoformat()
    )
    status = "active"
    created_at = factory.LazyFunction(lambda: datetime.utcnow().isoformat())