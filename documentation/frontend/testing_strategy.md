# Estrategia de Testing Frontend - Financial Nomad

## Vision General

Este documento define la estrategia completa de testing para el frontend Angular de Financial Nomad, incluyendo unit tests, integration tests, end-to-end tests, y testing de accesibilidad. Se enfoca en garantizar calidad, confiabilidad y mantenibilidad del codigo.

## 1. Piramide de Testing

### 1.1 Distribucion de Tests
- **70% Unit Tests**: Componentes, servicios, pipes, guards aislados
- **20% Integration Tests**: Interaccion entre componentes y servicios  
- **10% E2E Tests**: Flujos criticos de usuario completos

### 1.2 Principios Fundamentales
- **Test First Development**: Escribir tests antes del codigo
- **Single Responsibility**: Un test, una funcionalidad
- **Fast Feedback**: Tests rapidos y deterministas
- **Isolation**: Tests independientes entre si
- **Maintainability**: Tests faciles de mantener y actualizar

## 2. Configuracion del Entorno de Testing

### 2.1 Herramientas Principales

```json
{
  "devDependencies": {
    "@testing-library/angular": "^15.0.0",
    "@testing-library/jest-dom": "^6.1.0",
    "@testing-library/user-event": "^14.5.0",
    "jest": "^29.7.0",
    "jest-preset-angular": "^13.1.0",
    "@types/jest": "^29.5.0",
    "playwright": "^1.40.0",
    "@playwright/test": "^1.40.0",
    "@axe-core/playwright": "^4.8.0",
    "msw": "^2.0.0",
    "fake-indexeddb": "^5.0.0",
    "jest-environment-jsdom": "^29.7.0"
  }
}
```

### 2.2 Configuracion Jest

```javascript
// jest.config.js
module.exports = {
  preset: 'jest-preset-angular',
  setupFilesAfterEnv: ['<rootDir>/src/test-setup.ts'],
  testEnvironment: 'jsdom',
  collectCoverageFrom: [
    'src/app/**/*.ts',
    '!src/app/**/*.d.ts',
    '!src/app/**/*.module.ts',
    '!src/app/**/*.routes.ts',
    '!src/app/**/index.ts',
    '!src/main.ts',
    '!src/polyfills.ts'
  ],
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80
    }
  },
  testMatch: [
    '<rootDir>/src/app/**/*.spec.ts'
  ],
  moduleNameMapping: {
    '^@app/(.*)$': '<rootDir>/src/app/$1',
    '^@shared/(.*)$': '<rootDir>/src/app/shared/$1',
    '^@core/(.*)$': '<rootDir>/src/app/core/$1',
    '^@features/(.*)$': '<rootDir>/src/app/features/$1'
  },
  transformIgnorePatterns: [
    'node_modules/(?!(.*\\.mjs$|@angular|@ngrx))'
  ]
};
```

### 2.3 Test Setup

```typescript
// src/test-setup.ts
import 'jest-preset-angular/setup-jest';
import '@testing-library/jest-dom';
import 'fake-indexeddb/auto';

// Mock global objects
Object.defineProperty(window, 'CSS', { value: null });
Object.defineProperty(window, 'getComputedStyle', {
  value: () => {
    return {
      display: 'none',
      appearance: ['-webkit-appearance']
    };
  }
});

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  unobserve() {}
};

// Suppress Angular animations in tests
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

// Mock Google APIs
(window as any).google = {
  accounts: {
    id: {
      initialize: jest.fn(),
      renderButton: jest.fn(),
      prompt: jest.fn()
    }
  }
};
```

## 3. Unit Testing

### 3.1 Testing de Componentes

#### Componente Simple
```typescript
// transaction-card.component.spec.ts
import { render, screen } from '@testing-library/angular';
import { TransactionCardComponent } from './transaction-card.component';
import { Transaction, TransactionType } from '@shared/models';

describe('TransactionCardComponent', () => {
  const mockTransaction: Transaction = {
    id: '1',
    amount: 50.00,
    description: 'Groceries',
    transaction_type: TransactionType.EXPENSE,
    transaction_date: '2024-01-15',
    account_name: 'Checking',
    category_name: 'Food',
    is_confirmed: true
  };

  it('should display transaction information', async () => {
    await render(TransactionCardComponent, {
      componentInputs: { transaction: mockTransaction }
    });

    expect(screen.getByText('Groceries')).toBeInTheDocument();
    expect(screen.getByText('-€50.00')).toBeInTheDocument();
    expect(screen.getByText('Food')).toBeInTheDocument();
    expect(screen.getByText('Checking')).toBeInTheDocument();
  });

  it('should apply correct CSS class for expense', async () => {
    await render(TransactionCardComponent, {
      componentInputs: { transaction: mockTransaction }
    });

    const amountElement = screen.getByText('-€50.00');
    expect(amountElement).toHaveClass('amount--expense');
  });

  it('should emit edit event when edit button is clicked', async () => {
    const user = userEvent.setup();
    let emittedTransaction: Transaction | undefined;

    await render(TransactionCardComponent, {
      componentInputs: { transaction: mockTransaction },
      componentOutputs: {
        edit: (transaction: Transaction) => emittedTransaction = transaction
      }
    });

    await user.click(screen.getByRole('button', { name: /edit/i }));
    
    expect(emittedTransaction).toEqual(mockTransaction);
  });
});
```

