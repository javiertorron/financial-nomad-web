// Tipos para entidades financieras - alineados con la API backend
export interface Account {
  id: string;
  name: string;
  account_type: AccountType;
  balance: string; // Decimal como string desde la API
  currency: string;
  description?: string;
  is_active: boolean;
  color?: string;
  icon?: string;
  created_at: string;
  updated_at: string;
}

export interface AccountSummary {
  id: string;
  name: string;
  account_type: AccountType;
  balance: string;
  currency: string;
  description?: string;
  is_active: boolean;
  color?: string;
  icon?: string;
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

export interface Category {
  id: string;
  name: string;
  category_type: CategoryType;
  parent_id?: string;
  description?: string;
  is_active: boolean;
  color?: string;
  icon?: string;
  monthly_budget?: string;
  is_system?: boolean;
  created_at: string;
  updated_at: string;
}

export interface CategorySummary {
  id: string;
  name: string;
  category_type: CategoryType;
  parent_name?: string;
  monthly_budget?: string;
  is_active: boolean;
  is_system?: boolean;
  color?: string;
  icon?: string;
}

export enum CategoryType {
  INCOME = 'income',
  EXPENSE = 'expense',
  TRANSFER = 'transfer'
}

export interface Transaction {
  id: string;
  account_id: string;
  category_id?: string;
  amount: string; // Decimal como string desde la API
  description: string;
  transaction_date: string;
  destination_account_id?: string;
  reference_number?: string;
  notes?: string;
  tags?: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface TransactionSummary {
  id: string;
  account_id: string;
  category_id?: string;
  amount: string;
  description: string;
  transaction_date: string;
  destination_account_id?: string;
  is_active: boolean;
}

export interface Budget {
  id: string;
  user_id: string;
  name: string;
  category_id: string;
  amount: number;
  period: BudgetPeriod;
  start_date: string;
  end_date?: string;
  spent: number;
  remaining: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  category?: Category;
}

export enum BudgetPeriod {
  WEEKLY = 'weekly',
  MONTHLY = 'monthly',
  QUARTERLY = 'quarterly',
  YEARLY = 'yearly'
}

// DTOs para crear/actualizar entidades - alineados con la API backend
export interface CreateAccountRequest {
  name: string;
  account_type: AccountType;
  balance?: string;
  currency?: string;
  description?: string;
  color?: string;
  icon?: string;
}

export interface UpdateAccountRequest {
  name?: string;
  balance?: string;
  description?: string;
  is_active?: boolean;
  color?: string;
  icon?: string;
}

export interface CreateCategoryRequest {
  name: string;
  category_type: CategoryType;
  parent_id?: string;
  description?: string;
  color?: string;
  icon?: string;
  monthly_budget?: string;
}

export interface UpdateCategoryRequest {
  name?: string;
  parent_id?: string;
  description?: string;
  is_active?: boolean;
  color?: string;
  icon?: string;
  monthly_budget?: string;
}

export interface CreateTransactionRequest {
  account_id: string;
  category_id?: string;
  amount: string; // Decimal como string
  description: string;
  transaction_date: string;
  destination_account_id?: string;
  reference_number?: string;
  notes?: string;
  tags?: string[];
}

export interface UpdateTransactionRequest {
  account_id?: string;
  category_id?: string;
  amount?: string;
  description?: string;
  transaction_date?: string;
  destination_account_id?: string;
  reference_number?: string;
  notes?: string;
  tags?: string[];
  is_active?: boolean;
}

export interface CreateBudgetDto {
  name: string;
  category_id: string;
  amount: number;
  period: BudgetPeriod;
  start_date: string;
  end_date?: string;
}

export interface UpdateBudgetDto {
  name?: string;
  category_id?: string;
  amount?: number;
  period?: BudgetPeriod;
  start_date?: string;
  end_date?: string;
  is_active?: boolean;
}

// Tipos para importación/exportación YAML
export interface YAMLTransactionItem {
  account_name: string;
  category_name?: string;
  amount: string;
  description: string;
  date: string;
  destination_account_name?: string;
  reference_number?: string;
  notes?: string;
  tags?: string[];
}

export interface YAMLImportRequest {
  transactions: YAMLTransactionItem[];
  dry_run?: boolean;
  create_missing_categories?: boolean;
  default_category_type?: string;
}

export interface ImportValidationError {
  row_index: number;
  field?: string;
  error: string;
  transaction?: any;
}

export interface ImportSummary {
  total_transactions: number;
  successful_imports: number;
  failed_imports: number;
  created_categories?: number;
  errors: ImportValidationError[];
}

export interface YAMLImportResponse {
  success: boolean;
  summary: ImportSummary;
  message: string;
  created_transaction_ids?: string[];
}

export interface YAMLExportRequest {
  account_id?: string;
  category_id?: string;
  start_date?: string;
  end_date?: string;
  include_inactive?: boolean;
  format_amounts?: boolean;
}

export interface YAMLExportResponse {
  yaml_content: string;
  transaction_count: number;
  filename: string;
}