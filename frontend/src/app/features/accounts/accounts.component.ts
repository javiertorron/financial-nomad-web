import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { LayoutComponent } from '../../shared/components/layout/layout.component';
import { AccountService } from '../../core/services/account.service';
import { NotificationService } from '../../core/services/notification.service';
import { LoadingService } from '../../core/services/loading.service';
import { 
  AccountSummary, 
  Account,
  CreateAccountRequest, 
  UpdateAccountRequest, 
  AccountType 
} from '../../core/types/financial.types';

@Component({
  selector: 'app-accounts',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, LayoutComponent],
  template: `
    <app-layout>
      <div class="accounts-container">
        <header class="accounts-header">
          <h1>Gestión de Cuentas</h1>
          <button class="btn btn-primary" (click)="showCreateModal = true">
            <i class="fas fa-plus"></i> Nueva Cuenta
          </button>
        </header>

        <!-- Resumen de cuentas -->
        <div class="accounts-summary" *ngIf="accounts.length > 0">
          <div class="summary-card">
            <h3>Balance Total</h3>
            <p class="total-balance">{{ accountService.formatBalance(totalBalance, 'EUR') }}</p>
          </div>
          <div class="summary-card">
            <h3>Cuentas Activas</h3>
            <p class="active-count">{{ activeAccounts.length }}</p>
          </div>
        </div>

        <!-- Lista de cuentas -->
        <div class="accounts-list">
          <div class="account-card" *ngFor="let account of accounts" [class.inactive]="!account.is_active">
            <div class="account-info">
              <div class="account-header">
                <h3>{{ account.name }}</h3>
                <span class="account-type">{{ accountService.getAccountTypeDisplayName(account.account_type) }}</span>
              </div>
              <div class="account-details">
                <p class="balance">{{ accountService.formatBalance(account.balance, account.currency) }}</p>
                <p class="currency">{{ account.currency }}</p>
                <p class="description" *ngIf="account.description">{{ account.description }}</p>
              </div>
            </div>
            <div class="account-actions">
              <button class="btn btn-sm btn-outline" (click)="editAccount(account)">
                <i class="fas fa-edit"></i> Editar
              </button>
              <button class="btn btn-sm btn-danger" (click)="deleteAccount(account)" 
                      *ngIf="account.is_active">
                <i class="fas fa-trash"></i> Eliminar
              </button>
              <button class="btn btn-sm btn-success" (click)="reactivateAccount(account)" 
                      *ngIf="!account.is_active">
                <i class="fas fa-undo"></i> Reactivar
              </button>
            </div>
          </div>

          <div class="empty-state" *ngIf="accounts.length === 0">
            <i class="fas fa-piggy-bank fa-3x"></i>
            <h3>No tienes cuentas registradas</h3>
            <p>Crea tu primera cuenta para comenzar a gestionar tus finanzas</p>
            <button class="btn btn-primary" (click)="showCreateModal = true">
              <i class="fas fa-plus"></i> Crear Primera Cuenta
            </button>
          </div>
        </div>

        <!-- Modal para crear/editar cuenta -->
        <div class="modal" [class.show]="showCreateModal || showEditModal" *ngIf="showCreateModal || showEditModal">
          <div class="modal-content">
            <div class="modal-header">
              <h2>{{ editingAccount ? 'Editar Cuenta' : 'Nueva Cuenta' }}</h2>
              <button class="btn btn-link" (click)="closeModal()">
                <i class="fas fa-times"></i>
              </button>
            </div>
            
            <form [formGroup]="accountForm" (ngSubmit)="saveAccount()">
              <div class="form-group">
                <label for="name">Nombre de la cuenta *</label>
                <input 
                  type="text" 
                  id="name" 
                  formControlName="name" 
                  class="form-control"
                  placeholder="Ej: Cuenta Corriente BBVA">
                <div class="error-message" *ngIf="accountForm.get('name')?.errors && accountForm.get('name')?.touched">
                  El nombre es requerido
                </div>
              </div>

              <div class="form-group">
                <label for="account_type">Tipo de cuenta *</label>
                <select id="account_type" formControlName="account_type" class="form-control">
                  <option value="">Seleccionar tipo</option>
                  <option value="checking">Cuenta Corriente</option>
                  <option value="savings">Cuenta de Ahorros</option>
                  <option value="credit_card">Tarjeta de Crédito</option>
                  <option value="cash">Efectivo</option>
                  <option value="investment">Inversión</option>
                  <option value="loan">Préstamo</option>
                  <option value="other">Otra</option>
                </select>
                <div class="error-message" *ngIf="accountForm.get('account_type')?.errors && accountForm.get('account_type')?.touched">
                  El tipo de cuenta es requerido
                </div>
              </div>

              <div class="form-group">
                <label for="balance">Balance inicial</label>
                <input 
                  type="number" 
                  id="balance" 
                  formControlName="balance" 
                  class="form-control"
                  step="0.01"
                  placeholder="0.00">
              </div>

              <div class="form-group">
                <label for="currency">Moneda</label>
                <select id="currency" formControlName="currency" class="form-control">
                  <option value="EUR">EUR - Euro</option>
                  <option value="USD">USD - Dólar</option>
                  <option value="GBP">GBP - Libra</option>
                </select>
              </div>

              <div class="form-group">
                <label for="description">Descripción</label>
                <textarea 
                  id="description" 
                  formControlName="description" 
                  class="form-control"
                  rows="3"
                  placeholder="Descripción opcional de la cuenta"></textarea>
              </div>

              <div class="form-group">
                <label for="color">Color</label>
                <input 
                  type="color" 
                  id="color" 
                  formControlName="color" 
                  class="form-control">
              </div>

              <div class="modal-actions">
                <button type="button" class="btn btn-secondary" (click)="closeModal()">
                  Cancelar
                </button>
                <button type="submit" class="btn btn-primary" [disabled]="!accountForm.valid || isLoading">
                  {{ editingAccount ? 'Actualizar' : 'Crear' }} Cuenta
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </app-layout>
  `,
  styles: [`
    .accounts-container {
      max-width: 1200px;
      margin: 0 auto;
      padding: 20px;
    }

    .accounts-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 30px;
    }

    .accounts-summary {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 20px;
      margin-bottom: 30px;
    }

    .summary-card {
      background: white;
      padding: 20px;
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
      text-align: center;
    }

    .total-balance {
      font-size: 24px;
      font-weight: bold;
      color: #28a745;
      margin: 0;
    }

    .active-count {
      font-size: 24px;
      font-weight: bold;
      color: #007bff;
      margin: 0;
    }

    .accounts-list {
      display: grid;
      gap: 20px;
    }

    .account-card {
      background: white;
      padding: 20px;
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
      display: flex;
      justify-content: space-between;
      align-items: center;
      transition: opacity 0.3s;
    }

    .account-card.inactive {
      opacity: 0.6;
    }

    .account-info {
      flex: 1;
    }

    .account-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 10px;
    }

    .account-header h3 {
      margin: 0;
      color: #333;
    }

    .account-type {
      background: #e9ecef;
      padding: 4px 8px;
      border-radius: 12px;
      font-size: 12px;
      color: #666;
    }

    .account-details .balance {
      font-size: 18px;
      font-weight: bold;
      margin: 0;
      color: #28a745;
    }

    .account-actions {
      display: flex;
      gap: 10px;
    }

    .empty-state {
      text-align: center;
      padding: 60px 20px;
      color: #666;
    }

    .modal {
      display: none;
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0,0,0,0.5);
      z-index: 1000;
    }

    .modal.show {
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .modal-content {
      background: white;
      padding: 0;
      border-radius: 8px;
      width: 90%;
      max-width: 500px;
      max-height: 90vh;
      overflow-y: auto;
    }

    .modal-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 20px;
      border-bottom: 1px solid #eee;
    }

    .modal-header h2 {
      margin: 0;
    }

    .form-group {
      margin-bottom: 20px;
      padding: 0 20px;
    }

    .form-group label {
      display: block;
      margin-bottom: 5px;
      font-weight: 500;
    }

    .form-control {
      width: 100%;
      padding: 10px;
      border: 1px solid #ddd;
      border-radius: 4px;
      font-size: 14px;
    }

    .error-message {
      color: #dc3545;
      font-size: 12px;
      margin-top: 5px;
    }

    .modal-actions {
      display: flex;
      justify-content: flex-end;
      gap: 10px;
      padding: 20px;
      border-top: 1px solid #eee;
    }

    .btn {
      padding: 8px 16px;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      gap: 5px;
      font-size: 14px;
    }

    .btn-primary {
      background: #007bff;
      color: white;
    }

    .btn-secondary {
      background: #6c757d;
      color: white;
    }

    .btn-danger {
      background: #dc3545;
      color: white;
    }

    .btn-success {
      background: #28a745;
      color: white;
    }

    .btn-outline {
      background: transparent;
      color: #007bff;
      border: 1px solid #007bff;
    }

    .btn:hover {
      opacity: 0.9;
    }

    .btn:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }

    .btn-sm {
      padding: 4px 8px;
      font-size: 12px;
    }
  `]
})
export class AccountsComponent implements OnInit {
  accounts: AccountSummary[] = [];
  activeAccounts: AccountSummary[] = [];
  totalBalance = 0;
  