#### Componente con Formulario
```typescript
// transaction-form.component.spec.ts
import { render, screen, fireEvent } from '@testing-library/angular';
import { userEvent } from '@testing-library/user-event';
import { TransactionFormComponent } from './transaction-form.component';
import { ReactiveFormsModule } from '@angular/forms';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

describe('TransactionFormComponent', () => {
  async function renderComponent(inputs: Partial<TransactionFormComponent> = {}) {
    return render(TransactionFormComponent, {
      imports: [ReactiveFormsModule, NoopAnimationsModule],
      componentInputs: inputs
    });
  }

  it('should validate required fields', async () => {
    await renderComponent();
    
    const submitButton = screen.getByRole('button', { name: /save/i });
    expect(submitButton).toBeDisabled();
  });

  it('should enable submit when form is valid', async () => {
    const user = userEvent.setup();
    await renderComponent();

    await user.type(screen.getByLabelText(/amount/i), '100');
    await user.type(screen.getByLabelText(/description/i), 'Test transaction');
    await user.selectOptions(screen.getByLabelText(/category/i), 'food');
    await user.selectOptions(screen.getByLabelText(/account/i), 'checking');

    const submitButton = screen.getByRole('button', { name: /save/i });
    expect(submitButton).toBeEnabled();
  });

  it('should emit save event with form data', async () => {
    const user = userEvent.setup();
    let savedTransaction: any;

    await renderComponent({
      save: (transaction) => savedTransaction = transaction
    });

    await user.type(screen.getByLabelText(/amount/i), '100');
    await user.type(screen.getByLabelText(/description/i), 'Test transaction');
    await user.selectOptions(screen.getByLabelText(/category/i), 'food');
    await user.selectOptions(screen.getByLabelText(/account/i), 'checking');
    await user.click(screen.getByRole('button', { name: /save/i }));

    expect(savedTransaction).toEqual(
      expect.objectContaining({
        amount: 100,
        description: 'Test transaction',
        category_id: 'food',
        account_id: 'checking'
      })
    );
  });

  it('should show validation errors', async () => {
    const user = userEvent.setup();
    await renderComponent();

    const amountInput = screen.getByLabelText(/amount/i);
    await user.type(amountInput, '-50');
    await user.tab();

    expect(screen.getByText(/amount must be positive/i)).toBeInTheDocument();
  });
});
```

### 3.2 Testing de Servicios

#### Servicio HTTP
```typescript
// transaction.service.spec.ts
import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { TransactionService } from './transaction.service';
import { Transaction, CreateTransactionRequest } from '@shared/models';

describe('TransactionService', () => {
  let service: TransactionService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [TransactionService]
    });

    service = TestBed.inject(TransactionService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should fetch transactions', () => {
    const mockTransactions: Transaction[] = [
      { id: '1', amount: 100, description: 'Test' } as Transaction
    ];

    service.getTransactions().subscribe(transactions => {
      expect(transactions).toEqual(mockTransactions);
    });

    const req = httpMock.expectOne('/api/v1/transactions');
    expect(req.request.method).toBe('GET');
    req.flush({ items: mockTransactions });
  });

  it('should create transaction', () => {
    const newTransaction: CreateTransactionRequest = {
      amount: 100,
      description: 'New transaction',
      transaction_type: TransactionType.EXPENSE,
      account_id: 'acc1',
      category_id: 'cat1',
      transaction_date: '2024-01-15'
    };

    const createdTransaction: Transaction = {
      id: '123',
      ...newTransaction
    } as Transaction;

    service.createTransaction(newTransaction).subscribe(transaction => {
      expect(transaction).toEqual(createdTransaction);
    });

    const req = httpMock.expectOne('/api/v1/transactions');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual(newTransaction);
    req.flush(createdTransaction);
  });

  it('should handle HTTP errors', () => {
    service.getTransactions().subscribe({
      next: () => fail('Expected error'),
      error: (error) => {
        expect(error.status).toBe(500);
      }
    });

    const req = httpMock.expectOne('/api/v1/transactions');
    req.flush('Server error', { status: 500, statusText: 'Internal Server Error' });
  });
});
```

