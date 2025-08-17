# Contratos de API Frontend - Financial Nomad

## Vision General

Este documento define todos los contratos de API que el frontend Angular utilizara para comunicarse con el backend FastAPI. Incluye especificaciones detalladas de endpoints, modelos de datos, casos de error y ejemplos de uso.

## 1. Configuracion Base de API

### 1.1 Cliente HTTP Base

```typescript
// src/app/core/api/api.config.ts
export interface ApiConfig {
  baseUrl: string;
  timeout: number;
  retryAttempts: number;
  retryDelay: number;
}

export const API_CONFIG: ApiConfig = {
  baseUrl: environment.apiUrl,
  timeout: 30000,
  retryAttempts: 3,
  retryDelay: 1000
};
```

```typescript
// src/app/core/api/base-api.service.ts
@Injectable({ providedIn: 'root' })
export class BaseApiService {
  protected http = inject(HttpClient);
  protected config = inject(API_CONFIG);
  
  protected get<T>(url: string, options?: HttpOptions): Observable<T> {
    return this.http.get<T>(`${this.config.baseUrl}${url}`, options).pipe(
      timeout(this.config.timeout),
      retry({
        count: this.config.retryAttempts,
        delay: this.config.retryDelay
      }),
      catchError(this.handleError)
    );
  }
  
  protected post<T>(url: string, body: any, options?: HttpOptions): Observable<T> {
    return this.http.post<T>(`${this.config.baseUrl}${url}`, body, options).pipe(
      timeout(this.config.timeout),
      catchError(this.handleError)
    );
  }
  
  private handleError(error: HttpErrorResponse): Observable<never> {
    return throwError(() => new ApiError(error));
  }
}
```

### 1.2 Modelos Base

```typescript
// src/app/shared/models/base.models.ts
export interface ApiResponse<T = any> {
  data: T;
  message?: string;
  timestamp: string;
  requestId: string;
}

export interface ApiError {
  error: {
    code: string;
    message: string;
    details?: string[];
  };
  meta: {
    timestamp: number;
    requestId: string;
    path: string;
  };
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  totalPages: number;
  hasNext: boolean;
  hasPrevious: boolean;
}

export interface PaginationParams {
  page: number;
  size: number;
  sort?: string;
  order?: 'asc' | 'desc';
}
```

## 2. Autenticacion y Usuarios

### 2.1 Modelos de Autenticacion

```typescript
// src/app/core/auth/auth.models.ts
export interface LoginRequest {
  google_token: string;
  invitation_code?: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: UserProfile;
}

export interface UserProfile {
  id: string;
  email: string;
  name: string;
  picture?: string;
  role: UserRole;
  status: UserStatus;
  locale: string;
  timezone: string;
  currency: string;
  last_login?: string;
  has_asana_integration: boolean;
}

export enum UserRole {
  ADMIN = 'admin',
  USER = 'user',
  GUEST = 'guest'
}

export enum UserStatus {
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  SUSPENDED = 'suspended',
  PENDING = 'pending'
}

export interface UserPreferencesUpdate {
  locale?: string;
  timezone?: string;
  currency?: string;
}

export interface InvitationRequest {
  email: string;
  suggested_name?: string;
  message?: string;
  expires_in_days: number;
}

export interface InvitationResponse {
  id: string;
  email: string;
  invitation_code: string;
  expires_at: string;
  invited_by_name: string;
}

export interface TokenVerificationResponse {
  valid: boolean;
  user_id: string;
  email: string;
  expires_at: string;
}
```

### 2.2 Servicio de Autenticacion

