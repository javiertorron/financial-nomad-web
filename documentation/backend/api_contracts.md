# Contratos API — Backend Financial Nomad

> **Ambito**: definicion completa de contratos API REST  
> **Enfoque**: OpenAPI 3.0, validacion estricta, seguridad por defecto  
> **Base URL**: `https://api.financial-nomad.com/api/v1`

---

## 1. Consideraciones generales

### 1.1 Estandares
- **Protocolo**: HTTPS obligatorio
- **Formato**: JSON (Content-Type: application/json)
- **Encoding**: UTF-8
- **Versionado**: `/api/v1` en path
- **Documentacion**: OpenAPI 3.0 (Swagger UI)

### 1.2 Autenticacion
- **Metodo**: Google ID Token + Session Cookie
- **Headers**: 
  - `Authorization: Bearer <google-id-token>` (inicial)
  - `Cookie: session=<session-token>` (posteriores)
- **Expiracion**: 24 horas (renovable)

### 1.3 Respuestas estandar
```json
// Exito (200, 201)
{
  "data": { ... },
  "meta": {
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_abc123"
  }
}

// Error (4xx, 5xx)
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": ["field 'amount' is required"]
  },
  "meta": {
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_abc123"
  }
}

// Paginacion
{
  "data": [...],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_count": 150,
    "has_next": true,
    "has_previous": false
  }
}
```

### 1.4 Codigos de estado
- `200` - OK (GET, PUT)
- `201` - Created (POST)
- `204` - No Content (DELETE)
- `400` - Bad Request (validacion)
- `401` - Unauthorized (auth requerida)
- `403` - Forbidden (sin permisos)
- `404` - Not Found
- `422` - Unprocessable Entity (logica de negocio)
- `429` - Too Many Requests (rate limit)
- `500` - Internal Server Error

---

## 2. Autenticacion y autorizacion

### 2.1 Iniciar sesion
```http
POST /auth/login
Content-Type: application/json

{
  "google_id_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6...",
  "invitation_code": "INV_ABC123" // Opcional, solo en primer login
}
```

**Respuesta 200:**
```json
{
  "data": {
    "user": {
      "uid": "user_123",
      "email": "user@example.com",
      "display_name": "Usuario Ejemplo",
      "role": "user",
      "is_first_login": false,
      "preferences": {
        "language": "es",
        "currency": "EUR",
        "timezone": "Europe/Madrid"
      }
    },
    "session": {
      "expires_at": "2024-01-16T10:30:00Z"
    }
  }
}
```

**Errores:**
- `401` - Token de Google invalido
- `403` - Email sin invitacion valida
- `422` - Invitacion expirada/consumida

### 2.2 Renovar sesion
```http
POST /auth/refresh
```

**Respuesta 200:**
```json
{
  "data": {
    "session": {
      "expires_at": "2024-01-16T10:30:00Z"
    }
  }
}
```

### 2.3 Cerrar sesion
```http
POST /auth/logout
```

**Respuesta 204:** Sin contenido

### 2.4 Perfil de usuario
```http
GET /auth/profile
```

**Respuesta 200:**
```json
{
  "data": {
    "uid": "user_123",
    "email": "user@example.com",
    "display_name": "Usuario Ejemplo",
    "role": "user",
    "preferences": {
      "language": "es",
      "currency": "EUR",
      "timezone": "Europe/Madrid"
    },
    "savings_config": {
      "minimum_fixed_amount": 50000, // centimos
      "target_percentage": 20 // %
    },
    "created_at": "2024-01-01T00:00:00Z",
    "last_login": "2024-01-15T09:00:00Z"
  }
}
```

### 2.5 Actualizar perfil
```http
PUT /auth/profile
Content-Type: application/json

{
  "display_name": "Nuevo Nombre",
  "preferences": {
    "language": "en",
    "currency": "USD",
    "timezone": "America/New_York"
  },
  "savings_config": {
    "minimum_fixed_amount": 75000,
    "target_percentage": 25
  }
}
```

---

## 3. Gestion de invitaciones (Solo Admin)