#### Servicio con Estado (NgRx Signal Store)
```typescript
// transaction.store.spec.ts
import { TestBed } from '@angular/core/testing';
import { TransactionStore } from './transaction.store';
import { TransactionService } from './transaction.service';
import { of, throwError } from 'rxjs';

describe('TransactionStore', () => {
  let store: InstanceType<typeof TransactionStore>;
  let mockTransactionService: jest.Mocked<TransactionService>;

  beforeEach(() => {
    mockTransactionService = {
      getTransactions: jest.fn(),
      createTransaction: jest.fn(),
      updateTransaction: jest.fn(),
      deleteTransaction: jest.fn()
    } as any;

    TestBed.configureTestingModule({
      providers: [
        TransactionStore,
        { provide: TransactionService, useValue: mockTransactionService }
      ]
    });

    store = TestBed.inject(TransactionStore);
  });

  it('should load transactions successfully', async () => {
    const mockTransactions = [
      { id: '1', amount: 100 } as Transaction,
      { id: '2', amount: 200 } as Transaction
    ];

    mockTransactionService.getTransactions.mockReturnValue(of({ items: mockTransactions }));

    await store.loadTransactions();

    expect(store.transactions()).toEqual(mockTransactions);
    expect(store.loading()).toBe(false);
    expect(store.error()).toBeNull();
  });

  it('should handle loading errors', async () => {
    const error = new Error('Network error');
    mockTransactionService.getTransactions.mockReturnValue(throwError(() => error));

    await store.loadTransactions();

    expect(store.transactions()).toEqual([]);
    expect(store.loading()).toBe(false);
    expect(store.error()).toBe(error);
  });

  it('should filter transactions correctly', () => {
    store.patchState({
      transactions: [
        { id: '1', amount: 100, transaction_type: TransactionType.EXPENSE } as Transaction,
        { id: '2', amount: 200, transaction_type: TransactionType.INCOME } as Transaction
      ],
      filters: { transaction_type: TransactionType.EXPENSE }
    });

    const filtered = store.filteredTransactions();
    expect(filtered).toHaveLength(1);
    expect(filtered[0].transaction_type).toBe(TransactionType.EXPENSE);
  });
});
```

### 3.3 Testing de Guards

```typescript
// auth.guard.spec.ts
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { AuthGuard } from './auth.guard';
import { AuthService } from '@core/auth/auth.service';
import { of } from 'rxjs';

describe('AuthGuard', () => {
  let guard: AuthGuard;
  let mockAuthService: jest.Mocked<AuthService>;
  let mockRouter: jest.Mocked<Router>;

  beforeEach(() => {
    mockAuthService = {
      isAuthenticated$: jest.fn()
    } as any;

    mockRouter = {
      navigate: jest.fn()
    } as any;

    TestBed.configureTestingModule({
      providers: [
        AuthGuard,
        { provide: AuthService, useValue: mockAuthService },
        { provide: Router, useValue: mockRouter }
      ]
    });

    guard = TestBed.inject(AuthGuard);
  });

  it('should allow access when user is authenticated', (done) => {
    mockAuthService.isAuthenticated$.mockReturnValue(of(true));

    guard.canActivate().subscribe(result => {
      expect(result).toBe(true);
      expect(mockRouter.navigate).not.toHaveBeenCalled();
      done();
    });
  });

  it('should redirect to login when user is not authenticated', (done) => {
    mockAuthService.isAuthenticated$.mockReturnValue(of(false));

    guard.canActivate().subscribe(result => {
      expect(result).toBe(false);
      expect(mockRouter.navigate).toHaveBeenCalledWith(['/auth/login']);
      done();
    });
  });
});
```

### 3.4 Testing de Pipes

```typescript
// currency-format.pipe.spec.ts
import { CurrencyFormatPipe } from './currency-format.pipe';

describe('CurrencyFormatPipe', () => {
  let pipe: CurrencyFormatPipe;

  beforeEach(() => {
    pipe = new CurrencyFormatPipe();
  });

  it('should format positive amounts correctly', () => {
    expect(pipe.transform(100.50, 'EUR')).toBe('€100.50');
  });

  it('should format negative amounts correctly', () => {
    expect(pipe.transform(-100.50, 'EUR')).toBe('-€100.50');
  });

  it('should handle zero amounts', () => {
    expect(pipe.transform(0, 'EUR')).toBe('€0.00');
  });

  it('should handle different currencies', () => {
    expect(pipe.transform(100, 'USD')).toBe('$100.00');
  });

  it('should handle null values', () => {
    expect(pipe.transform(null, 'EUR')).toBe('€0.00');
  });
});
```

## 4. Integration Testing

### 4.1 Testing de Feature Modules