```typescript
// src/app/core/auth/auth.service.ts
@Injectable({ providedIn: 'root' })
export class AuthService extends BaseApiService {
  
  /**
   * POST /api/v1/auth/login
   * Autentica usuario con token de Google OAuth
   */
  login(request: LoginRequest): Observable<LoginResponse> {
    return this.post<LoginResponse>('/auth/login', request);
  }
  
  /**
   * POST /api/v1/auth/logout
   * Cierra sesion del usuario actual
   */
  logout(): Observable<void> {
    return this.post<void>('/auth/logout', {});
  }
  
  /**
   * POST /api/v1/auth/logout-all
   * Cierra todas las sesiones del usuario
   */
  logoutAllSessions(): Observable<void> {
    return this.post<void>('/auth/logout-all', {});
  }
  
  /**
   * GET /api/v1/auth/profile
   * Obtiene perfil del usuario actual
   */
  getProfile(): Observable<UserProfile> {
    return this.get<UserProfile>('/auth/profile');
  }
  
  /**
   * PUT /api/v1/auth/profile
   * Actualiza preferencias del usuario
   */
  updateProfile(preferences: UserPreferencesUpdate): Observable<UserProfile> {
    return this.http.put<UserProfile>(`${this.config.baseUrl}/auth/profile`, preferences);
  }
  
  /**
   * POST /api/v1/auth/invite
   * Crea una nueva invitacion de usuario
   */
  createInvitation(request: InvitationRequest): Observable<InvitationResponse> {
    return this.post<InvitationResponse>('/auth/invite', request);
  }
  
  /**
   * GET /api/v1/auth/verify
   * Verifica si el token actual es valido
   */
  verifyToken(): Observable<TokenVerificationResponse> {
    return this.get<TokenVerificationResponse>('/auth/verify');
  }
}
```

## 3. Gestion de Cuentas

### 3.1 Modelos de Cuenta

```typescript
// src/app/features/accounts/models/account.models.ts
export interface Account {
  id: string;
  user_id: string;
  name: string;
  account_type: AccountType;
  balance: number;
  currency: string;
  description?: string;
  is_active: boolean;
  color?: string;
  icon?: string;
  created_at: string;
  updated_at: string;
  is_deleted: boolean;
}

export enum AccountType {
  CHECKING = 'checking',
  SAVINGS = 'savings',
  CREDIT_CARD = 'credit_card',
  CASH = 'cash',
  INVESTMENT = 'investment',
  LOAN = 'loan',
  OTHER = 'other'
}

export interface AccountSummary {
  id: string;
  name: string;
  account_type: AccountType;
  balance: number;
  currency: string;
  is_active: boolean;
  color?: string;
  icon?: string;
}

export interface CreateAccountRequest {
  name: string;
  account_type: AccountType;
  balance?: number;
  currency?: string;
  description?: string;
  color?: string;
  icon?: string;
}

export interface UpdateAccountRequest {
  name?: string;
  account_type?: AccountType;
  balance?: number;
  description?: string;
  is_active?: boolean;
  color?: string;
  icon?: string;
}
```

### 3.2 Servicio de Cuentas

```typescript
// src/app/features/accounts/services/account.service.ts
@Injectable({ providedIn: 'root' })
export class AccountService extends BaseApiService {
  
  /**
   * GET /api/v1/accounts
   * Lista todas las cuentas del usuario
   */
  getAccounts(includeInactive = false): Observable<AccountSummary[]> {
    const params = includeInactive ? { include_inactive: 'true' } : {};
    return this.get<AccountSummary[]>('/accounts', { params });
  }
  
  /**
   * GET /api/v1/accounts/{id}
   * Obtiene detalles de una cuenta especifica
   */
  getAccount(id: string): Observable<Account> {
    return this.get<Account>(`/accounts/${id}`);
  }
  
  /**
   * POST /api/v1/accounts
   * Crea una nueva cuenta
   */
  createAccount(request: CreateAccountRequest): Observable<Account> {
    return this.post<Account>('/accounts', request);
  }
  
  /**
   * PUT /api/v1/accounts/{id}
   * Actualiza una cuenta existente
   */
  updateAccount(id: string, request: UpdateAccountRequest): Observable<Account> {
    return this.http.put<Account>(`${this.config.baseUrl}/accounts/${id}`, request);
  }
  
  /**
   * DELETE /api/v1/accounts/{id}
   * Elimina una cuenta (soft delete)
   */
  deleteAccount(id: string): Observable<void> {
    return this.http.delete<void>(`${this.config.baseUrl}/accounts/${id}`);
  }
  
  /**
   * GET /api/v1/accounts/{id}/balance
   * Obtiene balance actual de una cuenta
   */
  getAccountBalance(id: string): Observable<{ balance: number; currency: string }> {
    return this.get<{ balance: number; currency: string }>(`/accounts/${id}/balance`);
  }
}
```

## 4. Gestion de Categorias

### 4.1 Modelos de Categoria

