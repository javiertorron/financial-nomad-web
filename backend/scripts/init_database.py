#!/usr/bin/env python3
"""
Script para inicializar la base de datos Firestore con datos de ejemplo y estructura básica.
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal

# Agregar el directorio padre al path para poder importar los módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import get_settings
from src.infrastructure import get_firestore
from src.models.auth import User, UserRole, UserStatus, Invitation
from src.models.financial import (
    Account, Category, Transaction, Budget, RecurringTransaction,
    AccountType, CategoryType, TransactionType, RecurringFrequency
)
from src.services.auth import AuthService, get_auth_service
from src.utils.exceptions import ValidationError

settings = get_settings()
firestore = get_firestore()
auth_service = get_auth_service()


async def create_demo_user():
    """Crear usuario de demostración."""
    print("🔧 Creando usuario de demostración...")
    
    try:
        # Verificar si ya existe el usuario demo
        existing_users = await firestore.query_documents(
            collection="users",
            model_class=User,
            where_clauses=[("email", "==", "demo@financial-nomad.com")]
        )
        
        if existing_users:
            print("✅ Usuario de demostración ya existe")
            return existing_users[0].id
        
        # Crear usuario demo
        demo_user = User(
            id="demo-user-id-12345",
            email="demo@financial-nomad.com",
            name="Usuario Demo",
            password_hash=auth_service.hash_password("demo123456"),
            role=UserRole.USER,
            status=UserStatus.ACTIVE,
            locale="es-ES",
            timezone="Europe/Madrid",
            currency="EUR"
        )
        
        await firestore.create_document(
            collection="users",
            document_id=demo_user.id,
            data=demo_user
        )
        
        print("✅ Usuario de demostración creado")
        print(f"   Email: demo@financial-nomad.com")
        print(f"   Password: demo123456")
        
        return demo_user.id
        
    except Exception as e:
        print(f"❌ Error creando usuario demo: {e}")
        return None


async def create_demo_accounts(user_id: str):
    """Crear cuentas de ejemplo."""
    print("🏦 Creando cuentas de ejemplo...")
    
    demo_accounts = [
        {
            "id": "account-checking-001",
            "name": "Cuenta Corriente BBVA",
            "account_type": AccountType.CHECKING,
            "balance": Decimal("2500.50"),
            "currency": "EUR",
            "description": "Cuenta principal para gastos diarios",
            "color": "#004481",
            "icon": "university"
        },
        {
            "id": "account-savings-001",
            "name": "Cuenta de Ahorros",
            "account_type": AccountType.SAVINGS,
            "balance": Decimal("15000.00"),
            "currency": "EUR",
            "description": "Ahorros para emergencias",
            "color": "#28a745",
            "icon": "piggy-bank"
        },
        {
            "id": "account-credit-001",
            "name": "Tarjeta Visa Gold",
            "account_type": AccountType.CREDIT_CARD,
            "balance": Decimal("-850.25"),
            "currency": "EUR",
            "description": "Tarjeta de crédito principal",
            "color": "#dc3545",
            "icon": "credit-card"
        },
        {
            "id": "account-cash-001",
            "name": "Efectivo",
            "account_type": AccountType.CASH,
            "balance": Decimal("125.00"),
            "currency": "EUR",
            "description": "Dinero en efectivo",
            "color": "#ffc107",
            "icon": "money-bill-wave"
        }
    ]
    
    created_accounts = []
    
    for account_data in demo_accounts:
        try:
            # Verificar si la cuenta ya existe
            existing = await firestore.query_documents(
                collection=f"accounts/{user_id}/bank_accounts",
                model_class=Account,
                where_clauses=[("name", "==", account_data["name"])]
            )
            
            if existing:
                print(f"   ⏭️  Cuenta '{account_data['name']}' ya existe")
                created_accounts.append(existing[0])
                continue
            
            account = Account(
                id=account_data["id"],
                user_id=user_id,
                name=account_data["name"],
                account_type=account_data["account_type"],
                balance=account_data["balance"],
                currency=account_data["currency"],
                description=account_data["description"],
                color=account_data["color"],
                icon=account_data["icon"]
            )
            
            await firestore.create_document(
                collection=f"accounts/{user_id}/bank_accounts",
                document_id=account.id,
                data=account
            )
            
            created_accounts.append(account)
            print(f"   ✅ Cuenta creada: {account.name}")
            
        except Exception as e:
            print(f"   ❌ Error creando cuenta {account_data['name']}: {e}")
    
    print(f"✅ {len(created_accounts)} cuentas de ejemplo creadas/verificadas")
    return created_accounts


async def create_demo_categories(user_id: str):
    """Crear categorías de ejemplo."""
    print("📂 Creando categorías de ejemplo...")
    
    demo_categories = [
        # Categorías de ingresos
        {
            "id": "cat-income-salary",
            "name": "Salario",
            "category_type": CategoryType.INCOME,
            "color": "#28a745",
            "icon": "money-check-alt",
            "monthly_budget": None,
            "description": "Ingresos por trabajo"
        },
        {
            "id": "cat-income-freelance",
            "name": "Trabajos Freelance",
            "category_type": CategoryType.INCOME,
            "color": "#17a2b8",
            "icon": "laptop-code",
            "monthly_budget": None,
            "description": "Ingresos por trabajos independientes"
        },
        
        # Categorías de gastos
        {
            "id": "cat-expense-food",
            "name": "Alimentación",
            "category_type": CategoryType.EXPENSE,
            "color": "#fd7e14",
            "icon": "utensils",
            "monthly_budget": Decimal("400.00"),
            "description": "Gastos en comida y supermercado"
        },
        {
            "id": "cat-expense-transport",
            "name": "Transporte",
            "category_type": CategoryType.EXPENSE,
            "color": "#6f42c1",
            "icon": "car",
            "monthly_budget": Decimal("150.00"),
            "description": "Gastos en transporte público y combustible"
        },
        {
            "id": "cat-expense-housing",
            "name": "Vivienda",
            "category_type": CategoryType.EXPENSE,
            "color": "#e83e8c",
            "icon": "home",
            "monthly_budget": Decimal("800.00"),
            "description": "Alquiler, hipoteca y gastos del hogar"
        },
        {
            "id": "cat-expense-utilities",
            "name": "Servicios",
            "category_type": CategoryType.EXPENSE,
            "color": "#20c997",
            "icon": "bolt",
            "monthly_budget": Decimal("200.00"),
            "description": "Luz, agua, gas, internet, teléfono"
        },
        {
            "id": "cat-expense-entertainment",
            "name": "Entretenimiento",
            "category_type": CategoryType.EXPENSE,
            "color": "#6610f2",
            "icon": "gamepad",
            "monthly_budget": Decimal("100.00"),
            "description": "Ocio, cine, restaurantes"
        },
        {
            "id": "cat-expense-health",
            "name": "Salud",
            "category_type": CategoryType.EXPENSE,
            "color": "#dc3545",
            "icon": "heartbeat",
            "monthly_budget": Decimal("80.00"),
            "description": "Gastos médicos y farmacia"
        },
        
        # Categoría de transferencias
        {
            "id": "cat-transfer",
            "name": "Transferencias",
            "category_type": CategoryType.TRANSFER,
            "color": "#6c757d",
            "icon": "exchange-alt",
            "monthly_budget": None,
            "description": "Transferencias entre cuentas"
        }
    ]
    
    created_categories = []
    
    for cat_data in demo_categories:
        try:
            # Verificar si la categoría ya existe
            existing = await firestore.query_documents(
                collection=f"categories/{user_id}/user_categories",
                model_class=Category,
                where_clauses=[("name", "==", cat_data["name"])]
            )
            
            if existing:
                print(f"   ⏭️  Categoría '{cat_data['name']}' ya existe")
                created_categories.append(existing[0])
                continue
            
            category = Category(
                id=cat_data["id"],
                user_id=user_id,
                name=cat_data["name"],
                category_type=cat_data["category_type"],
                color=cat_data["color"],
                icon=cat_data["icon"],
                monthly_budget=cat_data["monthly_budget"],
                description=cat_data["description"],
                is_system=False
            )
            
            await firestore.create_document(
                collection=f"categories/{user_id}/user_categories",
                document_id=category.id,
                data=category
            )
            
            created_categories.append(category)
            print(f"   ✅ Categoría creada: {category.name}")
            
        except Exception as e:
            print(f"   ❌ Error creando categoría {cat_data['name']}: {e}")
    
    print(f"✅ {len(created_categories)} categorías de ejemplo creadas/verificadas")
    return created_categories


async def create_demo_transactions(user_id: str, accounts: list, categories: list):
    """Crear transacciones de ejemplo."""
    print("💳 Creando transacciones de ejemplo...")
    
    # Crear diccionarios de lookup
    account_lookup = {acc.name: acc for acc in accounts}
    category_lookup = {cat.name: cat for cat in categories}
    
    # Transacciones de los últimos 30 días
    base_date = datetime.now()
    
    demo_transactions = [
        # Ingresos
        {
            "id": "txn-001",
            "account_name": "Cuenta Corriente BBVA",
            "category_name": "Salario",
            "amount": Decimal("2800.00"),
            "description": "Salario mensual enero",
            "days_ago": 25,
            "reference_number": "SAL202501",
            "tags": ["salary", "monthly"]
        },
        {
            "id": "txn-002",
            "account_name": "Cuenta Corriente BBVA",
            "category_name": "Trabajos Freelance",
            "amount": Decimal("450.00"),
            "description": "Proyecto web para cliente",
            "days_ago": 20,
            "reference_number": "FRL001",
            "tags": ["freelance", "web"]
        },
        
        # Gastos de alimentación
        {
            "id": "txn-003",
            "account_name": "Cuenta Corriente BBVA",
            "category_name": "Alimentación",
            "amount": Decimal("-85.50"),
            "description": "Supermercado Carrefour",
            "days_ago": 2,
            "tags": ["grocery", "food"]
        },
        {
            "id": "txn-004",
            "account_name": "Tarjeta Visa Gold",
            "category_name": "Alimentación",
            "amount": Decimal("-32.80"),
            "description": "Restaurante La Tasca",
            "days_ago": 5,
            "tags": ["restaurant", "dinner"]
        },
        {
            "id": "txn-005",
            "account_name": "Cuenta Corriente BBVA",
            "category_name": "Alimentación",
            "amount": Decimal("-67.25"),
            "description": "Mercadona compra semanal",
            "days_ago": 7,
            "tags": ["grocery", "weekly"]
        },
        
        # Gastos de transporte
        {
            "id": "txn-006",
            "account_name": "Cuenta Corriente BBVA",
            "category_name": "Transporte",
            "amount": Decimal("-50.00"),
            "description": "Abono mensual metro",
            "days_ago": 28,
            "reference_number": "METRO202501",
            "tags": ["transport", "metro", "monthly"]
        },
        {
            "id": "txn-007",
            "account_name": "Tarjeta Visa Gold",
            "category_name": "Transporte",
            "amount": Decimal("-45.60"),
            "description": "Gasolina BP",
            "days_ago": 10,
            "tags": ["fuel", "car"]
        },
        
        # Gastos de vivienda
        {
            "id": "txn-008",
            "account_name": "Cuenta Corriente BBVA",
            "category_name": "Vivienda",
            "amount": Decimal("-750.00"),
            "description": "Alquiler enero",
            "days_ago": 30,
            "reference_number": "RENT202501",
            "tags": ["rent", "monthly"]
        },
        
        # Servicios
        {
            "id": "txn-009",
            "account_name": "Cuenta Corriente BBVA",
            "category_name": "Servicios",
            "amount": Decimal("-45.80"),
            "description": "Factura de luz - Iberdrola",
            "days_ago": 15,
            "reference_number": "IBE202501",
            "tags": ["electricity", "utilities"]
        },
        {
            "id": "txn-010",
            "account_name": "Cuenta Corriente BBVA",
            "category_name": "Servicios",
            "amount": Decimal("-29.99"),
            "description": "Internet fibra Movistar",
            "days_ago": 22,
            "reference_number": "MOV202501",
            "tags": ["internet", "monthly"]
        },
        
        # Entretenimiento
        {
            "id": "txn-011",
            "account_name": "Tarjeta Visa Gold",
            "category_name": "Entretenimiento",
            "amount": Decimal("-12.90"),
            "description": "Netflix suscripción",
            "days_ago": 18,
            "tags": ["streaming", "subscription"]
        },
        {
            "id": "txn-012",
            "account_name": "Efectivo",
            "category_name": "Entretenimiento",
            "amount": Decimal("-25.00"),
            "description": "Cine con amigos",
            "days_ago": 8,
            "tags": ["movie", "friends"]
        },
        
        # Salud
        {
            "id": "txn-013",
            "account_name": "Tarjeta Visa Gold",
            "category_name": "Salud",
            "amount": Decimal("-15.60"),
            "description": "Farmacia - medicamentos",
            "days_ago": 12,
            "tags": ["pharmacy", "medicine"]
        },
        
        # Transferencias
        {
            "id": "txn-014",
            "account_name": "Cuenta Corriente BBVA",
            "category_name": "Transferencias",
            "amount": Decimal("-500.00"),
            "description": "Transferencia a ahorros",
            "destination_account_name": "Cuenta de Ahorros",
            "days_ago": 26,
            "tags": ["transfer", "savings"]
        },
        {
            "id": "txn-015",
            "account_name": "Cuenta de Ahorros",
            "category_name": "Transferencias",
            "amount": Decimal("500.00"),
            "description": "Recibido desde cuenta corriente",
            "days_ago": 26,
            "tags": ["transfer", "received"]
        }
    ]
    
    created_transactions = []
    
    for txn_data in demo_transactions:
        try:
            # Verificar si la transacción ya existe
            existing = await firestore.query_documents(
                collection=f"transactions/{user_id}/user_transactions",
                model_class=Transaction,
                where_clauses=[("description", "==", txn_data["description"])]
            )
            
            if existing:
                print(f"   ⏭️  Transacción '{txn_data['description']}' ya existe")
                continue
            
            # Obtener cuenta y categoría
            account = account_lookup.get(txn_data["account_name"])
            category = category_lookup.get(txn_data["category_name"])
            destination_account = None
            
            if txn_data.get("destination_account_name"):
                destination_account = account_lookup.get(txn_data["destination_account_name"])
            
            if not account:
                print(f"   ❌ Cuenta no encontrada: {txn_data['account_name']}")
                continue
                
            if not category:
                print(f"   ❌ Categoría no encontrada: {txn_data['category_name']}")
                continue
            
            # Calcular fecha de transacción
            transaction_date = base_date - timedelta(days=txn_data["days_ago"])
            
            # Determinar tipo de transacción automáticamente
            if destination_account:
                transaction_type = TransactionType.TRANSFER
            elif txn_data["amount"] > 0:
                transaction_type = TransactionType.INCOME
            else:
                transaction_type = TransactionType.EXPENSE
            
            transaction = Transaction(
                id=txn_data["id"],
                user_id=user_id,
                account_id=account.id,
                category_id=category.id,
                amount=txn_data["amount"],
                description=txn_data["description"],
                transaction_type=transaction_type,
                transaction_date=transaction_date,
                to_account_id=destination_account.id if destination_account else None,
                reference=txn_data.get("reference_number"),
                tags=txn_data.get("tags", [])
            )
            
            await firestore.create_document(
                collection=f"transactions/{user_id}/user_transactions",
                document_id=transaction.id,
                data=transaction
            )
            
            created_transactions.append(transaction)
            print(f"   ✅ Transacción creada: {transaction.description}")
            
        except Exception as e:
            print(f"   ❌ Error creando transacción {txn_data['description']}: {e}")
    
    print(f"✅ {len(created_transactions)} transacciones de ejemplo creadas")
    return created_transactions


async def create_demo_budgets(user_id: str, categories: list):
    """Crear presupuestos de ejemplo."""
    print("💰 Creando presupuestos de ejemplo...")
    
    # Crear diccionario de lookup de categorías
    category_lookup = {cat.name: cat for cat in categories if cat.category_type == CategoryType.EXPENSE}
    
    # Calcular fechas para presupuestos (período actual)
    now = datetime.now()
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if now.month == 12:
        period_end = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        period_end = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
    
    demo_budgets = [
        {
            "id": "budget-food-jan",
            "name": "Presupuesto Alimentación Enero",
            "category_name": "Alimentación",
            "amount": Decimal("400.00"),
            "alert_threshold": Decimal("80.00")
        },
        {
            "id": "budget-transport-jan",
            "name": "Presupuesto Transporte Enero",
            "category_name": "Transporte",
            "amount": Decimal("150.00"),
            "alert_threshold": Decimal("90.00")
        },
        {
            "id": "budget-entertainment-jan",
            "name": "Presupuesto Entretenimiento Enero",
            "category_name": "Entretenimiento",
            "amount": Decimal("100.00"),
            "alert_threshold": Decimal("75.00")
        }
    ]
    
    created_budgets = []
    
    for budget_data in demo_budgets:
        try:
            # Verificar si el presupuesto ya existe
            existing = await firestore.query_documents(
                collection=f"budgets/{user_id}/user_budgets",
                model_class=Budget,
                where_clauses=[("name", "==", budget_data["name"])]
            )
            
            if existing:
                print(f"   ⏭️  Presupuesto '{budget_data['name']}' ya existe")
                created_budgets.append(existing[0])
                continue
            
            category = category_lookup.get(budget_data["category_name"])
            if not category:
                print(f"   ❌ Categoría no encontrada: {budget_data['category_name']}")
                continue
            
            budget = Budget(
                id=budget_data["id"],
                user_id=user_id,
                name=budget_data["name"],
                category_id=category.id,
                amount=budget_data["amount"],
                period_start=period_start,
                period_end=period_end,
                alert_threshold=budget_data["alert_threshold"]
            )
            
            await firestore.create_document(
                collection=f"budgets/{user_id}/user_budgets",
                document_id=budget.id,
                data=budget
            )
            
            created_budgets.append(budget)
            print(f"   ✅ Presupuesto creado: {budget.name}")
            
        except Exception as e:
            print(f"   ❌ Error creando presupuesto {budget_data['name']}: {e}")
    
    print(f"✅ {len(created_budgets)} presupuestos de ejemplo creados/verificados")
    return created_budgets


async def create_demo_recurring_transactions(user_id: str, accounts: list, categories: list):
    """Crear transacciones recurrentes de ejemplo."""
    print("🔄 Creando transacciones recurrentes de ejemplo...")
    
    # Crear diccionarios de lookup
    account_lookup = {acc.name: acc for acc in accounts}
    category_lookup = {cat.name: cat for cat in categories}
    
    # Fechas base
    now = datetime.now()
    next_month = now.replace(day=1) + timedelta(days=32)
    next_month = next_month.replace(day=1)
    
    demo_recurring = [
        {
            "id": "recurring-salary",
            "name": "Salario Mensual",
            "amount": Decimal("2800.00"),
            "description": "Salario mensual por trabajo",
            "transaction_type": TransactionType.INCOME,
            "account_name": "Cuenta Corriente BBVA",
            "category_name": "Salario",
            "frequency": RecurringFrequency.MONTHLY,
            "start_date": now.replace(day=1),
            "tags": ["salary", "monthly", "auto"]
        },
        {
            "id": "recurring-rent",
            "name": "Alquiler",
            "amount": Decimal("-750.00"),
            "description": "Pago mensual de alquiler",
            "transaction_type": TransactionType.EXPENSE,
            "account_name": "Cuenta Corriente BBVA",
            "category_name": "Vivienda",
            "frequency": RecurringFrequency.MONTHLY,
            "start_date": now.replace(day=1),
            "tags": ["rent", "monthly", "auto"]
        },
        {
            "id": "recurring-internet",
            "name": "Internet Fibra",
            "amount": Decimal("-29.99"),
            "description": "Cuota mensual de internet",
            "transaction_type": TransactionType.EXPENSE,
            "account_name": "Cuenta Corriente BBVA",
            "category_name": "Servicios",
            "frequency": RecurringFrequency.MONTHLY,
            "start_date": now.replace(day=22),
            "tags": ["internet", "utilities", "monthly"]
        },
        {
            "id": "recurring-metro",
            "name": "Abono de Transporte",
            "amount": Decimal("-50.00"),
            "description": "Abono mensual de metro",
            "transaction_type": TransactionType.EXPENSE,
            "account_name": "Cuenta Corriente BBVA",
            "category_name": "Transporte",
            "frequency": RecurringFrequency.MONTHLY,
            "start_date": now.replace(day=28),
            "tags": ["transport", "metro", "monthly"]
        },
        {
            "id": "recurring-savings",
            "name": "Transferencia a Ahorros",
            "amount": Decimal("-500.00"),
            "description": "Ahorro mensual automático",
            "transaction_type": TransactionType.TRANSFER,
            "account_name": "Cuenta Corriente BBVA",
            "destination_account_name": "Cuenta de Ahorros",
            "category_name": "Transferencias",
            "frequency": RecurringFrequency.MONTHLY,
            "start_date": now.replace(day=26),
            "tags": ["savings", "transfer", "monthly"]
        }
    ]
    
    created_recurring = []
    
    for recurring_data in demo_recurring:
        try:
            # Verificar si ya existe
            existing = await firestore.query_documents(
                collection=f"recurring_transactions/{user_id}/user_recurring_transactions",
                model_class=RecurringTransaction,
                where_clauses=[("name", "==", recurring_data["name"])]
            )
            
            if existing:
                print(f"   ⏭️  Transacción recurrente '{recurring_data['name']}' ya existe")
                created_recurring.append(existing[0])
                continue
            
            # Obtener cuenta y categoría
            account = account_lookup.get(recurring_data["account_name"])
            category = category_lookup.get(recurring_data["category_name"])
            to_account = None
            
            if recurring_data.get("destination_account_name"):
                to_account = account_lookup.get(recurring_data["destination_account_name"])
            
            if not account:
                print(f"   ❌ Cuenta no encontrada: {recurring_data['account_name']}")
                continue
                
            if not category:
                print(f"   ❌ Categoría no encontrada: {recurring_data['category_name']}")
                continue
            
            # Calcular próxima ejecución
            next_execution = recurring_data["start_date"]
            if next_execution < now:
                next_execution = next_month.replace(day=recurring_data["start_date"].day)
            
            recurring = RecurringTransaction(
                id=recurring_data["id"],
                user_id=user_id,
                name=recurring_data["name"],
                amount=recurring_data["amount"],
                description=recurring_data["description"],
                transaction_type=recurring_data["transaction_type"],
                account_id=account.id,
                to_account_id=to_account.id if to_account else None,
                category_id=category.id,
                frequency=recurring_data["frequency"],
                start_date=recurring_data["start_date"],
                next_execution=next_execution,
                tags=recurring_data.get("tags", [])
            )
            
            await firestore.create_document(
                collection=f"recurring_transactions/{user_id}/user_recurring_transactions",
                document_id=recurring.id,
                data=recurring
            )
            
            created_recurring.append(recurring)
            print(f"   ✅ Transacción recurrente creada: {recurring.name}")
            
        except Exception as e:
            print(f"   ❌ Error creando transacción recurrente {recurring_data['name']}: {e}")
    
    print(f"✅ {len(created_recurring)} transacciones recurrentes de ejemplo creadas/verificadas")
    return created_recurring


async def create_admin_user():
    """Crear usuario administrador si no existe."""
    print("👑 Verificando usuario administrador...")
    
    try:
        # Verificar si ya existe un admin
        admin_users = await firestore.query_documents(
            collection="users",
            model_class=User,
            where_clauses=[("role", "==", UserRole.ADMIN)]
        )
        
        if admin_users:
            print("✅ Usuario administrador ya existe")
            return
        
        # Crear admin
        admin_user = User(
            id="admin-user-master",
            email="admin@financial-nomad.com",
            name="Administrador",
            password_hash=auth_service.hash_password("admin123456"),
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
            locale="es-ES",
            timezone="Europe/Madrid",
            currency="EUR"
        )
        
        await firestore.create_document(
            collection="users",
            document_id=admin_user.id,
            data=admin_user
        )
        
        print("✅ Usuario administrador creado")
        print(f"   Email: admin@financial-nomad.com")
        print(f"   Password: admin123456")
        
    except Exception as e:
        print(f"❌ Error creando usuario admin: {e}")


async def main():
    """Función principal de inicialización."""
    print("🚀 Iniciando configuración de base de datos Firestore...")
    print("=" * 60)
    
    try:
        # 1. Crear usuario administrador
        await create_admin_user()
        print()
        
        # 2. Crear usuario de demostración
        demo_user_id = await create_demo_user()
        if not demo_user_id:
            print("❌ No se pudo crear el usuario demo. Abortando...")
            return
        print()
        
        # 3. Crear cuentas de ejemplo
        demo_accounts = await create_demo_accounts(demo_user_id)
        print()
        
        # 4. Crear categorías de ejemplo
        demo_categories = await create_demo_categories(demo_user_id)
        print()
        
        # 5. Crear transacciones de ejemplo
        demo_transactions = await create_demo_transactions(demo_user_id, demo_accounts, demo_categories)
        print()
        
        # 6. Crear presupuestos de ejemplo (Fase 3)
        demo_budgets = await create_demo_budgets(demo_user_id, demo_categories)
        print()
        
        # 7. Crear transacciones recurrentes de ejemplo (Fase 3)
        demo_recurring = await create_demo_recurring_transactions(demo_user_id, demo_accounts, demo_categories)
        print()
        
        print("=" * 60)
        print("🎉 ¡Inicialización de base de datos completada!")
        print()
        print("📊 Resumen:")
        print(f"   • {len(demo_accounts)} cuentas creadas")
        print(f"   • {len(demo_categories)} categorías creadas") 
        print(f"   • {len(demo_transactions)} transacciones creadas")
        print(f"   • {len(demo_budgets)} presupuestos creados")
        print(f"   • {len(demo_recurring)} transacciones recurrentes creadas")
        print()
        print("👤 Usuarios de prueba:")
        print("   • Admin: admin@financial-nomad.com / admin123456")
        print("   • Demo:  demo@financial-nomad.com / demo123456")
        print()
        print("🌐 Puedes probar la API en: http://localhost:8080/docs")
        
    except Exception as e:
        print(f"❌ Error durante la inicialización: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())