```typescript
// transactions.feature.spec.ts
import { render, screen, waitFor } from '@testing-library/angular';
import { userEvent } from '@testing-library/user-event';
import { TransactionsComponent } from './transactions.component';
import { TransactionService } from './services/transaction.service';
import { AccountService } from '@features/accounts/services/account.service';
import { CategoryService } from '@features/categories/services/category.service';
import { of } from 'rxjs';

describe('Transactions Feature', () => {
  const mockTransactionService = {
    getTransactions: jest.fn(),
    createTransaction: jest.fn(),
    updateTransaction: jest.fn(),
    deleteTransaction: jest.fn()
  };

  const mockAccountService = {
    getAccounts: jest.fn()
  };

  const mockCategoryService = {
    getCategories: jest.fn()
  };

  async function renderFeature() {
    return render(TransactionsComponent, {
      providers: [
        { provide: TransactionService, useValue: mockTransactionService },
        { provide: AccountService, useValue: mockAccountService },
        { provide: CategoryService, useValue: mockCategoryService }
      ]
    });
  }

  beforeEach(() => {
    mockTransactionService.getTransactions.mockReturnValue(of({ items: [] }));
    mockAccountService.getAccounts.mockReturnValue(of([]));
    mockCategoryService.getCategories.mockReturnValue(of([]));
  });

  it('should load and display transactions', async () => {
    const mockTransactions = [
      { id: '1', description: 'Groceries', amount: 50 }
    ];
    
    mockTransactionService.getTransactions.mockReturnValue(of({ items: mockTransactions }));

    await renderFeature();

    await waitFor(() => {
      expect(screen.getByText('Groceries')).toBeInTheDocument();
    });
  });

  it('should create new transaction through form', async () => {
    const user = userEvent.setup();
    const mockAccounts = [{ id: 'acc1', name: 'Checking' }];
    const mockCategories = [{ id: 'cat1', name: 'Food' }];

    mockAccountService.getAccounts.mockReturnValue(of(mockAccounts));
    mockCategoryService.getCategories.mockReturnValue(of(mockCategories));
    mockTransactionService.createTransaction.mockReturnValue(of({ id: '123' }));

    await renderFeature();

    // Open form
    await user.click(screen.getByRole('button', { name: /add transaction/i }));

    // Fill form
    await user.type(screen.getByLabelText(/amount/i), '100');
    await user.type(screen.getByLabelText(/description/i), 'New transaction');
    await user.selectOptions(screen.getByLabelText(/account/i), 'acc1');
    await user.selectOptions(screen.getByLabelText(/category/i), 'cat1');

    // Submit
    await user.click(screen.getByRole('button', { name: /save/i }));

    await waitFor(() => {
      expect(mockTransactionService.createTransaction).toHaveBeenCalledWith(
        expect.objectContaining({
          amount: 100,
          description: 'New transaction',
          account_id: 'acc1',
          category_id: 'cat1'
        })
      );
    });
  });

  it('should filter transactions by category', async () => {
    const user = userEvent.setup();
    const mockTransactions = [
      { id: '1', category_name: 'Food', description: 'Groceries' },
      { id: '2', category_name: 'Transport', description: 'Bus ticket' }
    ];

    mockTransactionService.getTransactions.mockReturnValue(of({ items: mockTransactions }));

    await renderFeature();

    // Apply filter
    await user.selectOptions(screen.getByLabelText(/category filter/i), 'Food');

    await waitFor(() => {
      expect(mockTransactionService.getTransactions).toHaveBeenCalledWith(
        expect.objectContaining({
          category_id: 'food'
        })
      );
    });
  });
});
```

### 4.2 Testing de Routing

```typescript
// app-routing.spec.ts
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { Location } from '@angular/common';
import { Component } from '@angular/core';
import { RouterTestingModule } from '@angular/router/testing';
import { AuthGuard } from '@core/guards/auth.guard';

@Component({ template: '' })
class MockComponent {}

describe('App Routing', () => {
  let router: Router;
  let location: Location;
  let mockAuthGuard: jest.Mocked<AuthGuard>;

  beforeEach(async () => {
    mockAuthGuard = {
      canActivate: jest.fn()
    } as any;

    await TestBed.configureTestingModule({
      imports: [RouterTestingModule.withRoutes([
        { path: 'auth/login', component: MockComponent },
        { 
          path: 'app/dashboard', 
          component: MockComponent, 
          canActivate: [AuthGuard] 
        }
      ])],
      providers: [
        { provide: AuthGuard, useValue: mockAuthGuard }
      ]
    }).compileComponents();

    router = TestBed.inject(Router);
    location = TestBed.inject(Location);
  });

  it('should navigate to login', async () => {
    await router.navigate(['/auth/login']);
    expect(location.path()).toBe('/auth/login');
  });

  it('should protect dashboard route', async () => {
    mockAuthGuard.canActivate.mockReturnValue(false);

    await router.navigate(['/app/dashboard']);
    
    expect(mockAuthGuard.canActivate).toHaveBeenCalled();
    // Should redirect to login if guard returns false
  });
});
```

## 5. End-to-End Testing

### 5.1 Configuracion Playwright

```typescript
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['html'],
    ['junit', { outputFile: 'test-results/junit.xml' }]
  ],
  use: {
    baseURL: 'http://localhost:4200',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure'
  },
  projects: [
    {
      name: 'setup',
      testMatch: /.*\.setup\.ts/,
    },
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
      dependencies: ['setup'],
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
      dependencies: ['setup'],
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
      dependencies: ['setup'],
    },
    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 5'] },
      dependencies: ['setup'],
    }
  ],
  webServer: {
    command: 'npm run start',
    url: 'http://localhost:4200',
    reuseExistingServer: !process.env.CI,
  },
});
```

