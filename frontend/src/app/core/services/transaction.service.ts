import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { HttpService } from './http.service';
import {
  Transaction,
  TransactionSummary,
  CreateTransactionRequest,
  UpdateTransactionRequest
} from '../types/financial.types';

@Injectable({
  providedIn: 'root'
})
export class TransactionService {
  private readonly baseUrl = '/transactions';

  constructor(private httpService: HttpService) {}

  /**
   * Create a new transaction
   */
  createTransaction(request: CreateTransactionRequest): Observable<Transaction> {
    return this.httpService.post<Transaction>(this.baseUrl, request).pipe(
      map(response => response.data!)
    );
  }

  /**
   * Get all transactions for the current user with optional filters
   */
  getTransactions(options?: {
    accountId?: string;
    categoryId?: string;
    startDate?: string;
    endDate?: string;
    activeOnly?: boolean;
    limit?: number;
    offset?: number;
  }): Observable<TransactionSummary[]> {
    const params: any = {};
    
    if (options?.accountId) params.account_id = options.accountId;
    if (options?.categoryId) params.category_id = options.categoryId;
    if (options?.startDate) params.start_date = options.startDate;
    if (options?.endDate) params.end_date = options.endDate;
    if (options?.activeOnly) params.active_only = 'true';
    if (options?.limit) params.limit = options.limit.toString();
    if (options?.offset) params.offset = options.offset.toString();

    return this.httpService.get<TransactionSummary[]>(this.baseUrl, params).pipe(
      map(response => response.data!)
    );
  }

  /**
   * Get a specific transaction by ID
   */
  getTransaction(transactionId: string): Observable<Transaction> {
    return this.httpService.get<Transaction>(`${this.baseUrl}/${transactionId}`).pipe(
      map(response => response.data!)
    );
  }

  /**
   * Update an existing transaction
   */
  updateTransaction(transactionId: string, request: UpdateTransactionRequest): Observable<Transaction> {
    return this.httpService.put<Transaction>(`${this.baseUrl}/${transactionId}`, request).pipe(
      map(response => response.data!)
    );
  }

  /**
   * Delete a transaction (soft delete)
   */
  deleteTransaction(transactionId: string): Observable<void> {
    return this.httpService.delete<void>(`${this.baseUrl}/${transactionId}`).pipe(
      map(response => response.data!)
    );
  }

  /**
   * Get transactions for a specific account
   */
  getTransactionsByAccount(accountId: string, options?: {
    startDate?: string;
    endDate?: string;
    activeOnly?: boolean;
    limit?: number;
    offset?: number;
  }): Observable<TransactionSummary[]> {
    return this.getTransactions({ ...options, accountId });
  }

  /**
   * Get transactions for a specific category
   */
  getTransactionsByCategory(categoryId: string, options?: {
    startDate?: string;
    endDate?: string;
    activeOnly?: boolean;
    limit?: number;
    offset?: number;
  }): Observable<TransactionSummary[]> {
    return this.getTransactions({ ...options, categoryId });
  }

  /**
   * Get transactions for a date range
   */
  getTransactionsByDateRange(startDate: string, endDate: string, options?: {
    accountId?: string;
    categoryId?: string;
    activeOnly?: boolean;
    limit?: number;
    offset?: number;
  }): Observable<TransactionSummary[]> {
    return this.getTransactions({ ...options, startDate, endDate });
  }

  /**
   * Get recent transactions
   */
  getRecentTransactions(limit: number = 10): Observable<TransactionSummary[]> {
    return this.getTransactions({ limit, activeOnly: true });
  }

  /**
   * Get transaction amount as number
   */
  getTransactionAmount(transaction: Transaction | TransactionSummary): number {
    return parseFloat(transaction.amount) || 0;
  }

  /**
   * Format transaction amount for display
   */
  formatAmount(amount: string | number, currency: string = 'EUR'): string {
    const value = typeof amount === 'string' ? parseFloat(amount) : amount;
    return new Intl.NumberFormat('es-ES', {
      style: 'currency',
      currency: currency
    }).format(value || 0);
  }

  /**
   * Check if transaction is an expense (negative amount)
   */
  isExpense(transaction: Transaction | TransactionSummary): boolean {
    return this.getTransactionAmount(transaction) < 0;
  }

  /**
   * Check if transaction is income (positive amount)
   */
  isIncome(transaction: Transaction | TransactionSummary): boolean {
    return this.getTransactionAmount(transaction) > 0;
  }

  /**
   * Check if transaction is a transfer
   */
  isTransfer(transaction: Transaction | TransactionSummary): boolean {
    return !!transaction.destination_account_id;
  }

  /**
   * Get absolute amount (always positive)
   */
  getAbsoluteAmount(transaction: Transaction | TransactionSummary): number {
    return Math.abs(this.getTransactionAmount(transaction));
  }

  /**
   * Format transaction date for display
   */
  formatTransactionDate(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleDateString('es-ES', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  }

  /**
   * Format transaction date and time for display
   */
  formatTransactionDateTime(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleString('es-ES', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  /**
   * Get transaction type based on amount and destination account
   */
  getTransactionType(transaction: Transaction | TransactionSummary): 'income' | 'expense' | 'transfer' {
    if (this.isTransfer(transaction)) return 'transfer';
    if (this.isIncome(transaction)) return 'income';
    return 'expense';
  }

  /**
   * Get transaction type display name
   */
  getTransactionTypeDisplayName(transaction: Transaction | TransactionSummary): string {
    const type = this.getTransactionType(transaction);
    const typeMap = {
      'income': 'Ingreso',
      'expense': 'Gasto',
      'transfer': 'Transferencia'
    };
    return typeMap[type];
  }

  /**
   * Calculate total amount for a list of transactions
   */
  getTotalAmount(transactions: (Transaction | TransactionSummary)[]): number {
    return transactions.reduce((total, transaction) => {
      return total + this.getTransactionAmount(transaction);
    }, 0);
  }

  /**
   * Calculate total income from transactions
   */
  getTotalIncome(transactions: (Transaction | TransactionSummary)[]): number {
    return transactions
      .filter(t => this.isIncome(t))
      .reduce((total, transaction) => total + this.getTransactionAmount(transaction), 0);
  }

  /**
   * Calculate total expenses from transactions
   */
  getTotalExpenses(transactions: (Transaction | TransactionSummary)[]): number {
    return Math.abs(transactions
      .filter(t => this.isExpense(t))
      .reduce((total, transaction) => total + this.getTransactionAmount(transaction), 0));
  }

  /**
   * Filter transactions by active status
   */
  getActiveTransactions(transactions: (Transaction | TransactionSummary)[]): (Transaction | TransactionSummary)[] {
    return transactions.filter(transaction => transaction.is_active);
  }
}