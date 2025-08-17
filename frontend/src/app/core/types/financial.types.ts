// Tipos para entidades financieras
export interface Account {
  id: string;
  user_id: string;
  name: string;
  type: AccountType;
  currency: string;
  balance: number;
  initial_balance: number;
  description?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export enum AccountType {
  CHECKING = 'checking',
  SAVINGS = 'savings',
  INVESTMENT = 'investment',
  CREDIT_CARD = 'credit_card',
  LOAN = 'loan',
  CASH = 'cash',
  OTHER = 'other'
}

export interface Category {
  id: string;
  user_id: string;
  name: string;
  type: CategoryType;
  parent_id?: string;
  color: string;
  icon: string;
  description?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  subcategories?: Category[];
}

export enum CategoryType {
  INCOME = 'income',
  EXPENSE = 'expense',
  TRANSFER = 'transfer'
}

export interface Transaction {
  id: string;
  user_id: string;
  account_id: string;
  category_id?: string;
  amount: number;
  type: TransactionType;
  description: string;
  date: string;
  reference?: string;
  tags?: string[];
  from_account_id?: string;
  to_account_id?: string;
  created_at: string;
  updated_at: string;
  account?: Account;
  category?: Category;
}

export enum TransactionType {
  INCOME = 'income',
  EXPENSE = 'expense',
  TRANSFER = 'transfer'
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

// DTOs para crear/actualizar entidades
export interface CreateAccountDto {
  name: string;
  type: AccountType;
  currency: string;
  initial_balance: number;
  description?: string;
}

export interface UpdateAccountDto {
  name?: string;
  type?: AccountType;
  currency?: string;
  description?: string;
  is_active?: boolean;
}

export interface CreateCategoryDto {
  name: string;
  type: CategoryType;
  parent_id?: string;
  color: string;
  icon: string;
  description?: string;
}

export interface UpdateCategoryDto {
  name?: string;
  parent_id?: string;
  color?: string;
  icon?: string;
  description?: string;
  is_active?: boolean;
}

export interface CreateTransactionDto {
  account_id: string;
  category_id?: string;
  amount: number;
  type: TransactionType;
  description: string;
  date: string;
  reference?: string;
  tags?: string[];
  from_account_id?: string;
  to_account_id?: string;
}

export interface UpdateTransactionDto {
  account_id?: string;
  category_id?: string;
  amount?: number;
  description?: string;
  date?: string;
  reference?: string;
  tags?: string[];
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