### 5.2 Page Object Model

```typescript
// e2e/pages/login.page.ts
import { Page, Locator, expect } from '@playwright/test';

export class LoginPage {
  readonly page: Page;
  readonly emailInput: Locator;
  readonly passwordInput: Locator;
  readonly loginButton: Locator;
  readonly errorMessage: Locator;

  constructor(page: Page) {
    this.page = page;
    this.emailInput = page.getByTestId('email-input');
    this.passwordInput = page.getByTestId('password-input');
    this.loginButton = page.getByTestId('login-button');
    this.errorMessage = page.getByTestId('error-message');
  }

  async goto() {
    await this.page.goto('/auth/login');
  }

  async login(email: string, password: string) {
    await this.emailInput.fill(email);
    await this.passwordInput.fill(password);
    await this.loginButton.click();
  }

  async expectErrorMessage(message: string) {
    await expect(this.errorMessage).toHaveText(message);
  }
}
```

```typescript
// e2e/pages/dashboard.page.ts
import { Page, Locator } from '@playwright/test';

export class DashboardPage {
  readonly page: Page;
  readonly totalBalance: Locator;
  readonly monthlyIncome: Locator;
  readonly monthlyExpenses: Locator;
  readonly recentTransactions: Locator;
  readonly addTransactionButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.totalBalance = page.getByTestId('total-balance');
    this.monthlyIncome = page.getByTestId('monthly-income');
    this.monthlyExpenses = page.getByTestId('monthly-expenses');
    this.recentTransactions = page.getByTestId('recent-transactions');
    this.addTransactionButton = page.getByTestId('add-transaction-fab');
  }

  async expectToBeVisible() {
    await this.totalBalance.waitFor({ state: 'visible' });
  }

  async getBalance(): Promise<string> {
    return await this.totalBalance.textContent() || '';
  }
}
```

### 5.3 Tests E2E

```typescript
// e2e/auth.spec.ts
import { test, expect } from '@playwright/test';
import { LoginPage } from './pages/login.page';
import { DashboardPage } from './pages/dashboard.page';

test.describe('Authentication', () => {
  let loginPage: LoginPage;
  let dashboardPage: DashboardPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    dashboardPage = new DashboardPage(page);
  });

  test('should login successfully with valid credentials', async ({ page }) => {
    await loginPage.goto();
    await loginPage.login('test@example.com', 'password123');
    
    await dashboardPage.expectToBeVisible();
    expect(page.url()).toContain('/app/dashboard');
  });

  test('should show error with invalid credentials', async ({ page }) => {
    await loginPage.goto();
    await loginPage.login('invalid@example.com', 'wrongpassword');
    
    await loginPage.expectErrorMessage('Invalid credentials');
  });

  test('should redirect to login when accessing protected route without auth', async ({ page }) => {
    await page.goto('/app/dashboard');
    
    expect(page.url()).toContain('/auth/login');
  });
});
```

```typescript
// e2e/transactions.spec.ts
import { test, expect } from '@playwright/test';
import { LoginPage } from './pages/login.page';
import { TransactionsPage } from './pages/transactions.page';

test.describe('Transaction Management', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login('test@example.com', 'password123');
    
    // Navigate to transactions
    const transactionsPage = new TransactionsPage(page);
    await transactionsPage.goto();
  });

  test('should create new transaction', async ({ page }) => {
    const transactionsPage = new TransactionsPage(page);
    
    await transactionsPage.clickAddTransaction();
    await transactionsPage.fillTransactionForm({
      amount: '100.50',
      description: 'Groceries',
      category: 'Food',
      account: 'Checking'
    });
    await transactionsPage.saveTransaction();
    
    await expect(transactionsPage.getTransactionByDescription('Groceries')).toBeVisible();
  });

  test('should edit existing transaction', async ({ page }) => {
    const transactionsPage = new TransactionsPage(page);
    
    // Assume there's already a transaction
    await transactionsPage.editTransaction('Groceries');
    await transactionsPage.updateTransactionDescription('Updated Groceries');
    await transactionsPage.saveTransaction();
    
    await expect(transactionsPage.getTransactionByDescription('Updated Groceries')).toBeVisible();
  });

  test('should filter transactions by category', async ({ page }) => {
    const transactionsPage = new TransactionsPage(page);
    
    await transactionsPage.filterByCategory('Food');
    
    const transactions = await transactionsPage.getAllTransactions();
    for (const transaction of transactions) {
      await expect(transaction.getByText('Food')).toBeVisible();
    }
  });

  test('should import transactions from YAML', async ({ page }) => {
    const transactionsPage = new TransactionsPage(page);
    const yamlContent = `