  showCreateModal = false;
  showEditModal = false;
  editingAccount: AccountSummary | null = null;
  
  accountForm: FormGroup;
  isLoading = false;

  constructor(
    public accountService: AccountService,
    private notificationService: NotificationService,
    private loadingService: LoadingService,
    private fb: FormBuilder
  ) {
    this.accountForm = this.createAccountForm();
  }

  ngOnInit() {
    this.loadAccounts();
  }

  private createAccountForm(): FormGroup {
    return this.fb.group({
      name: ['', [Validators.required, Validators.maxLength(100)]],
      account_type: ['', [Validators.required]],
      balance: [0],
      currency: ['EUR'],
      description: [''],
      color: ['#007bff']
    });
  }

  loadAccounts() {
    this.isLoading = true;
    this.accountService.getAccounts().subscribe({
      next: (accounts) => {
        this.accounts = accounts;
        this.activeAccounts = this.accountService.getActiveAccounts(accounts);
        this.totalBalance = this.accountService.getTotalBalance(this.activeAccounts);
        this.isLoading = false;
      },
      error: (error) => {
        this.notificationService.showError('Error al cargar las cuentas');
        this.isLoading = false;
      }
    });
  }

  editAccount(account: AccountSummary) {
    this.editingAccount = account;
    this.accountForm.patchValue({
      name: account.name,
      account_type: account.account_type,
      balance: account.balance,
      currency: account.currency,
      description: '',
      color: account.color || '#007bff'
    });
    this.showEditModal = true;
  }

