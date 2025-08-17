# Arquitectura Frontend - Financial Nomad

## Vision General

Este documento define la arquitectura tecnica completa del frontend de Financial Nomad, una aplicacion web Angular para gestion de finanzas personales con integracion a Asana y funcionalidades avanzadas de exportacion y backup.

## 1. Stack Tecnologico

### 1.1 Core Framework
- **Angular 18+** con Standalone Components
- **TypeScript 5.2+** con configuracion estricta
- **Node.js 20 LTS** para desarrollo y build
- **npm 10+** como gestor de paquetes

### 1.2 UI y Estilos
- **Angular Material (M3)** como sistema de diseno base
- **Angular CDK** para primitivos avanzados
- **Tailwind CSS** (opcional) para utilidades adicionales
- **CSS Custom Properties** para temas dinamicos
- **SASS** para estilos complejos y mixins

### 1.3 Estado y Data Management
- **Angular Signals** para estado local reactivo
- **NgRx Signal Store** para estado global complejo
- **RxJS** para operaciones asincronas y streams
- **Angular HttpClient** con interceptores para API

### 1.4 Formularios y Validacion
- **Angular Reactive Forms** con FormBuilder
- **Custom Validators** para reglas de negocio
- **Angular Material Form Fields** para UI consistente
- **Dynamic Forms** para importacion YAML

### 1.5 Internacionalizacion
- **Angular i18n** para multi-idioma (es/en)
- **Date/Number Pipes** localizados
- **Angular Locale** para formatos regionales
- **ICU Message Format** para pluralizacion

### 1.6 Routing y Navegacion
- **Angular Router** con lazy loading
- **Route Guards** para autenticacion y autorizacion
- **Route Resolvers** para pre-carga de datos
- **Route Animations** para transiciones

### 1.7 Progressive Web App
- **Angular Service Worker** para cache estrategico
- **Workbox** para estrategias de cache avanzadas
- **Web App Manifest** para instalacion
- **Push Notifications** (opcional futuro)

### 1.8 Testing
- **Jest** como test runner principal
- **Angular Testing Library** para testing centrado en usuario
- **Playwright** para tests end-to-end
- **MSW (Mock Service Worker)** para mocking de APIs

### 1.9 Build y Optimizacion
- **Angular CLI** con Webpack bajo el capo
- **esbuild** para builds rapidos en desarrollo
- **Terser** para minificacion de produccion
- **Bundle Analyzer** para optimizacion de tamano

## 2. Arquitectura de Componentes

### 2.1 Estructura de Directorios

```
src/
├── app/
│   ├── core/                    # Servicios singleton y configuracion
│   │   ├── auth/               # Autenticacion y guards
│   │   ├── api/                # Servicios HTTP y modelos
│   │   ├── config/             # Configuracion de la app
│   │   ├── interceptors/       # HTTP interceptors
│   │   └── services/           # Servicios core singleton
│   ├── shared/                 # Componentes y servicios reutilizables
│   │   ├── components/         # UI components compartidos
│   │   ├── directives/         # Directivas custom
│   │   ├── pipes/              # Pipes custom
│   │   ├── models/             # Interfaces y tipos TypeScript
│   │   └── utils/              # Funciones de utilidad
│   ├── features/               # Modulos de funcionalidades
│   │   ├── dashboard/          # Dashboard y balance
│   │   ├── transactions/       # Gestion de transacciones
│   │   ├── accounts/           # Gestion de cuentas
│   │   ├── categories/         # Gestion de categorias
│   │   ├── budgets/            # Presupuestos
│   │   ├── reports/            # Reportes y exportacion
│   │   ├── settings/           # Configuracion de usuario
│   │   └── asana/              # Integracion Asana
│   ├── layout/                 # Componentes de layout
│   │   ├── header/             # Barra superior
│   │   ├── sidebar/            # Navegacion lateral
│   │   ├── footer/             # Pie de pagina
│   │   └── shell/              # Shell principal
│   └── auth/                   # Paginas de autenticacion
├── assets/                     # Recursos estaticos
├── environments/               # Configuraciones por entorno
└── styles/                     # Estilos globales y temas
```