expenses:
  - amount: 25.50
    description: "Coffee shop"
    category: "Food"
    date: "2024-01-15"
`;
    
    await transactionsPage.clickImportButton();
    await transactionsPage.pasteYamlContent(yamlContent);
    await transactionsPage.confirmImport();
    
    await expect(transactionsPage.getTransactionByDescription('Coffee shop')).toBeVisible();
  });
});
```

### 5.4 Testing de Performance

```typescript
// e2e/performance.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Performance Tests', () => {
  test('should load dashboard within performance budget', async ({ page }) => {
    // Start measuring
    await page.goto('/auth/login');
    
    // Login
    await page.fill('[data-testid="email-input"]', 'test@example.com');
    await page.fill('[data-testid="password-input"]', 'password123');
    
    const startTime = Date.now();
    await page.click('[data-testid="login-button"]');
    
    // Wait for dashboard to load
    await page.waitForSelector('[data-testid="total-balance"]');
    const endTime = Date.now();
    
    const loadTime = endTime - startTime;
    expect(loadTime).toBeLessThan(3000); // 3 seconds max
  });

  test('should handle large transaction lists efficiently', async ({ page }) => {
    await page.goto('/app/transactions');
    
    // Measure time to load 1000+ transactions
    const startTime = Date.now();
    await page.waitForSelector('[data-testid="transaction-list"]');
    const endTime = Date.now();
    
    const loadTime = endTime - startTime;
    expect(loadTime).toBeLessThan(2000); // 2 seconds max for large lists
  });
});
```

## 6. Testing de Accesibilidad

### 6.1 Testing Automatizado con Axe

```typescript
// e2e/accessibility.spec.ts
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe('Accessibility Tests', () => {
  test('should not have accessibility violations on login page', async ({ page }) => {
    await page.goto('/auth/login');
    
    const accessibilityScanResults = await new AxeBuilder({ page }).analyze();
    
    expect(accessibilityScanResults.violations).toEqual([]);
  });

  test('should not have accessibility violations on dashboard', async ({ page }) => {
    // Login first
    await page.goto('/auth/login');
    await page.fill('[data-testid="email-input"]', 'test@example.com');
    await page.fill('[data-testid="password-input"]', 'password123');
    await page.click('[data-testid="login-button"]');
    
    await page.waitForSelector('[data-testid="total-balance"]');
    
    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();
    
    expect(accessibilityScanResults.violations).toEqual([]);
  });

  test('should support keyboard navigation', async ({ page }) => {
    await page.goto('/app/transactions');
    
    // Tab through interactive elements
    await page.keyboard.press('Tab');
    await expect(page.locator(':focus')).toHaveAttribute('data-testid', 'add-transaction-fab');
    
    await page.keyboard.press('Tab');
    await expect(page.locator(':focus')).toHaveAttribute('data-testid', 'filter-button');
  });

  test('should work with screen reader', async ({ page }) => {
    await page.goto('/app/dashboard');
    
    // Check for proper ARIA labels
    const balanceElement = page.getByTestId('total-balance');
    await expect(balanceElement).toHaveAttribute('aria-label', /total balance/i);
    
    // Check for live regions
    const notificationArea = page.getByRole('status');
    await expect(notificationArea).toHaveAttribute('aria-live', 'polite');
  });
});
```

### 6.2 Manual Testing Checklist

```typescript
// accessibility-checklist.md
/*
## Manual Accessibility Testing Checklist

### Keyboard Navigation
- [ ] All interactive elements are reachable via Tab
- [ ] Tab order is logical and follows visual flow
- [ ] Escape key closes modals and dropdowns
- [ ] Arrow keys work in lists and menus
- [ ] Enter/Space activate buttons and links

### Screen Reader Support
- [ ] All images have alt text
- [ ] Form labels are properly associated
- [ ] Headings create logical document structure
- [ ] Live regions announce dynamic content
- [ ] Error messages are announced

### Visual Accessibility
- [ ] Color contrast meets WCAG AA standards (4.5:1)
- [ ] Information isn't conveyed by color alone
- [ ] Text remains readable at 200% zoom
- [ ] Focus indicators are clearly visible
- [ ] Motion respects prefers-reduced-motion

### Mobile Accessibility
- [ ] Touch targets are at least 44px
- [ ] Content reflows properly in landscape
- [ ] Zoom works without horizontal scrolling
- [ ] Voice control navigation works
*/
```

## 7. Mock Services y Test Data

### 7.1 MSW (Mock Service Worker)