  deleteAccount(account: AccountSummary) {
    if (confirm(`¿Estás seguro de que deseas eliminar la cuenta "${account.name}"?`)) {
      this.accountService.deleteAccount(account.id).subscribe({
        next: () => {
          this.notificationService.showSuccess('Cuenta eliminada correctamente');
          this.loadAccounts();
        },
        error: (error) => {
          this.notificationService.showError('Error al eliminar la cuenta');
        }
      });
    }
  }

  reactivateAccount(account: AccountSummary) {
    const updateRequest: UpdateAccountRequest = { is_active: true };
    this.accountService.updateAccount(account.id, updateRequest).subscribe({
      next: () => {
        this.notificationService.showSuccess('Cuenta reactivada correctamente');
        this.loadAccounts();
      },
      error: (error) => {
        this.notificationService.showError('Error al reactivar la cuenta');
      }
    });
  }

  saveAccount() {
    if (this.accountForm.valid) {
      this.isLoading = true;
      const formValue = this.accountForm.value;

      if (this.editingAccount) {
        // Update existing account
        const updateRequest: UpdateAccountRequest = {
          name: formValue.name,
          balance: formValue.balance.toString(),
          description: formValue.description,
          color: formValue.color
        };

        this.accountService.updateAccount(this.editingAccount.id, updateRequest).subscribe({
          next: () => {
            this.notificationService.showSuccess('Cuenta actualizada correctamente');
            this.closeModal();
            this.loadAccounts();
            this.isLoading = false;
          },
          error: (error) => {
            this.notificationService.showError('Error al actualizar la cuenta');
            this.isLoading = false;
          }
        });
      } else {
        // Create new account
        const createRequest: CreateAccountRequest = {
          name: formValue.name,
          account_type: formValue.account_type as AccountType,
          balance: formValue.balance.toString(),
          currency: formValue.currency,
          description: formValue.description,
          color: formValue.color
        };

        this.accountService.createAccount(createRequest).subscribe({
          next: () => {
            this.notificationService.showSuccess('Cuenta creada correctamente');
            this.closeModal();
            this.loadAccounts();
            this.isLoading = false;
          },
          error: (error) => {
            this.notificationService.showError('Error al crear la cuenta');
            this.isLoading = false;
          }
        });
      }
    }
  }

  closeModal() {
    this.showCreateModal = false;
    this.showEditModal = false;
    this.editingAccount = null;
    this.accountForm.reset();
    this.accountForm.patchValue({
      balance: 0,
      currency: 'EUR',
      color: '#007bff'
    });
  }
}