```typescript
// src/app/features/categories/models/category.models.ts
export interface Category {
  id: string;
  user_id: string;
  name: string;
  category_type: CategoryType;
  parent_id?: string;
  description?: string;
  is_active: boolean;
  color?: string;
  icon?: string;
  monthly_budget?: number;
  created_at: string;
  updated_at: string;
  is_deleted: boolean;
}

export enum CategoryType {
  INCOME = 'income',
  EXPENSE = 'expense',
  TRANSFER = 'transfer'
}

export interface CategorySummary {
  id: string;
  name: string;
  category_type: CategoryType;
  parent_name?: string;
  monthly_budget?: number;
  is_active: boolean;
  color?: string;
  icon?: string;
}

export interface CategoryTree {
  category: CategorySummary;
  children: CategoryTree[];
}

export interface CreateCategoryRequest {
  name: string;
  category_type: CategoryType;
  parent_id?: string;
  description?: string;
  color?: string;
  icon?: string;
  monthly_budget?: number;
}

export interface UpdateCategoryRequest {
  name?: string;
  parent_id?: string;
  description?: string;
  is_active?: boolean;
  color?: string;
  icon?: string;
  monthly_budget?: number;
}
```

### 4.2 Servicio de Categorias

```typescript
// src/app/features/categories/services/category.service.ts
@Injectable({ providedIn: 'root' })
export class CategoryService extends BaseApiService {
  
  /**
   * GET /api/v1/categories
   * Lista todas las categorias del usuario
   */
  getCategories(type?: CategoryType, includeInactive = false): Observable<CategorySummary[]> {
    const params: any = {};
    if (type) params.type = type;
    if (includeInactive) params.include_inactive = 'true';
    
    return this.get<CategorySummary[]>('/categories', { params });
  }
  
  /**
   * GET /api/v1/categories/tree
   * Obtiene categorias en estructura jerarquica
   */
  getCategoryTree(type?: CategoryType): Observable<CategoryTree[]> {
    const params = type ? { type } : {};
    return this.get<CategoryTree[]>('/categories/tree', { params });
  }
  
  /**
   * GET /api/v1/categories/{id}
   * Obtiene detalles de una categoria especifica
   */
  getCategory(id: string): Observable<Category> {
    return this.get<Category>(`/categories/${id}`);
  }
  
  /**
   * POST /api/v1/categories
   * Crea una nueva categoria
   */
  createCategory(request: CreateCategoryRequest): Observable<Category> {
    return this.post<Category>('/categories', request);
  }
  
  /**
   * PUT /api/v1/categories/{id}
   * Actualiza una categoria existente
   */
  updateCategory(id: string, request: UpdateCategoryRequest): Observable<Category> {
    return this.http.put<Category>(`${this.config.baseUrl}/categories/${id}`, request);
  }
  
  /**
   * DELETE /api/v1/categories/{id}
   * Elimina una categoria (soft delete)
   */
  deleteCategory(id: string): Observable<void> {
    return this.http.delete<void>(`${this.config.baseUrl}/categories/${id}`);
  }
}
```

## 5. Gestion de Transacciones

### 5.1 Modelos de Transaccion

```typescript
// src/app/features/transactions/models/transaction.models.ts
export interface Transaction {
  id: string;
  user_id: string;
  amount: number;
  description: string;
  transaction_type: TransactionType;
  transaction_date: string;
  account_id: string;
  to_account_id?: string;
  category_id: string;
  subcategory_id?: string;
  reference?: string;
  notes?: string;
  tags: string[];
  import_id?: string;
  import_source?: string;
  is_confirmed: boolean;
  is_reconciled: boolean;
  created_at: string;
  updated_at: string;
  is_deleted: boolean;
}

export enum TransactionType {
  INCOME = 'income',
  EXPENSE = 'expense',
  TRANSFER = 'transfer'
}

export interface TransactionSummary {
  id: string;
  amount: number;
  description: string;
  transaction_type: TransactionType;
  transaction_date: string;
  account_name: string;
  category_name: string;
  is_confirmed: boolean;
}

export interface CreateTransactionRequest {
  amount: number;
  description: string;
  transaction_type: TransactionType;
  transaction_date: string;
  account_id: string;
  to_account_id?: string;
  category_id: string;
  subcategory_id?: string;
  reference?: string;
  notes?: string;
  tags?: string[];
}

export interface UpdateTransactionRequest {
  amount?: number;
  description?: string;
  transaction_date?: string;
  account_id?: string;
  to_account_id?: string;
  category_id?: string;
  subcategory_id?: string;
  reference?: string;
  notes?: string;
  tags?: string[];
  is_confirmed?: boolean;
  is_reconciled?: boolean;
}

export interface TransactionFilters {
  account_id?: string;
  category_id?: string;
  transaction_type?: TransactionType;
  date_from?: string;
  date_to?: string;
  amount_min?: number;
  amount_max?: number;
  search?: string;
  tags?: string[];
  is_confirmed?: boolean;
  is_reconciled?: boolean;
}

export interface BulkImportRequest {
  yaml_content: string;
  date_format?: string;
  default_account_id?: string;
  dry_run?: boolean;
}

export interface BulkImportResponse {
  success_count: number;
  error_count: number;
  errors: ImportError[];
  transactions?: TransactionSummary[];
}

export interface ImportError {
  line: number;
  field?: string;
  message: string;
  raw_data: any;
}
```