```typescript
// src/mocks/handlers.ts
import { rest } from 'msw';
import { mockTransactions, mockAccounts, mockCategories } from './data';

export const handlers = [
  // Auth endpoints
  rest.post('/api/v1/auth/login', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        access_token: 'mock-token',
        user: {
          id: '1',
          email: 'test@example.com',
          name: 'Test User'
        }
      })
    );
  }),

  // Transaction endpoints
  rest.get('/api/v1/transactions', (req, res, ctx) => {
    const page = req.url.searchParams.get('page') || '1';
    const size = req.url.searchParams.get('size') || '10';
    
    return res(
      ctx.status(200),
      ctx.json({
        items: mockTransactions.slice(0, parseInt(size)),
        total: mockTransactions.length,
        page: parseInt(page),
        size: parseInt(size)
      })
    );
  }),

  rest.post('/api/v1/transactions', (req, res, ctx) => {
    const newTransaction = {
      id: Date.now().toString(),
      ...req.body,
      created_at: new Date().toISOString()
    };
    
    return res(
      ctx.status(201),
      ctx.json(newTransaction)
    );
  }),

  // Account endpoints
  rest.get('/api/v1/accounts', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json(mockAccounts)
    );
  }),

  // Category endpoints
  rest.get('/api/v1/categories', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json(mockCategories)
    );
  }),

  // Error simulation
  rest.get('/api/v1/error-simulation', (req, res, ctx) => {
    return res(
      ctx.status(500),
      ctx.json({
        error: {
          code: 'INTERNAL_ERROR',
          message: 'Simulated server error'
        }
      })
    );
  })
];
```

### 7.2 Test Data Factories

```typescript
// src/testing/factories/transaction.factory.ts
import { Factory } from 'fishery';
import { Transaction, TransactionType } from '@shared/models';

export const transactionFactory = Factory.define<Transaction>(() => ({
  id: Math.random().toString(36).substr(2, 9),
  amount: Math.floor(Math.random() * 1000) + 1,
  description: 'Test transaction',
  transaction_type: TransactionType.EXPENSE,
  transaction_date: new Date().toISOString().split('T')[0],
  account_id: 'account-1',
  category_id: 'category-1',
  account_name: 'Test Account',
  category_name: 'Test Category',
  is_confirmed: true,
  user_id: 'user-1',
  tags: [],
  is_reconciled: false,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  is_deleted: false
}));

// Usage examples
export const createMockTransaction = (overrides?: Partial<Transaction>) =>
  transactionFactory.build(overrides);

export const createMockTransactions = (count: number) =>
  transactionFactory.buildList(count);

export const createIncomeTransaction = () =>
  transactionFactory.build({
    transaction_type: TransactionType.INCOME,
    amount: Math.floor(Math.random() * 2000) + 500
  });
```

### 7.3 Custom Test Utilities

```typescript
// src/testing/utils/test-utils.ts
import { render, RenderResult } from '@testing-library/angular';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { ReactiveFormsModule } from '@angular/forms';
import { MatDialogModule } from '@angular/material/dialog';
import { MatSnackBarModule } from '@angular/material/snack-bar';

export function renderWithMaterial<T>(
  component: any,
  options?: any
): Promise<RenderResult<T>> {
  return render(component, {
    imports: [
      NoopAnimationsModule,
      ReactiveFormsModule,
      MatDialogModule,
      MatSnackBarModule,
      ...(options?.imports || [])
    ],
    ...options
  });
}

export function createMockAuthUser() {
  return {
    id: 'user-1',
    email: 'test@example.com',
    name: 'Test User',
    role: 'user',
    status: 'active'
  };
}

export function setupIntersectionObserverMock() {
  const mockIntersectionObserver = jest.fn();
  mockIntersectionObserver.mockReturnValue({
    observe: () => null,
    unobserve: () => null,
    disconnect: () => null
  });
  
  window.IntersectionObserver = mockIntersectionObserver;
}
```

## 8. CI/CD Integration

### 8.1 GitHub Actions Workflow

```yaml
# .github/workflows/frontend-tests.yml
name: Frontend Tests

on:
  push:
    branches: [ main, develop ]
    paths: [ 'frontend/**' ]
  pull_request:
    branches: [ main ]
    paths: [ 'frontend/**' ]

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      
      - name: Install dependencies
        run: npm ci
        working-directory: frontend
      
      - name: Run linting
        run: npm run lint
        working-directory: frontend
      
      - name: Run unit tests
        run: npm run test:ci
        working-directory: frontend
      
      - name: Upload coverage reports
        uses: codecov/codecov-action@v3
        with:
          directory: frontend/coverage
          flags: frontend
          name: frontend-coverage
  
  e2e-tests:
    runs-on: ubuntu-latest
    needs: lint-and-test
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      
      - name: Install dependencies
        run: npm ci
        working-directory: frontend
      
      - name: Install Playwright
        run: npx playwright install --with-deps
        working-directory: frontend
      
      - name: Start backend services
        run: docker-compose up -d backend
      
      - name: Wait for backend
        run: npx wait-on http://localhost:8080/health
        working-directory: frontend
      
      - name: Run E2E tests
        run: npm run e2e:ci
        working-directory: frontend
      
      - name: Upload E2E artifacts
        uses: actions/upload-artifact@v3
        if: failure()
        with:
          name: playwright-report
          path: frontend/playwright-report/
          retention-days: 30
  
  accessibility-tests:
    runs-on: ubuntu-latest
    needs: lint-and-test
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      
      - name: Install dependencies
        run: npm ci
        working-directory: frontend
      
      - name: Run accessibility tests
        run: npm run test:a11y
        working-directory: frontend
      
      - name: Upload accessibility report
        uses: actions/upload-artifact@v3
        with:
          name: accessibility-report
          path: frontend/accessibility-report/
```