### 3.1 Crear invitacion
```http
POST /admin/invitations
Content-Type: application/json

{
  "email": "nuevo@example.com",
  "expires_in_days": 7
}
```

**Respuesta 201:**
```json
{
  "data": {
    "code": "INV_ABC123",
    "email": "nuevo@example.com",
    "issued_by": "admin_456",
    "expires_at": "2024-01-22T10:30:00Z",
    "status": "pending",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

### 3.2 Listar invitaciones
```http
GET /admin/invitations?status=pending&page=1&page_size=20
```

**Respuesta 200:**
```json
{
  "data": [
    {
      "code": "INV_ABC123",
      "email": "nuevo@example.com",
      "issued_by": "admin_456",
      "expires_at": "2024-01-22T10:30:00Z",
      "status": "pending",
      "consumed_by": null,
      "consumed_at": null,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_count": 5,
    "has_next": false
  }
}
```

### 3.3 Revocar invitacion
```http
DELETE /admin/invitations/{code}
```

**Respuesta 204:** Sin contenido

---

## 4. Gestion de cuentas

### 4.1 Listar cuentas
```http
GET /accounts?type=bank&active=true
```

**Respuesta 200:**
```json
{
  "data": [
    {
      "id": "acc_123",
      "name": "Cuenta Corriente Principal",
      "type": "bank", // bank, cash, card
      "bank_name": "Banco Ejemplo",
      "last_four_digits": "1234",
      "currency": "EUR",
      "balance": 150000, // centimos
      "is_default": true,
      "is_active": true,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

### 4.2 Crear cuenta
```http
POST /accounts
Content-Type: application/json

{
  "name": "Nueva Cuenta",
  "type": "bank",
  "bank_name": "Banco Nuevo",
  "last_four_digits": "5678",
  "currency": "EUR",
  "initial_balance": 100000,
  "is_default": false
}
```

**Respuesta 201:**
```json
{
  "data": {
    "id": "acc_456",
    "name": "Nueva Cuenta",
    "type": "bank",
    "bank_name": "Banco Nuevo",
    "last_four_digits": "5678",
    "currency": "EUR",
    "balance": 100000,
    "is_default": false,
    "is_active": true,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
}
```

### 4.3 Obtener cuenta
```http
GET /accounts/{account_id}
```

### 4.4 Actualizar cuenta
```http
PUT /accounts/{account_id}
Content-Type: application/json

{
  "name": "Cuenta Actualizada",
  "is_default": true,
  "is_active": false
}
```

### 4.5 Eliminar cuenta
```http
DELETE /accounts/{account_id}
```

**Respuesta 204:** Sin contenido

**Errores:**
- `422` - Cuenta tiene transacciones asociadas

---

## 5. Gestion de categorias

### 5.1 Listar categorias
```http
GET /categories?type=expense&parent_id=cat_123
```

**Respuesta 200:**
```json
{
  "data": [
    {
      "id": "cat_123",
      "name": "Alimentacion",
      "type": "expense", // income, expense
      "parent_id": null,
      "icon": "restaurant",
      "color": "#FF5722",
      "is_active": true,
      "transaction_count": 45,
      "created_at": "2024-01-01T00:00:00Z"
    },
    {
      "id": "cat_456",
      "name": "Supermercado",
      "type": "expense",
      "parent_id": "cat_123",
      "icon": "shopping_cart",
      "color": "#FF5722",
      "is_active": true,
      "transaction_count": 23,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

### 5.2 Crear categoria
```http
POST /categories
Content-Type: application/json

{
  "name": "Nueva Categoria",
  "type": "expense",
  "parent_id": "cat_123", // Opcional
  "icon": "shopping_bag",
  "color": "#4CAF50"
}
```

### 5.3 Actualizar categoria
```http
PUT /categories/{category_id}
Content-Type: application/json

{
  "name": "Categoria Actualizada",
  "icon": "new_icon",
  "color": "#2196F3",
  "is_active": false
}
```

### 5.4 Eliminar categoria
```http
DELETE /categories/{category_id}
```

**Errores:**
- `422` - Categoria tiene transacciones asociadas
- `422` - Categoria tiene subcategorias

---

## 6. Gestion de transacciones

### 6.1 Listar transacciones
```http
GET /transactions?type=expense&category_id=cat_123&account_id=acc_123&date_from=2024-01-01&date_to=2024-01-31&page=1&page_size=50&sort=-date
```

**Respuesta 200:**
```json
{
  "data": [
    {
      "id": "txn_123",
      "type": "expense",
      "amount": 2550, // centimos
      "currency": "EUR",
      "description": "Compra supermercado",
      "date": "2024-01-15",
      "category": {
        "id": "cat_456",
        "name": "Supermercado",
        "type": "expense"
      },
      "account": {
        "id": "acc_123",
        "name": "Cuenta Corriente"
      },
      "tags": ["groceries", "weekly"],
      "external_ref": "asana_task_789", // Referencia Asana opcional
      "attachments": [],
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total_count": 150,
    "has_next": true
  }
}
```

### 6.2 Crear transaccion
```http
POST /transactions
Content-Type: application/json

{
  "type": "expense",
  "amount": 2550,
  "currency": "EUR",
  "description": "Nueva compra",
  "date": "2024-01-15",
  "category_id": "cat_456",
  "account_id": "acc_123",
  "tags": ["shopping"],
  "external_ref": "asana_task_790"
}
```

**Respuesta 201:**
```json
{
  "data": {
    "id": "txn_456",
    "type": "expense",
    "amount": 2550,
    "currency": "EUR",
    "description": "Nueva compra",
    "date": "2024-01-15",
    "category": {
      "id": "cat_456",
      "name": "Supermercado",
      "type": "expense"
    },
    "account": {
      "id": "acc_123",
      "name": "Cuenta Corriente"
    },
    "tags": ["shopping"],
    "external_ref": "asana_task_790",
    "attachments": [],
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
}
```

### 6.3 Importar transacciones YAML
```http
POST /transactions/import
Content-Type: application/json

{
  "yaml_content": "gastos:\n  - descripcion: Supermercado\n    monto: 25.50\n    fecha: 2024-01-15\n    categoria: Alimentacion\n    metodo: Tarjeta",
  "preview_mode": true // Solo validar, no crear
}
```

**Respuesta 200 (preview):**
```json
{
  "data": {
    "preview": {
      "total_items": 5,
      "valid_items": 4,
      "invalid_items": 1,
      "transactions": [
        {
          "description": "Supermercado",
          "amount": 2550,
          "date": "2024-01-15",
          "category_id": "cat_456",
          "account_id": "acc_123",
          "type": "expense",
          "status": "valid"
        }
      ],
      "errors": [
        {
          "line": 3,
          "error": "Categoria 'Inexistente' no encontrada"
        }
      ]
    }
  }
}
```

**Respuesta 201 (import):**
```json
{
  "data": {
    "import_result": {
      "created_count": 4,
      "skipped_count": 1,
      "error_count": 0,
      "created_transactions": ["txn_789", "txn_790"]
    }
  }
}
```

### 6.4 Obtener transaccion
```http
GET /transactions/{transaction_id}
```

### 6.5 Actualizar transaccion
```http
PUT /transactions/{transaction_id}
Content-Type: application/json

{
  "description": "Descripcion actualizada",
  "amount": 3000,
  "category_id": "cat_789",
  "tags": ["updated", "shopping"]
}
```

### 6.6 Eliminar transaccion
```http
DELETE /transactions/{transaction_id}
```

### 6.7 Estadisticas de transacciones
```http
GET /transactions/stats?date_from=2024-01-01&date_to=2024-01-31&group_by=category
```

**Respuesta 200:**
```json
{
  "data": {
    "period": {
      "from": "2024-01-01",
      "to": "2024-01-31"
    },
    "summary": {
      "total_income": 300000, // centimos
      "total_expense": 180000,
      "net_balance": 120000,
      "transaction_count": 45
    },
    "by_category": [
      {
        "category_id": "cat_123",
        "category_name": "Alimentacion",
        "type": "expense",
        "amount": 45000,
        "transaction_count": 12,
        "percentage": 25.0
      }
    ]
  }
}
```

---

## 7. Gestion de elementos fijos

### 7.1 Listar elementos fijos
```http
GET /fixed-items?type=income&active=true
```

**Respuesta 200:**
```json
{
  "data": [
    {
      "id": "fix_123",
      "name": "Salario Mensual",
      "type": "income",
      "amount": 200000, // centimos
      "currency": "EUR",
      "frequency": "monthly", // weekly, monthly, yearly, custom
      "custom_frequency_days": null,
      "start_date": "2024-01-01",
      "end_date": null,
      "next_occurrence": "2024-02-01",
      "category_id": "cat_salary",
      "account_id": "acc_123",
      "is_active": true,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

### 7.2 Crear elemento fijo
```http
POST /fixed-items
Content-Type: application/json

{
  "name": "Alquiler Mensual",
  "type": "expense",
  "amount": 80000,
  "currency": "EUR",
  "frequency": "monthly",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "category_id": "cat_rent",
  "account_id": "acc_123"
}
```

### 7.3 Generar transacciones pendientes
```http
POST /fixed-items/generate
Content-Type: application/json

{
  "up_to_date": "2024-02-29", // Generar hasta esta fecha
  "preview_mode": false
}
```

**Respuesta 201:**
```json
{
  "data": {
    "generated_count": 3,
    "transaction_ids": ["txn_890", "txn_891", "txn_892"]
  }
}
```

---

## 8. Gestion de presupuestos

### 8.1 Listar presupuestos
```http
GET /budgets?period=2024-01&category_id=cat_123
```

**Respuesta 200:**
```json
{
  "data": [
    {
      "id": "bud_123",
      "category_id": "cat_123",
      "category_name": "Alimentacion",
      "period": "2024-01",
      "period_type": "monthly", // monthly, yearly
      "limit_amount": 50000, // centimos
      "spent_amount": 35000,
      "remaining_amount": 15000,
      "percentage_used": 70.0,
      "status": "warning", // ok, warning, exceeded
      "is_active": true,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

### 8.2 Crear presupuesto
```http
POST /budgets
Content-Type: application/json

{
  "category_id": "cat_123",
  "period": "2024-02",
  "period_type": "monthly",
  "limit_amount": 55000
}
```

### 8.3 Resumen de presupuestos
```http
GET /budgets/summary?period=2024-01
```

**Respuesta 200:**
```json
{
  "data": {
    "period": "2024-01",
    "total_budgeted": 250000,
    "total_spent": 180000,
    "total_remaining": 70000,
    "overall_percentage": 72.0,
    "status_counts": {
      "ok": 5,
      "warning": 2,
      "exceeded": 1
    }
  }
}
```

---

## 9. Proyectos de ahorro

### 9.1 Listar proyectos
```http
GET /savings-projects?status=active
```

**Respuesta 200:**
```json
{
  "data": [
    {
      "id": "sav_123",
      "name": "Vacaciones Europa",
      "description": "Viaje a Europa en verano",
      "target_amount": 300000, // centimos
      "current_amount": 150000,
      "remaining_amount": 150000,
      "progress_percentage": 50.0,
      "priority": 1, // 1=alta, 2=media, 3=baja
      "target_date": "2024-07-01",
      "status": "active", // active, completed, cancelled
      "associated_transactions": 15,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

### 9.2 Crear proyecto
```http
POST /savings-projects
Content-Type: application/json

{
  "name": "Fondo Emergencia",
  "description": "Fondo para emergencias",
  "target_amount": 500000,
  "priority": 1,
  "target_date": "2024-12-31"
}
```

### 9.3 Asociar transaccion a proyecto
```http
POST /savings-projects/{project_id}/transactions
Content-Type: application/json

{
  "transaction_id": "txn_123"
}
```

### 9.4 Completar proyecto
```http
POST /savings-projects/{project_id}/complete
```

---

## 10. Pagos diferidos

### 10.1 Listar pagos diferidos
```http
GET /deferred-payments?status=active
```

**Respuesta 200:**
```json
{
  "data": [
    {
      "id": "def_123",
      "name": "Prestamo Coche",
      "type": "loan", // loan, mortgage, installment
      "principal_amount": 2000000, // centimos
      "interest_rate": 5.5, // porcentaje anual
      "term_months": 60,
      "monthly_payment": 38124,
      "start_date": "2024-01-01",
      "end_date": "2025-01-01",
      "total_paid": 190620,
      "remaining_principal": 1809380,
      "total_interest_paid": 5678,
      "remaining_interest": 94436,
      "payments_made": 5,
      "remaining_payments": 55,
      "status": "active", // active, completed, defaulted
      "next_payment_date": "2024-06-01",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

### 10.2 Crear pago diferido
```http
POST /deferred-payments
Content-Type: application/json

{
  "name": "Hipoteca Casa",
  "type": "mortgage",
  "principal_amount": 30000000,
  "interest_rate": 3.2,
  "term_months": 300,
  "start_date": "2024-01-01",
  "account_id": "acc_123"
}
```

### 10.3 Registrar pago
```http
POST /deferred-payments/{payment_id}/payments
Content-Type: application/json

{
  "amount": 38124,
  "payment_date": "2024-02-01",
  "transaction_id": "txn_456" // Opcional
}
```

### 10.4 Calendario de pagos
```http
GET /deferred-payments/{payment_id}/schedule?from_payment=1&to_payment=12
```

**Respuesta 200:**
```json
{
  "data": {
    "payments": [
      {
        "payment_number": 1,
        "due_date": "2024-02-01",
        "total_amount": 38124,
        "principal_amount": 32446,
        "interest_amount": 5678,
        "remaining_balance": 1967554,
        "status": "paid", // pending, paid, late
        "paid_date": "2024-02-01"
      }
    ]
  }
}
```

---

## 11. Integracion con Asana

### 11.1 Iniciar OAuth con Asana
```http
GET /asana/oauth/authorize
```

**Respuesta 302:** Redirect a Asana OAuth

### 11.2 Callback OAuth
```http
GET /asana/oauth/callback?code=auth_code&state=csrf_token
```

**Respuesta 200:**
```json
{
  "data": {
    "status": "connected",
    "user_info": {
      "gid": "asana_user_123",
      "name": "Usuario Asana",
      "email": "user@example.com"
    },
    "workspaces": [
      {
        "gid": "workspace_456",
        "name": "Mi Workspace"
      }
    ]
  }
}
```

### 11.3 Obtener configuracion Asana
```http
GET /asana/config
```

**Respuesta 200:**
```json
{
  "data": {
    "status": "connected", // connected, disconnected
    "project": {
      "gid": "project_789",
      "name": "Finanzas Personales"
    },
    "sections_mapping": {
      "expenses_pending": "section_101",
      "expenses_processed": "section_102",
      "incomes_pending": "section_103",
      "incomes_processed": "section_104"
    },
    "field_mapping": {
      "amount_field": "custom_field_amount",
      "date_field": "due_date",
      "category_extraction": "tags" // tags, title, custom_field
    },
    "last_sync": "2024-01-15T09:00:00Z",
    "sync_stats": {
      "total_synced": 45,
      "last_sync_count": 3,
      "errors_count": 0
    }
  }
}
```

### 11.4 Configurar proyecto y secciones
```http
PUT /asana/config
Content-Type: application/json

{
  "project_gid": "project_789",
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
```

### 11.5 Listar proyectos disponibles
```http
GET /asana/projects?workspace_gid=workspace_456
```

**Respuesta 200:**
```json
{
  "data": [
    {
      "gid": "project_789",
      "name": "Finanzas Personales",
      "sections": [
        {
          "gid": "section_101",
          "name": "Gastos Pendientes"
        },
        {
          "gid": "section_102",
          "name": "Gastos Procesados"
        }
      ]
    }
  ]
}
```

### 11.6 Sincronizar tareas
```http
POST /asana/sync
Content-Type: application/json

{
  "dry_run": false // Solo simular, no crear transacciones
}
```

**Respuesta 200:**
```json
{
  "data": {
    "sync_id": "sync_abc123",
    "started_at": "2024-01-15T10:30:00Z",
    "completed_at": "2024-01-15T10:31:00Z",
    "results": {
      "tasks_read": 15,
      "expenses_created": 8,
      "incomes_created": 2,
      "tasks_moved": 10,
      "errors": 0,
      "skipped": 5 // Ya procesadas anteriormente
    },
    "errors": [],
    "created_transactions": ["txn_890", "txn_891"]
  }
}
```

### 11.7 Webhook de Asana
```http
POST /asana/webhook
Content-Type: application/json
X-Hook-Signature: sha256=...

{
  "events": [
    {
      "user": {
        "gid": "user_123"
      },
      "resource": {
        "gid": "task_456",
        "resource_type": "task"
      },
      "action": "added",
      "parent": {
        "gid": "section_101"
      }
    }
  ]
}
```

**Respuesta 200:**
```json
{
  "data": {
    "processed_events": 1,
    "triggered_syncs": 1
  }
}
```

### 11.8 Historial de sincronizaciones
```http
GET /asana/sync-history?page=1&page_size=10
```

**Respuesta 200:**
```json
{
  "data": [
    {
      "sync_id": "sync_abc123",
      "started_at": "2024-01-15T10:30:00Z",
      "completed_at": "2024-01-15T10:31:00Z",
      "status": "completed", // running, completed, failed
      "results": {
        "tasks_read": 15,
        "expenses_created": 8,
        "incomes_created": 2,
        "errors": 0
      }
    }
  ]
}
```

### 11.9 Desconectar Asana
```http
DELETE /asana/config
```

**Respuesta 204:** Sin contenido

---

## 12. Exportaciones para LLMs

### 12.1 Crear exportacion
```http
POST /exports
Content-Type: application/json

{
  "name": "Analisis Enero 2024",
  "date_from": "2024-01-01",
  "date_to": "2024-01-31",
  "include_types": ["transactions", "budgets", "categories"],
  "anonymize": true
}
```

**Respuesta 201:**
```json
{
  "data": {
    "export_id": "exp_123",
    "name": "Analisis Enero 2024",
    "status": "processing", // processing, ready, expired, failed
    "date_from": "2024-01-01",
    "date_to": "2024-01-31",
    "include_types": ["transactions", "budgets", "categories"],
    "anonymize": true,
    "created_at": "2024-01-15T10:30:00Z",
    "expires_at": "2024-01-16T10:30:00Z"
  }
}
```

### 12.2 Listar exportaciones
```http
GET /exports?status=ready
```

**Respuesta 200:**
```json
{
  "data": [
    {
      "export_id": "exp_123",
      "name": "Analisis Enero 2024",
      "status": "ready",
      "file_size": 15680, // bytes
      "download_count": 2,
      "created_at": "2024-01-15T10:30:00Z",
      "expires_at": "2024-01-16T10:30:00Z"
    }
  ]
}
```

### 12.3 Descargar exportacion
```http
GET /exports/{export_id}/download
```

**Respuesta 200:**
```
Content-Type: application/zip
Content-Disposition: attachment; filename="financial_export_exp_123.zip"

[Binary ZIP content with snapshot.json, instructions.md, constraints.md]
```

### 12.4 Obtener metadatos de exportacion
```http
GET /exports/{export_id}
```

**Respuesta 200:**
```json
{
  "data": {
    "export_id": "exp_123",
    "name": "Analisis Enero 2024",
    "status": "ready",
    "date_from": "2024-01-01",
    "date_to": "2024-01-31",
    "include_types": ["transactions", "budgets", "categories"],
    "anonymize": true,
    "file_size": 15680,
    "download_count": 2,
    "record_counts": {
      "transactions": 125,
      "categories": 15,
      "budgets": 8
    },
    "created_at": "2024-01-15T10:30:00Z",
    "expires_at": "2024-01-16T10:30:00Z"
  }
}
```

### 12.5 Eliminar exportacion
```http
DELETE /exports/{export_id}
```

**Respuesta 204:** Sin contenido

---

## 13. Gestion de datos y backups

### 13.1 Crear backup manual
```http
POST /admin/backups
Content-Type: application/json

{
  "description": "Backup manual enero 2024",
  "include_user_data": true,
  "upload_to_drive": true
}
```

**Respuesta 201:**
```json
{
  "data": {
    "backup_id": "bak_123",
    "description": "Backup manual enero 2024",
    "status": "processing", // processing, completed, failed
    "include_user_data": true,
    "upload_to_drive": true,
    "started_at": "2024-01-15T10:30:00Z"
  }
}
```

### 13.2 Listar backups
```http
GET /admin/backups?page=1&page_size=20
```

### 13.3 Exportar datos de usuario
```http
GET /user/export
```

**Respuesta 200:**
```
Content-Type: application/zip
Content-Disposition: attachment; filename="user_data_export.zip"

[Binary ZIP content with all user data]
```

### 13.4 Eliminar cuenta de usuario
```http
DELETE /user/account
Content-Type: application/json

{
  "confirmation": "DELETE_MY_ACCOUNT",
  "reason": "Ya no necesito el servicio"
}
```

**Respuesta 204:** Sin contenido

---

## 14. Health checks y metricas

### 14.1 Health check basico
```http
GET /health
```

**Respuesta 200:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "1.0.0",
  "environment": "production"
}
```

### 14.2 Health check detallado
```http
GET /health/detailed
```

**Respuesta 200:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "checks": {
    "database": {
      "status": "healthy",
      "response_time_ms": 15
    },
    "asana_api": {
      "status": "healthy",
      "response_time_ms": 120
    },
    "drive_api": {
      "status": "healthy",
      "response_time_ms": 200
    }
  }
}
```

### 14.3 Metricas de uso (Admin)
```http
GET /admin/metrics?period=last_30_days
```

**Respuesta 200:**
```json
{
  "data": {
    "period": "last_30_days",
    "users": {
      "total_users": 150,
      "active_users": 120,
      "new_users": 15
    },
    "transactions": {
      "total_transactions": 5420,
      "transactions_per_day": 180.67,
      "imports_count": 45
    },
    "asana_syncs": {
      "total_syncs": 890,
      "successful_syncs": 875,
      "failed_syncs": 15,
      "success_rate": 98.31
    },
    "exports": {
      "total_exports": 25,
      "total_downloads": 48
    },
    "resource_usage": {
      "firestore_reads": 125000,
      "firestore_writes": 35000,
      "api_requests": 280000
    }
  }
}
```

---

## 15. Codigos de error especificos

### 15.1 Errores de autenticacion
- `AUTH_001` - Token de Google invalido
- `AUTH_002` - Sesion expirada
- `AUTH_003` - Email sin invitacion valida
- `AUTH_004` - Invitacion expirada o consumida
- `AUTH_005` - Permisos insuficientes

### 15.2 Errores de validacion
- `VALIDATION_001` - Campo requerido faltante
- `VALIDATION_002` - Formato de datos invalido
- `VALIDATION_003` - Valor fuera de rango permitido
- `VALIDATION_004` - Referencia a entidad inexistente

### 15.3 Errores de negocio
- `BUSINESS_001` - Cuenta tiene transacciones asociadas
- `BUSINESS_002` - Categoria tiene subcategorias
- `BUSINESS_003` - Presupuesto ya existe para el periodo
- `BUSINESS_004` - Configuracion Asana incompleta
- `BUSINESS_005` - Transaccion duplicada (mismo external_ref)

### 15.4 Errores de integracion
- `INTEGRATION_001` - Error de conexion con Asana
- `INTEGRATION_002` - Token de Asana invalido o expirado
- `INTEGRATION_003` - Proyecto o seccion no encontrada en Asana
- `INTEGRATION_004` - Error de conexion con Google Drive
- `INTEGRATION_005` - Limite de rate limit alcanzado

---

Esta especificacion define todos los contratos API necesarios para el backend de Financial Nomad, manteniendo consistencia con la documentacion funcional y arquitectura establecidas.