### 5.2 Servicio de Transacciones

```typescript
// src/app/features/transactions/services/transaction.service.ts
@Injectable({ providedIn: 'root' })
export class TransactionService extends BaseApiService {
  
  /**
   * GET /api/v1/transactions
   * Lista transacciones con filtros y paginacion
   */
  getTransactions(
    filters?: TransactionFilters,
    pagination?: PaginationParams
  ): Observable<PaginatedResponse<TransactionSummary>> {
    const params: any = { ...filters, ...pagination };
    return this.get<PaginatedResponse<TransactionSummary>>('/transactions', { params });
  }
  
  /**
   * GET /api/v1/transactions/{id}
   * Obtiene detalles de una transaccion especifica
   */
  getTransaction(id: string): Observable<Transaction> {
    return this.get<Transaction>(`/transactions/${id}`);
  }
  
  /**
   * POST /api/v1/transactions
   * Crea una nueva transaccion
   */
  createTransaction(request: CreateTransactionRequest): Observable<Transaction> {
    return this.post<Transaction>('/transactions', request);
  }
  
  /**
   * PUT /api/v1/transactions/{id}
   * Actualiza una transaccion existente
   */
  updateTransaction(id: string, request: UpdateTransactionRequest): Observable<Transaction> {
    return this.http.put<Transaction>(`${this.config.baseUrl}/transactions/${id}`, request);
  }
  
  /**
   * DELETE /api/v1/transactions/{id}
   * Elimina una transaccion (soft delete)
   */
  deleteTransaction(id: string): Observable<void> {
    return this.http.delete<void>(`${this.config.baseUrl}/transactions/${id}`);
  }
  
  /**
   * POST /api/v1/transactions/bulk-import
   * Importa transacciones desde YAML
   */
  bulkImport(request: BulkImportRequest): Observable<BulkImportResponse> {
    return this.post<BulkImportResponse>('/transactions/bulk-import', request);
  }
  
  /**
   * GET /api/v1/transactions/export
   * Exporta transacciones en formato especificado
   */
  exportTransactions(
    format: 'csv' | 'excel' | 'pdf',
    filters?: TransactionFilters
  ): Observable<Blob> {
    const params: any = { format, ...filters };
    return this.http.get(`${this.config.baseUrl}/transactions/export`, {
      params,
      responseType: 'blob'
    });
  }
  
  /**
   * PUT /api/v1/transactions/{id}/confirm
   * Confirma una transaccion
   */
  confirmTransaction(id: string): Observable<Transaction> {
    return this.http.put<Transaction>(`${this.config.baseUrl}/transactions/${id}/confirm`, {});
  }
  
  /**
   * PUT /api/v1/transactions/{id}/reconcile
   * Marca una transaccion como reconciliada
   */
  reconcileTransaction(id: string): Observable<Transaction> {
    return this.http.put<Transaction>(`${this.config.baseUrl}/transactions/${id}/reconcile`, {});
  }
}
```

## 6. Gestion de Presupuestos

### 6.1 Modelos de Presupuesto