### 8.2 Quality Gates

```json
{
  "scripts": {
    "test:ci": "jest --coverage --watchAll=false --ci",
    "test:watch": "jest --watch",
    "e2e:ci": "playwright test",
    "e2e:headed": "playwright test --headed",
    "test:a11y": "playwright test accessibility.spec.ts",
    "lint": "ng lint",
    "lint:fix": "ng lint --fix",
    "test:coverage": "jest --coverage",
    "test:coverage:watch": "jest --coverage --watchAll"
  },
  "jest": {
    "collectCoverageFrom": [
      "src/app/**/*.ts",
      "!src/app/**/*.spec.ts",
      "!src/app/**/*.d.ts"
    ],
    "coverageThreshold": {
      "global": {
        "branches": 80,
        "functions": 80,
        "lines": 80,
        "statements": 80
      }
    }
  }
}
```

## 9. Metricas y Reporting

### 9.1 Test Coverage Reporting

```typescript
// jest.config.coverage.js
module.exports = {
  ...require('./jest.config.js'),
  collectCoverage: true,
  coverageReporters: ['html', 'lcov', 'text-summary', 'json'],
  coverageDirectory: 'coverage',
  coveragePathIgnorePatterns: [
    '/node_modules/',
    '/src/test-setup.ts',
    '/src/mocks/',
    '/src/testing/',
    '/.spec.ts$/',
    '/.mock.ts$/'
  ],
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80
    },
    './src/app/core/': {
      branches: 90,
      functions: 90,
      lines: 90,
      statements: 90
    },
    './src/app/shared/': {
      branches: 85,
      functions: 85,
      lines: 85,
      statements: 85
    }
  }
};
```

### 9.2 Performance Metrics

```typescript
// e2e/utils/performance.ts
import { Page } from '@playwright/test';

export async function measurePagePerformance(page: Page, url: string) {
  await page.goto(url);
  
  const metrics = await page.evaluate(() => {
    const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
    const paint = performance.getEntriesByType('paint');
    
    return {
      // Core Web Vitals
      FCP: paint.find(p => p.name === 'first-contentful-paint')?.startTime,
      LCP: 0, // Measured separately
      
      // Navigation timing
      domContentLoaded: navigation.domContentLoadedEventEnd - navigation.navigationStart,
      loadComplete: navigation.loadEventEnd - navigation.navigationStart,
      
      // Resource timing
      resourceCount: performance.getEntriesByType('resource').length,
      totalResourceSize: performance.getEntriesByType('resource')
        .reduce((total, resource: any) => total + (resource.transferSize || 0), 0)
    };
  });
  
  return metrics;
}
```

## 10. Best Practices y Guidelines

### 10.1 Testing Best Practices

1. **AAA Pattern**: Arrange, Act, Assert
2. **Single Responsibility**: Un test, una funcionalidad
3. **Descriptive Names**: Tests auto-documentados
4. **Independent Tests**: Sin dependencias entre tests
5. **Fast Execution**: Tests rapidos y deterministas

### 10.2 Naming Conventions

```typescript
// Good test names
describe('TransactionService', () => {
  describe('createTransaction', () => {
    it('should create transaction when valid data is provided', () => {});
    it('should throw validation error when amount is negative', () => {});
    it('should call API with correct parameters', () => {});
  });
});

// Bad test names
describe('TransactionService', () => {
  it('test1', () => {});
  it('should work', () => {});
  it('testing creation', () => {});
});
```

### 10.3 Test Organization

```
src/
├── app/
│   ├── features/
│   │   └── transactions/
│   │       ├── components/
│   │       │   ├── transaction-list.component.ts
│   │       │   └── transaction-list.component.spec.ts
│   │       ├── services/
│   │       │   ├── transaction.service.ts
│   │       │   └── transaction.service.spec.ts
│   │       └── transactions.feature.spec.ts
│   └── shared/
│       └── components/
│           ├── date-picker.component.ts
│           └── date-picker.component.spec.ts
├── testing/
│   ├── factories/
│   ├── mocks/
│   └── utils/
└── e2e/
    ├── pages/
    ├── fixtures/
    └── tests/
```

---

## Conclusion

Esta estrategia de testing proporciona una cobertura completa para el frontend de Financial Nomad, asegurando calidad, confiabilidad y mantenibilidad del codigo. La combinacion de unit tests, integration tests y E2E tests, junto con testing de accesibilidad y performance, garantiza una experiencia de usuario robusta y accesible.