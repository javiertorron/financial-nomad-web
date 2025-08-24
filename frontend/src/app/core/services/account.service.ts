import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { HttpService } from './http.service';
import {
  Account,
  AccountSummary,
  CreateAccountRequest,
  UpdateAccountRequest
} from '../types/financial.types';

@Injectable({
  providedIn: 'root'
})
export class AccountService {
  private readonly baseUrl = '/accounts';

  constructor(private httpService: HttpService) {}

  /**
   * Create a new account
   */
  createAccount(request: CreateAccountRequest): Observable<Account> {
    return this.httpService.post<Account>(this.baseUrl, request).pipe(
      map(response => response.data!)
    );
  }

  /**
   * Get all accounts for the current user
   */
  getAccounts(activeOnly: boolean = false): Observable<AccountSummary[]> {
    const params = activeOnly ? { active_only: 'true' } : {};
    return this.httpService.get<AccountSummary[]>(this.baseUrl, params).pipe(
      map(response => response.data!)
    );
  }

  /**
   * Get a specific account by ID
   */
  getAccount(accountId: string): Observable<Account> {
    return this.httpService.get<Account>(`${this.baseUrl}/${accountId}`).pipe(
      map(response => response.data!)
    );
  }

  /**
   * Update an existing account
   */
  updateAccount(accountId: string, request: UpdateAccountRequest): Observable<Account> {
    return this.httpService.put<Account>(`${this.baseUrl}/${accountId}`, request).pipe(
      map(response => response.data!)
    );
  }

  /**
   * Delete an account (soft delete)
   */
  deleteAccount(accountId: string): Observable<void> {
    return this.httpService.delete<void>(`${this.baseUrl}/${accountId}`).pipe(
      map(response => response.data!)
    );
  }

  /**
   * Get account balance as number
   */
  getAccountBalance(account: Account | AccountSummary): number {
    return parseFloat(account.balance) || 0;
  }

  /**
   * Format account balance for display
   */
  formatBalance(balance: string | number, currency: string = 'EUR'): string {
    const amount = typeof balance === 'string' ? parseFloat(balance) : balance;
    return new Intl.NumberFormat('es-ES', {
      style: 'currency',
      currency: currency
    }).format(amount || 0);
  }

  /**
   * Get account type display name
   */
  getAccountTypeDisplayName(accountType: string): string {
    const typeMap: Record<string, string> = {
      'checking': 'Cuenta Corriente',
      'savings': 'Cuenta de Ahorros',
      'credit_card': 'Tarjeta de Crédito',
      'cash': 'Efectivo',
      'investment': 'Inversión',
      'loan': 'Préstamo',
      'other': 'Otra'
    };
    return typeMap[accountType] || accountType;
  }

  /**
   * Get total balance across all accounts
   */
  getTotalBalance(accounts: (Account | AccountSummary)[]): number {
    return accounts.reduce((total, account) => {
      if (account.is_active) {
        return total + this.getAccountBalance(account);
      }
      return total;
    }, 0);
  }

  /**
   * Filter accounts by type
   */
  filterAccountsByType(accounts: (Account | AccountSummary)[], accountType: string): (Account | AccountSummary)[] {
    return accounts.filter(account => account.account_type === accountType);
  }

  /**
   * Get active accounts only
   */
  getActiveAccounts(accounts: (Account | AccountSummary)[]): (Account | AccountSummary)[] {
    return accounts.filter(account => account.is_active);
  }
}