```typescript
// src/app/features/budgets/models/budget.models.ts
export interface Budget {
  id: string;
  user_id: string;
  name: string;
  category_id: string;
  amount: number;
  period_start: string;
  period_end: string;
  spent_amount: number;
  is_active: boolean;
  alert_threshold?: number;
  alert_sent: boolean;
  created_at: string;
  updated_at: string;
  is_deleted: boolean;
}

export interface BudgetSummary {
  id: string;
  name: string;
  category_name: string;
  amount: number;
  spent_amount: number;
  remaining_amount: number;
  percentage_used: number;
  period_start: string;
  period_end: string;
  is_over_budget: boolean;
  days_remaining: number;
}

export interface CreateBudgetRequest {
  name: string;
  category_id: string;
  amount: number;
  period_start: string;
  period_end: string;
  alert_threshold?: number;
}

export interface UpdateBudgetRequest {
  name?: string;
  amount?: number;
  period_start?: string;
  period_end?: string;
  is_active?: boolean;
  alert_threshold?: number;
}

export interface BudgetProgress {
  budget_id: string;
  period: string;
  total_budget: number;
  spent_amount: number;
  remaining_amount: number;
  percentage_used: number;
  daily_average: number;
  projected_total: number;
  status: 'on_track' | 'over_budget' | 'warning';
}

export interface BudgetAlert {
  budget_id: string;
  budget_name: string;
  category_name: string;
  alert_type: 'threshold_reached' | 'over_budget' | 'period_ending';
  message: string;
  created_at: string;
}
```

### 6.2 Servicio de Presupuestos

```typescript
// src/app/features/budgets/services/budget.service.ts
@Injectable({ providedIn: 'root' })
export class BudgetService extends BaseApiService {
  
  /**
   * GET /api/v1/budgets
   * Lista presupuestos del usuario
   */
  getBudgets(includeInactive = false): Observable<BudgetSummary[]> {
    const params = includeInactive ? { include_inactive: 'true' } : {};
    return this.get<BudgetSummary[]>('/budgets', { params });
  }
  
  /**
   * GET /api/v1/budgets/{id}
   * Obtiene detalles de un presupuesto especifico
   */
  getBudget(id: string): Observable<Budget> {
    return this.get<Budget>(`/budgets/${id}`);
  }
  
  /**
   * POST /api/v1/budgets
   * Crea un nuevo presupuesto
   */
  createBudget(request: CreateBudgetRequest): Observable<Budget> {
    return this.post<Budget>('/budgets', request);
  }
  
  /**
   * PUT /api/v1/budgets/{id}
   * Actualiza un presupuesto existente
   */
  updateBudget(id: string, request: UpdateBudgetRequest): Observable<Budget> {
    return this.http.put<Budget>(`${this.config.baseUrl}/budgets/${id}`, request);
  }
  
  /**
   * DELETE /api/v1/budgets/{id}
   * Elimina un presupuesto (soft delete)
   */
  deleteBudget(id: string): Observable<void> {
    return this.http.delete<void>(`${this.config.baseUrl}/budgets/${id}`);
  }
  
  /**
   * GET /api/v1/budgets/{id}/progress
   * Obtiene progreso de un presupuesto
   */
  getBudgetProgress(id: string): Observable<BudgetProgress> {
    return this.get<BudgetProgress>(`/budgets/${id}/progress`);
  }
  
  /**
   * GET /api/v1/budgets/alerts
   * Obtiene alertas de presupuestos
   */
  getBudgetAlerts(): Observable<BudgetAlert[]> {
    return this.get<BudgetAlert[]>('/budgets/alerts');
  }
  
  /**
   * PUT /api/v1/budgets/{id}/reset
   * Reinicia un presupuesto para el siguiente periodo
   */
  resetBudget(id: string): Observable<Budget> {
    return this.http.put<Budget>(`${this.config.baseUrl}/budgets/${id}/reset`, {});
  }
}
```

## 7. Dashboard y Reportes

### 7.1 Modelos de Dashboard

```typescript
// src/app/features/dashboard/models/dashboard.models.ts
export interface DashboardSummary {
  total_balance: number;
  monthly_income: number;
  monthly_expenses: number;
  net_income: number;
  account_balances: AccountBalance[];
  recent_transactions: TransactionSummary[];
  budget_alerts: BudgetAlert[];
  period: string;
}

export interface AccountBalance {
  account_id: string;
  account_name: string;
  account_type: AccountType;
  balance: number;
  currency: string;
  percentage_of_total: number;
}

export interface MonthlyStats {
  month: string;
  total_income: number;
  total_expenses: number;
  net_amount: number;
  transaction_count: number;
  top_categories: CategorySpending[];
}

export interface CategorySpending {
  category_id: string;
  category_name: string;
  amount: number;
  percentage: number;
  transaction_count: number;
}

export interface TrendData {
  period: string;
  income: number;
  expenses: number;
  balance: number;
}

export interface ReportFilters {
  date_from: string;
  date_to: string;
  account_ids?: string[];
  category_ids?: string[];
  transaction_types?: TransactionType[];
}
```