### 2.2 Patrones de Componentes

#### Smart Components (Containers)
- Gestionan estado y logica de negocio
- Se comunican con servicios y APIs
- Pasan datos a componentes de presentacion
- Manejan eventos y actualizaciones de estado

#### Dumb Components (Presentational)
- Solo reciben datos via @Input()
- Emiten eventos via @Output()
- Sin dependencias externas
- Reutilizables y testeable aisladamente

#### Service Components
- Componentes que encapsulan logica compleja
- Pueden inyectar servicios
- Se enfocan en funcionalidad especifica
- Ejemplo: DatePickerService, FileUploadService

### 2.3 Sistema de Diseno

#### Tema Base
```typescript
interface AppTheme {
  primary: string;      // #1976d2 (azul corporativo)
  accent: string;       // #ff9800 (naranja de accion)
  success: string;      // #4caf50 (verde para ingresos)
  error: string;        // #f44336 (rojo para gastos)
  warning: string;      // #ff9800 (amarillo alertas)
  surface: string;      // #fafafa (fondos)
  onSurface: string;    // #212121 (texto principal)
}
```

#### Paleta Semantica
- **Ingresos**: Verde (#4caf50) con variaciones
- **Gastos**: Rojo (#f44336) con variaciones  
- **Transferencias**: Azul (#2196f3) con variaciones
- **Neutro**: Grises para elementos no-financieros

#### Componentes Atomicos
- **Buttons**: Primary, Secondary, Text, Icon, FAB
- **Cards**: Basic, Elevated, Outlined
- **Lists**: Simple, Avatar, Two-line, Three-line
- **Forms**: Text fields, Selects, Checkboxes, Radios
- **Navigation**: Tabs, Stepper, Breadcrumbs

## 3. Gestion de Estado

### 3.1 Estrategia de Estado

#### Estado Local (Signals)
```typescript
// Ejemplo: Estado de componente
@Component({...})
export class TransactionFormComponent {
  private readonly transactionSignal = signal<Transaction | null>(null);
  private readonly isLoadingSignal = signal(false);
  private readonly errorsSignal = signal<ValidationErrors>({});
  
  readonly transaction = this.transactionSignal.asReadonly();
  readonly isLoading = this.isLoadingSignal.asReadonly();
  readonly errors = this.errorsSignal.asReadonly();
  
  readonly isValid = computed(() => 
    Object.keys(this.errors()).length === 0
  );
}
```

#### Estado Global (NgRx Signal Store)
```typescript
// Ejemplo: Store de transacciones
export const TransactionStore = signalStore(
  { providedIn: 'root' },
  withState<TransactionState>({
    transactions: [],
    selectedTransaction: null,
    filters: DEFAULT_FILTERS,
    pagination: DEFAULT_PAGINATION,
    loading: false,
    error: null
  }),
  withComputed(({ transactions, filters }) => ({
    filteredTransactions: computed(() => 
      applyFilters(transactions(), filters())
    ),
    totalAmount: computed(() => 
      calculateTotal(transactions())
    )
  })),
  withMethods((store, transactionService = inject(TransactionService)) => ({
    async loadTransactions() {
      patchState(store, { loading: true });
      try {
        const transactions = await transactionService.getAll();
        patchState(store, { transactions, loading: false });
      } catch (error) {
        patchState(store, { error, loading: false });
      }
    }
  }))
);
```

### 3.2 Stores Principales

#### AuthStore
- Usuario actual y estado de autenticacion
- Permisos y roles
- Session management
- Profile y preferencias

#### TransactionStore  
- Lista de transacciones con filtros
- Transaccion seleccionada para edicion
- Estados de loading y error
- Cache y sincronizacion

#### AccountStore
- Cuentas bancarias y metodos de pago
- Balances y movimientos
- Configuraciones de cuenta

#### CategoryStore
- Categorias de ingresos y gastos
- Jerarquia y subcategorias
- Iconos y colores personalizados

#### BudgetStore
- Presupuestos por categoria y periodo
- Progreso y alertas
- Metas de ahorro

## 4. Servicios y APIs

### 4.1 Arquitectura de Servicios

#### HTTP Services
```typescript
@Injectable({ providedIn: 'root' })
export class TransactionService {
  constructor(
    private http: HttpClient,
    private config: ConfigService
  ) {}
  
  getTransactions(filters?: TransactionFilters): Observable<Transaction[]> {
    const params = this.buildParams(filters);
    return this.http.get<Transaction[]>(`${this.apiUrl}/transactions`, { params })
      .pipe(
        retry(3),
        catchError(this.handleError)
      );
  }
  
  createTransaction(transaction: CreateTransactionDto): Observable<Transaction> {
    return this.http.post<Transaction>(`${this.apiUrl}/transactions`, transaction)
      .pipe(
        tap(() => this.invalidateCache()),
        catchError(this.handleError)
      );
  }
}
```

#### Cache Strategy
```typescript
@Injectable({ providedIn: 'root' })
export class CacheService {
  private cache = new Map<string, { data: any; timestamp: number }>();
  private readonly TTL = 5 * 60 * 1000; // 5 minutos
  
  get<T>(key: string): T | null {
    const cached = this.cache.get(key);
    if (!cached) return null;
    
    if (Date.now() - cached.timestamp > this.TTL) {
      this.cache.delete(key);
      return null;
    }
    
    return cached.data;
  }
  
  set<T>(key: string, data: T): void {
    this.cache.set(key, { data, timestamp: Date.now() });
  }
}
```

### 4.2 Interceptores HTTP

#### AuthInterceptor
- Inyecta tokens de autenticacion
- Maneja renovacion automatica
- Redirige en caso de 401/403

#### ErrorInterceptor  
- Captura errores HTTP globalmente
- Muestra notificaciones de error
- Registra errores para debugging

#### LoadingInterceptor
- Muestra indicadores de carga
- Gestiona estados de loading globales
- Timeout para requests largos

#### CacheInterceptor
- Implementa cache HTTP inteligente
- Respeta headers de cache
- Invalidacion selectiva

## 5. Routing y Navegacion

### 5.1 Estructura de Rutas

```typescript
const routes: Routes = [
  {
    path: '',
    redirectTo: '/auth/login',
    pathMatch: 'full'
  },
  {
    path: 'auth',
    loadChildren: () => import('./auth/auth.routes').then(m => m.AUTH_ROUTES),
    canActivate: [GuestGuard]
  },
  {
    path: 'app',
    component: ShellComponent,
    canActivate: [AuthGuard],
    children: [
      {
        path: '',
        redirectTo: 'dashboard',
        pathMatch: 'full'
      },
      {
        path: 'dashboard',
        loadComponent: () => import('./features/dashboard/dashboard.component').then(m => m.DashboardComponent),
        title: 'Dashboard'
      },
      {
        path: 'transactions',
        loadChildren: () => import('./features/transactions/transactions.routes').then(m => m.TRANSACTION_ROUTES),
        title: 'Transacciones'
      },
      {
        path: 'accounts',
        loadChildren: () => import('./features/accounts/accounts.routes').then(m => m.ACCOUNT_ROUTES),
        title: 'Cuentas'
      },
      {
        path: 'categories',
        loadChildren: () => import('./features/categories/categories.routes').then(m => m.CATEGORY_ROUTES),
        title: 'Categorias'
      },
      {
        path: 'budgets',
        loadChildren: () => import('./features/budgets/budgets.routes').then(m => m.BUDGET_ROUTES),
        title: 'Presupuestos'
      },
      {
        path: 'reports',
        loadChildren: () => import('./features/reports/reports.routes').then(m => m.REPORT_ROUTES),
        title: 'Reportes'
      },
      {
        path: 'settings',
        loadChildren: () => import('./features/settings/settings.routes').then(m => m.SETTING_ROUTES),
        title: 'Configuracion'
      }
    ]
  },
  {
    path: '**',
    loadComponent: () => import('./shared/components/not-found/not-found.component').then(m => m.NotFoundComponent)
  }
];
```

### 5.2 Guards y Resolvers

#### AuthGuard
```typescript
@Injectable({ providedIn: 'root' })
export class AuthGuard implements CanActivate {
  constructor(
    private authService: AuthService,
    private router: Router
  ) {}
  
  canActivate(): Observable<boolean> {
    return this.authService.isAuthenticated$.pipe(
      tap(isAuth => {
        if (!isAuth) {
          this.router.navigate(['/auth/login']);
        }
      })
    );
  }
}
```

#### DataResolver
```typescript
@Injectable({ providedIn: 'root' })
export class TransactionResolver implements Resolve<Transaction[]> {
  constructor(private transactionService: TransactionService) {}
  
  resolve(): Observable<Transaction[]> {
    return this.transactionService.getTransactions().pipe(
      catchError(() => of([]))
    );
  }
}
```

## 6. Formularios y Validacion

### 6.1 Estrategia de Formularios

#### Reactive Forms con Tipado Fuerte
```typescript
interface TransactionForm {
  amount: FormControl<number>;
  description: FormControl<string>;
  categoryId: FormControl<string>;
  accountId: FormControl<string>;
  date: FormControl<Date>;
  type: FormControl<TransactionType>;
}

@Component({...})
export class TransactionFormComponent {
  private fb = inject(FormBuilder);
  
  transactionForm = this.fb.group<TransactionForm>({
    amount: this.fb.control(0, [Validators.required, Validators.min(0.01)]),
    description: this.fb.control('', [Validators.required, Validators.maxLength(200)]),
    categoryId: this.fb.control('', [Validators.required]),
    accountId: this.fb.control('', [Validators.required]),
    date: this.fb.control(new Date(), [Validators.required]),
    type: this.fb.control(TransactionType.EXPENSE, [Validators.required])
  });
}
```

#### Custom Validators
```typescript
export class FinancialValidators {
  static positiveAmount(control: AbstractControl): ValidationErrors | null {
    const value = control.value;
    return value > 0 ? null : { positiveAmount: true };
  }
  
  static validCategory(categories: Category[]) {
    return (control: AbstractControl): ValidationErrors | null => {
      const categoryId = control.value;
      const exists = categories.some(cat => cat.id === categoryId);
      return exists ? null : { invalidCategory: true };
    };
  }
  
  static futureDate(control: AbstractControl): ValidationErrors | null {
    const date = new Date(control.value);
    const today = new Date();
    return date <= today ? null : { futureDate: true };
  }
}
```

### 6.2 Formularios Dinamicos

#### YAML Import Form
```typescript
@Component({...})
export class YamlImportComponent {
  importForm = this.fb.group({
    yamlContent: ['', [Validators.required, this.yamlValidator]],
    dateFormat: ['DD/MM/YYYY', [Validators.required]],
    defaultAccount: ['', [Validators.required]]
  });
  
  private yamlValidator(control: AbstractControl): ValidationErrors | null {
    try {
      yaml.parse(control.value);
      return null;
    } catch (error) {
      return { invalidYaml: { message: error.message } };
    }
  }
}
```

## 7. Progressive Web App (PWA)

### 7.1 Service Worker Strategy

#### Cache Strategy
```typescript
// ngsw-config.json
{
  "index": "/index.html",
  "assetGroups": [
    {
      "name": "app",
      "installMode": "prefetch",
      "resources": {
        "files": ["/favicon.ico", "/index.html", "/*.css", "/*.js"]
      }
    },
    {
      "name": "assets",
      "installMode": "lazy",
      "updateMode": "prefetch",
      "resources": {
        "files": ["/assets/**", "/*.(eot|svg|cur|jpg|png|webp|gif|otf|ttf|woff|woff2|ani)"]
      }
    }
  ],
  "dataGroups": [
    {
      "name": "api-performance",
      "urls": ["/api/transactions", "/api/accounts", "/api/categories"],
      "cacheConfig": {
        "strategy": "performance",
        "maxSize": 100,
        "maxAge": "1d"
      }
    },
    {
      "name": "api-freshness",
      "urls": ["/api/auth/**", "/api/user/**"],
      "cacheConfig": {
        "strategy": "freshness",
        "maxAge": "5m"
      }
    }
  ]
}
```

#### Update Management
```typescript
@Injectable({ providedIn: 'root' })
export class UpdateService {
  constructor(private swUpdate: SwUpdate) {
    if (swUpdate.isEnabled) {
      this.checkForUpdates();
    }
  }
  
  private checkForUpdates() {
    this.swUpdate.available.subscribe(() => {
      if (confirm('Nueva version disponible. ¿Recargar?')) {
        window.location.reload();
      }
    });
  }
}
```

### 7.2 Offline Support

#### Offline Indicator
```typescript
@Injectable({ providedIn: 'root' })
export class ConnectionService {
  private onlineSignal = signal(navigator.onLine);
  
  readonly isOnline = this.onlineSignal.asReadonly();
  readonly isOffline = computed(() => !this.isOnline());
  
  constructor() {
    window.addEventListener('online', () => this.onlineSignal.set(true));
    window.addEventListener('offline', () => this.onlineSignal.set(false));
  }
}
```

## 8. Testing Strategy

### 8.1 Unit Testing

#### Component Testing
```typescript
describe('TransactionListComponent', () => {
  let component: TransactionListComponent;
  let fixture: ComponentFixture<TransactionListComponent>;
  let mockTransactionService: jest.Mocked<TransactionService>;
  
  beforeEach(async () => {
    const transactionServiceSpy = createMock<TransactionService>();
    
    await TestBed.configureTestingModule({
      imports: [TransactionListComponent],
      providers: [
        { provide: TransactionService, useValue: transactionServiceSpy }
      ]
    }).compileComponents();
    
    mockTransactionService = TestBed.inject(TransactionService) as jest.Mocked<TransactionService>;
  });
  
  it('should load transactions on init', async () => {
    const mockTransactions = createMockTransactions();
    mockTransactionService.getTransactions.mockReturnValue(of(mockTransactions));
    
    component.ngOnInit();
    
    expect(mockTransactionService.getTransactions).toHaveBeenCalled();
    expect(component.transactions()).toEqual(mockTransactions);
  });
});
```

#### Service Testing
```typescript
describe('TransactionService', () => {
  let service: TransactionService;
  let httpMock: HttpTestingController;
  
  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule]
    });
    
    service = TestBed.inject(TransactionService);
    httpMock = TestBed.inject(HttpTestingController);
  });
  
  it('should create transaction', () => {
    const mockTransaction = createMockTransaction();
    
    service.createTransaction(mockTransaction).subscribe(transaction => {
      expect(transaction).toEqual(mockTransaction);
    });
    
    const req = httpMock.expectOne('/api/transactions');
    expect(req.request.method).toBe('POST');
    req.flush(mockTransaction);
  });
});
```

### 8.2 Integration Testing

#### Feature Testing with Angular Testing Library
```typescript
import { render, screen, userEvent } from '@testing-library/angular';

describe('Transaction Feature', () => {
  it('should create transaction when form is submitted', async () => {
    const mockTransactionService = createMock<TransactionService>();
    
    await render(TransactionFormComponent, {
      providers: [
        { provide: TransactionService, useValue: mockTransactionService }
      ]
    });
    
    const user = userEvent.setup();
    
    await user.type(screen.getByLabelText(/amount/i), '100');
    await user.type(screen.getByLabelText(/description/i), 'Test transaction');
    await user.selectOptions(screen.getByLabelText(/category/i), 'food');
    await user.click(screen.getByRole('button', { name: /save/i }));
    
    expect(mockTransactionService.createTransaction).toHaveBeenCalledWith(
      expect.objectContaining({
        amount: 100,
        description: 'Test transaction',
        categoryId: 'food'
      })
    );
  });
});
```

### 8.3 E2E Testing

#### Playwright Configuration
```typescript
// playwright.config.ts
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:4200',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
  ],
  webServer: {
    command: 'npm run start',
    url: 'http://localhost:4200',
    reuseExistingServer: !process.env.CI,
  },
});
```

#### E2E Test Example
```typescript
import { test, expect } from '@playwright/test';

test.describe('Transaction Management', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/auth/login');
    await page.fill('[data-testid="email"]', 'test@example.com');
    await page.fill('[data-testid="password"]', 'password');
    await page.click('[data-testid="login-button"]');
    await expect(page).toHaveURL('/app/dashboard');
  });
  
  test('should create new transaction', async ({ page }) => {
    await page.click('[data-testid="add-transaction-fab"]');
    await page.fill('[data-testid="amount-input"]', '50.00');
    await page.fill('[data-testid="description-input"]', 'Groceries');
    await page.selectOption('[data-testid="category-select"]', 'food');
    await page.click('[data-testid="save-button"]');
    
    await expect(page.locator('[data-testid="success-message"]')).toBeVisible();
    await expect(page.locator('[data-testid="transaction-list"]')).toContainText('Groceries');
  });
});
```

## 9. Performance y Optimizacion

### 9.1 Estrategias de Optimizacion

#### Lazy Loading
- Modulos cargados bajo demanda
- Componentes standalone con lazy loading
- Imagenes con lazy loading nativo
- Datos paginados con virtual scrolling

#### Change Detection
```typescript
@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `...`
})
export class OptimizedComponent {
  // Usar signals para minimizar change detection
  private dataSignal = signal<Data[]>([]);
  readonly data = this.dataSignal.asReadonly();
  
  // Memoized computations
  readonly filteredData = computed(() => 
    this.data().filter(item => item.active)
  );
}
```

#### Bundle Optimization
```typescript
// webpack.config.js (custom)
module.exports = {
  optimization: {
    splitChunks: {
      chunks: 'all',
      cacheGroups: {
        vendor: {
          test: /[\\/]node_modules[\\/]/,
          name: 'vendors',
          chunks: 'all',
        },
        common: {
          name: 'common',
          minChunks: 2,
          chunks: 'all',
          enforce: true
        }
      }
    }
  }
};
```

### 9.2 Monitoring y Metricas

#### Core Web Vitals
```typescript
@Injectable({ providedIn: 'root' })
export class PerformanceService {
  constructor() {
    this.observeWebVitals();
  }
  
  private observeWebVitals() {
    // LCP - Largest Contentful Paint
    new PerformanceObserver((list) => {
      const entries = list.getEntries();
      const lcp = entries[entries.length - 1];
      console.log('LCP:', lcp.startTime);
    }).observe({ entryTypes: ['largest-contentful-paint'] });
    
    // FID - First Input Delay
    new PerformanceObserver((list) => {
      const entries = list.getEntries();
      entries.forEach(entry => {
        console.log('FID:', entry.processingStart - entry.startTime);
      });
    }).observe({ entryTypes: ['first-input'] });
  }
}
```

## 10. Accesibilidad (WCAG 2.2 AA)

### 10.1 Implementacion de Accesibilidad

#### Angular CDK A11y
```typescript
@Component({
  template: `
    <div class="form-field">
      <label 
        [id]="labelId"
        [for]="inputId"
        [attr.aria-required]="required">
        {{ label }}
      </label>
      <input
        [id]="inputId"
        [attr.aria-labelledby]="labelId"
        [attr.aria-describedby]="errorId"
        [attr.aria-invalid]="hasError"
        cdkTrapFocus
        cdkMonitorElementFocus>
      <div 
        [id]="errorId" 
        *ngIf="hasError" 
        aria-live="polite">
        {{ errorMessage }}
      </div>
    </div>
  `
})
export class AccessibleInputComponent {
  @Input() label!: string;
  @Input() required = false;
  
  labelId = `label-${Math.random().toString(36).substr(2, 9)}`;
  inputId = `input-${Math.random().toString(36).substr(2, 9)}`;
  errorId = `error-${Math.random().toString(36).substr(2, 9)}`;
}
```

#### Keyboard Navigation
```typescript
@Directive({
  selector: '[appKeyboardNav]'
})
export class KeyboardNavDirective {
  @HostListener('keydown', ['$event'])
  onKeyDown(event: KeyboardEvent) {
    switch (event.key) {
      case 'ArrowDown':
        this.focusNext();
        event.preventDefault();
        break;
      case 'ArrowUp':
        this.focusPrevious();
        event.preventDefault();
        break;
      case 'Home':
        this.focusFirst();
        event.preventDefault();
        break;
      case 'End':
        this.focusLast();
        event.preventDefault();
        break;
    }
  }
}
```

### 10.2 Testing de Accesibilidad

#### Axe Integration
```typescript
import { axe, toHaveNoViolations } from 'jest-axe';

expect.extend(toHaveNoViolations);

describe('Accessibility', () => {
  it('should not have accessibility violations', async () => {
    const { container } = await render(TransactionListComponent);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
```

## 11. Seguridad Frontend

### 11.1 Content Security Policy
```html
<meta http-equiv="Content-Security-Policy" 
      content="default-src 'self'; 
               script-src 'self' 'nonce-{random}';
               style-src 'self' 'unsafe-inline' fonts.googleapis.com;
               font-src 'self' fonts.gstatic.com;
               img-src 'self' data: https:;
               connect-src 'self' *.googleapis.com;">
```

### 11.2 XSS Protection
```typescript
import { DomSanitizer } from '@angular/platform-browser';

@Injectable({ providedIn: 'root' })
export class SanitizationService {
  constructor(private sanitizer: DomSanitizer) {}
  
  sanitizeHtml(html: string): SafeHtml {
    return this.sanitizer.sanitize(SecurityContext.HTML, html) || '';
  }
  
  sanitizeUrl(url: string): SafeUrl {
    return this.sanitizer.sanitize(SecurityContext.URL, url) || '';
  }
}
```

### 11.3 Token Management
```typescript
@Injectable({ providedIn: 'root' })
export class TokenService {
  private readonly TOKEN_KEY = 'auth_token';
  
  setToken(token: string): void {
    // Almacenar en httpOnly cookie via backend
    // No almacenar en localStorage por seguridad
    this.cookieService.set(this.TOKEN_KEY, token, {
      httpOnly: true,
      secure: true,
      sameSite: 'Strict'
    });
  }
  
  getToken(): string | null {
    // Token se envia automaticamente en cookies httpOnly
    return null; // No accesible desde JavaScript
  }
}
```

## 12. Build y Deployment

### 12.1 Configuracion de Build

#### Angular CLI Configuration
```json
{
  "projects": {
    "financial-nomad": {
      "architect": {
        "build": {
          "builder": "@angular-devkit/build-angular:browser",
          "options": {
            "outputPath": "dist/financial-nomad",
            "index": "src/index.html",
            "main": "src/main.ts",
            "polyfills": "src/polyfills.ts",
            "tsConfig": "tsconfig.app.json",
            "assets": [
              "src/favicon.ico",
              "src/assets",
              "src/manifest.json"
            ],
            "styles": [
              "@angular/material/prebuilt-themes/indigo-pink.css",
              "src/styles.scss"
            ],
            "scripts": [],
            "budgets": [
              {
                "type": "initial",
                "maximumWarning": "500kb",
                "maximumError": "1mb"
              },
              {
                "type": "anyComponentStyle",
                "maximumWarning": "2kb",
                "maximumError": "4kb"
              }
            ]
          },
          "configurations": {
            "production": {
              "budgets": [
                {
                  "type": "initial",
                  "maximumWarning": "500kb",
                  "maximumError": "1mb"
                }
              ],
              "fileReplacements": [
                {
                  "replace": "src/environments/environment.ts",
                  "with": "src/environments/environment.prod.ts"
                }
              ],
              "outputHashing": "all",
              "sourceMap": false,
              "namedChunks": false,
              "extractLicenses": true,
              "vendorChunk": false,
              "buildOptimizer": true,
              "serviceWorker": true,
              "ngswConfigPath": "ngsw-config.json"
            }
          }
        }
      }
    }
  }
}
```

### 12.2 CI/CD Pipeline

#### GitHub Actions
```yaml
name: Build and Deploy Frontend
on:
  push:
    branches: [ main ]
    paths: [ 'frontend/**' ]
  pull_request:
    branches: [ main ]
    paths: [ 'frontend/**' ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
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
      
      - name: Run e2e tests
        run: npm run e2e:ci
        working-directory: frontend
        
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          directory: frontend/coverage
  
  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      
      - name: Install dependencies
        run: npm ci
        working-directory: frontend
      
      - name: Build application
        run: npm run build:prod
        working-directory: frontend
        env:
          API_URL: ${{ secrets.API_URL }}
          GOOGLE_CLIENT_ID: ${{ secrets.GOOGLE_CLIENT_ID }}
      
      - name: Deploy to Firebase Hosting
        uses: FirebaseExtended/action-hosting-deploy@v0
        with:
          repoToken: '${{ secrets.GITHUB_TOKEN }}'
          firebaseServiceAccount: '${{ secrets.FIREBASE_SERVICE_ACCOUNT }}'
          channelId: live
          projectId: financial-nomad-prod
          entryPoint: frontend
```

### 12.3 Environment Configuration

#### Environment Files
```typescript
// environment.ts
export const environment = {
  production: false,
  apiUrl: 'http://localhost:8080/api/v1',
  googleClientId: 'your-google-client-id',
  firebaseConfig: {
    apiKey: 'your-api-key',
    authDomain: 'financial-nomad-dev.firebaseapp.com',
    projectId: 'financial-nomad-dev',
    storageBucket: 'financial-nomad-dev.appspot.com',
    messagingSenderId: '123456789',
    appId: 'your-app-id'
  },
  features: {
    asanaIntegration: true,
    offlineMode: true,
    debugMode: true
  }
};

// environment.prod.ts
export const environment = {
  production: true,
  apiUrl: 'https://api.financial-nomad.com/api/v1',
  googleClientId: process.env['GOOGLE_CLIENT_ID'],
  firebaseConfig: {
    apiKey: process.env['FIREBASE_API_KEY'],
    authDomain: 'financial-nomad-prod.firebaseapp.com',
    projectId: 'financial-nomad-prod',
    storageBucket: 'financial-nomad-prod.appspot.com',
    messagingSenderId: process.env['FIREBASE_MESSAGING_SENDER_ID'],
    appId: process.env['FIREBASE_APP_ID']
  },
  features: {
    asanaIntegration: true,
    offlineMode: true,
    debugMode: false
  }
};
```

---

## Conclusiones

Esta arquitectura frontend proporciona una base solida y escalable para Financial Nomad, implementando las mejores practicas de Angular moderno, accesibilidad, performance y seguridad. La estructura modular permite un desarrollo eficiente y mantenimiento a largo plazo, mientras que las estrategias de testing aseguran la calidad del codigo.

La integracion con PWA permite funcionalidad offline limitada, y la arquitectura de estado con Signals y NgRx Signal Store proporciona una gestion reactiva y eficiente del estado de la aplicacion.