### 7.2 Servicio de Dashboard y Reportes

```typescript
// src/app/features/dashboard/services/dashboard.service.ts
@Injectable({ providedIn: 'root' })
export class DashboardService extends BaseApiService {
  
  /**
   * GET /api/v1/dashboard/summary
   * Obtiene resumen del dashboard
   */
  getDashboardSummary(period = 'current_month'): Observable<DashboardSummary> {
    return this.get<DashboardSummary>('/dashboard/summary', {
      params: { period }
    });
  }
  
  /**
   * GET /api/v1/dashboard/monthly-stats
   * Obtiene estadisticas mensuales
   */
  getMonthlyStats(year: number, month?: number): Observable<MonthlyStats[]> {
    const params: any = { year };
    if (month) params.month = month;
    
    return this.get<MonthlyStats[]>('/dashboard/monthly-stats', { params });
  }
  
  /**
   * GET /api/v1/dashboard/trends
   * Obtiene datos de tendencias
   */
  getTrends(months = 6): Observable<TrendData[]> {
    return this.get<TrendData[]>('/dashboard/trends', {
      params: { months }
    });
  }
  
  /**
   * GET /api/v1/dashboard/category-breakdown
   * Obtiene desglose por categorias
   */
  getCategoryBreakdown(filters: ReportFilters): Observable<CategorySpending[]> {
    return this.get<CategorySpending[]>('/dashboard/category-breakdown', {
      params: filters as any
    });
  }
}
```

## 8. Integracion Asana

### 8.1 Modelos de Asana

```typescript
// src/app/features/asana/models/asana.models.ts
export interface AsanaIntegration {
  user_id: string;
  is_connected: boolean;
  workspace_id?: string;
  workspace_name?: string;
  last_sync: string;
  sync_enabled: boolean;
  settings: AsanaSettings;
}

export interface AsanaSettings {
  auto_sync: boolean;
  sync_frequency: 'manual' | 'hourly' | 'daily';
  task_mapping: TaskMapping;
  webhook_enabled: boolean;
}

export interface TaskMapping {
  transaction_project_id?: string;
  budget_project_id?: string;
  default_assignee?: string;
  tag_prefix?: string;
}

export interface AsanaTask {
  id: string;
  name: string;
  notes?: string;
  assignee?: string;
  project_id: string;
  completed: boolean;
  due_date?: string;
  tags: string[];
  custom_fields: Record<string, any>;
  transaction_id?: string;
  budget_id?: string;
}

export interface SyncReport {
  sync_id: string;
  started_at: string;
  completed_at?: string;
  status: 'running' | 'completed' | 'failed';
  items_processed: number;
  items_created: number;
  items_updated: number;
  errors: SyncError[];
}

export interface SyncError {
  item_type: 'transaction' | 'budget' | 'task';
  item_id: string;
  error_code: string;
  error_message: string;
}
```

### 8.2 Servicio de Asana

```typescript
// src/app/features/asana/services/asana.service.ts
@Injectable({ providedIn: 'root' })
export class AsanaService extends BaseApiService {
  
  /**
   * GET /api/v1/asana/integration
   * Obtiene estado de la integracion con Asana
   */
  getIntegration(): Observable<AsanaIntegration> {
    return this.get<AsanaIntegration>('/asana/integration');
  }
  
  /**
   * POST /api/v1/asana/connect
   * Inicia proceso de conexion OAuth con Asana
   */
  connect(): Observable<{ auth_url: string }> {
    return this.post<{ auth_url: string }>('/asana/connect', {});
  }
  
  /**
   * POST /api/v1/asana/disconnect
   * Desconecta la integracion con Asana
   */
  disconnect(): Observable<void> {
    return this.post<void>('/asana/disconnect', {});
  }
  
  /**
   * PUT /api/v1/asana/settings
   * Actualiza configuracion de la integracion
   */
  updateSettings(settings: AsanaSettings): Observable<AsanaIntegration> {
    return this.http.put<AsanaIntegration>(`${this.config.baseUrl}/asana/settings`, settings);
  }
  
  /**
   * POST /api/v1/asana/sync
   * Inicia sincronizacion manual
   */
  startSync(): Observable<SyncReport> {
    return this.post<SyncReport>('/asana/sync', {});
  }
  
  /**
   * GET /api/v1/asana/sync/{id}
   * Obtiene estado de una sincronizacion
   */
  getSyncStatus(syncId: string): Observable<SyncReport> {
    return this.get<SyncReport>(`/asana/sync/${syncId}`);
  }
  
  /**
   * GET /api/v1/asana/workspaces
   * Lista workspaces disponibles de Asana
   */
  getWorkspaces(): Observable<{ id: string; name: string }[]> {
    return this.get<{ id: string; name: string }[]>('/asana/workspaces');
  }
  
  /**
   * GET /api/v1/asana/projects
   * Lista proyectos del workspace seleccionado
   */
  getProjects(): Observable<{ id: string; name: string }[]> {
    return this.get<{ id: string; name: string }[]>('/asana/projects');
  }
}
```

## 9. Sistema de Archivos y Exportacion

### 9.1 Modelos de Archivos

```typescript
// src/app/features/reports/models/export.models.ts
export interface ExportRequest {
  format: 'csv' | 'excel' | 'pdf' | 'json';
  data_type: 'transactions' | 'accounts' | 'budgets' | 'complete';
  filters?: any;
  date_range?: {
    start: string;
    end: string;
  };
  include_metadata?: boolean;
}

export interface ExportJob {
  id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  download_url?: string;
  expires_at?: string;
  error_message?: string;
  created_at: string;
}

export interface LLMExportRequest {
  include_pii: boolean;
  anonymize_data: boolean;
  include_analysis_instructions: boolean;
  date_range?: {
    start: string;
    end: string;
  };
}

export interface BackupInfo {
  id: string;
  backup_date: string;
  size_bytes: number;
  status: 'completed' | 'failed' | 'in_progress';
  download_url?: string;
  expires_at: string;
}
```

### 9.2 Servicio de Exportacion

```typescript
// src/app/features/reports/services/export.service.ts
@Injectable({ providedIn: 'root' })
export class ExportService extends BaseApiService {
  
  /**
   * POST /api/v1/export/create
   * Crea un trabajo de exportacion
   */
  createExport(request: ExportRequest): Observable<ExportJob> {
    return this.post<ExportJob>('/export/create', request);
  }
  
  /**
   * GET /api/v1/export/{id}/status
   * Obtiene estado de un trabajo de exportacion
   */
  getExportStatus(id: string): Observable<ExportJob> {
    return this.get<ExportJob>(`/export/${id}/status`);
  }
  
  /**
   * GET /api/v1/export/{id}/download
   * Descarga archivo exportado
   */
  downloadExport(id: string): Observable<Blob> {
    return this.http.get(`${this.config.baseUrl}/export/${id}/download`, {
      responseType: 'blob'
    });
  }
  
  /**
   * POST /api/v1/export/llm
   * Crea exportacion para LLMs
   */
  createLLMExport(request: LLMExportRequest): Observable<{
    snapshot_url: string;
    instructions_url: string;
    expires_at: string;
  }> {
    return this.post('/export/llm', request);
  }
  
  /**
   * GET /api/v1/backups
   * Lista backups disponibles
   */
  getBackups(): Observable<BackupInfo[]> {
    return this.get<BackupInfo[]>('/backups');
  }
  
  /**
   * POST /api/v1/backups/create
   * Solicita creacion de backup manual
   */
  createBackup(): Observable<BackupInfo> {
    return this.post<BackupInfo>('/backups/create', {});
  }
}
```

## 10. Health Check y Monitoreo

### 10.1 Modelos de Health Check

```typescript
// src/app/core/health/health.models.ts
export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: string;
  version: string;
  uptime: number;
  checks: HealthCheck[];
}

export interface HealthCheck {
  name: string;
  status: 'healthy' | 'unhealthy';
  duration_ms: number;
  details?: Record<string, any>;
}
```

### 10.2 Servicio de Health Check

```typescript
// src/app/core/health/health.service.ts
@Injectable({ providedIn: 'root' })
export class HealthService extends BaseApiService {
  
  /**
   * GET /api/v1/health
   * Obtiene estado de salud del sistema
   */
  getHealth(): Observable<HealthStatus> {
    return this.get<HealthStatus>('/health');
  }
  
  /**
   * GET /api/v1/health/ready
   * Verifica si el sistema esta listo
   */
  getReadiness(): Observable<{ ready: boolean }> {
    return this.get<{ ready: boolean }>('/health/ready');
  }
  
  /**
   * GET /api/v1/health/live
   * Verifica si el sistema esta vivo
   */
  getLiveness(): Observable<{ alive: boolean }> {
    return this.get<{ alive: boolean }>('/health/live');
  }
}
```

## 11. Interceptores y Manejo de Errores

### 11.1 Error Interceptor

```typescript
// src/app/core/interceptors/error.interceptor.ts
@Injectable()
export class ErrorInterceptor implements HttpInterceptor {
  
  constructor(
    private notificationService: NotificationService,
    private router: Router
  ) {}
  
  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    return next.handle(req).pipe(
      catchError((error: HttpErrorResponse) => {
        this.handleError(error);
        return throwError(() => error);
      })
    );
  }
  
  private handleError(error: HttpErrorResponse): void {
    switch (error.status) {
      case 401:
        this.handleUnauthorized(error);
        break;
      case 403:
        this.handleForbidden(error);
        break;
      case 404:
        this.handleNotFound(error);
        break;
      case 422:
        this.handleValidationError(error);
        break;
      case 500:
        this.handleServerError(error);
        break;
      default:
        this.handleGenericError(error);
    }
  }
  
  private handleUnauthorized(error: HttpErrorResponse): void {
    this.notificationService.showError('Sesion expirada. Por favor, inicia sesion nuevamente.');
    this.router.navigate(['/auth/login']);
  }
  
  private handleValidationError(error: HttpErrorResponse): void {
    const apiError = error.error as ApiError;
    const message = apiError.error?.message || 'Error de validacion';
    this.notificationService.showError(message);
  }
  
  private handleServerError(error: HttpErrorResponse): void {
    this.notificationService.showError('Error interno del servidor. Intenta nuevamente.');
  }
  
  private handleGenericError(error: HttpErrorResponse): void {
    const message = error.error?.error?.message || 'Error inesperado';
    this.notificationService.showError(message);
  }
}
```

### 11.2 Loading Interceptor

```typescript
// src/app/core/interceptors/loading.interceptor.ts
@Injectable()
export class LoadingInterceptor implements HttpInterceptor {
  private activeRequests = 0;
  private loadingSubject = new BehaviorSubject<boolean>(false);
  
  loading$ = this.loadingSubject.asObservable();
  
  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    // No mostrar loading para requests de health check
    if (req.url.includes('/health')) {
      return next.handle(req);
    }
    
    this.activeRequests++;
    this.updateLoadingState();
    
    return next.handle(req).pipe(
      finalize(() => {
        this.activeRequests--;
        this.updateLoadingState();
      })
    );
  }
  
  private updateLoadingState(): void {
    this.loadingSubject.next(this.activeRequests > 0);
  }
}
```

## 12. Tipos Utilitarios

### 12.1 Tipos HTTP

```typescript
// src/app/shared/types/http.types.ts
export interface HttpOptions {
  headers?: HttpHeaders | {
    [header: string]: string | string[];
  };
  params?: HttpParams | {
    [param: string]: string | string[];
  };
  observe?: 'body';
  responseType?: 'json';
  reportProgress?: boolean;
  withCredentials?: boolean;
}

export interface RequestConfig {
  retries?: number;
  timeout?: number;
  skipErrorHandler?: boolean;
  skipLoadingIndicator?: boolean;
}
```

### 12.2 Validadores de Formulario

```typescript
// src/app/shared/validators/api.validators.ts
export class ApiValidators {
  
  static uniqueEmail(authService: AuthService): AsyncValidatorFn {
    return (control: AbstractControl): Observable<ValidationErrors | null> => {
      if (!control.value) {
        return of(null);
      }
      
      return authService.checkEmailExists(control.value).pipe(
        map(exists => exists ? { emailExists: true } : null),
        catchError(() => of(null))
      );
    };
  }
  
  static uniqueAccountName(accountService: AccountService): AsyncValidatorFn {
    return (control: AbstractControl): Observable<ValidationErrors | null> => {
      if (!control.value) {
        return of(null);
      }
      
      return accountService.checkNameExists(control.value).pipe(
        map(exists => exists ? { nameExists: true } : null),
        catchError(() => of(null))
      );
    };
  }
}
```

---

## Conclusion

Esta especificacion de contratos de API proporciona una base completa para la comunicacion entre el frontend Angular y el backend FastAPI de Financial Nomad. Los modelos TypeScript aseguran type safety, mientras que los servicios encapsulan toda la logica de comunicacion con la API.

Los interceptores manejan concerns transversales como autenticacion, errores y estados de carga, proporcionando una experiencia de usuario consistente y robusta.