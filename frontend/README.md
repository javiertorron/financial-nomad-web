# Financial Nomad - Frontend

Frontend de la aplicación Financial Nomad desarrollado con Angular 18+ y Material Design.

## 🚀 Características

- **Angular 18+** con Standalone Components
- **Material Design 3** para UI/UX
- **Google OAuth** para autenticación
- **NgRx Signals** para gestión de estado reactivo
- **PWA** con Service Worker
- **TypeScript** con configuración estricta
- **Testing** con Jest y Playwright
- **ESLint** para linting
- **WCAG 2.2 AA** cumplimiento de accesibilidad

## 📁 Estructura del Proyecto

```
src/
├── app/
│   ├── core/                 # Servicios principales, guards, interceptores
│   │   ├── guards/
│   │   ├── interceptors/
│   │   ├── services/
│   │   └── types/
│   ├── shared/               # Componentes compartidos
│   │   └── components/
│   ├── features/             # Módulos de funcionalidades
│   │   ├── auth/
│   │   ├── dashboard/
│   │   ├── accounts/
│   │   ├── transactions/
│   │   ├── categories/
│   │   ├── budgets/
│   │   ├── reports/
│   │   └── settings/
│   ├── app.component.ts
│   ├── app.config.ts
│   └── app.routes.ts
├── environments/
├── assets/
└── styles.scss
```

## 🛠️ Desarrollo

### Prerequisitos

- Node.js 20+
- npm 10+
- Angular CLI 18+

### Instalación

```bash
# Instalar dependencias
npm install

# Desarrollo local
npm start

# La aplicación estará disponible en http://localhost:4200
```

### Comandos Disponibles

```bash
# Desarrollo
npm start                     # Servidor de desarrollo
npm run build                 # Build de producción
npm run build:dev            # Build de desarrollo
npm run watch                # Build con watch mode

# Testing
npm test                     # Tests unitarios
npm run test:ci              # Tests en modo CI
npm run test:coverage        # Tests con coverage
npm run e2e                  # Tests E2E con Playwright

# Linting y calidad
npm run lint                 # ESLint
npm run analyze              # Análisis del bundle
```

## 🧪 Testing

### Tests Unitarios (Jest)

```bash
# Ejecutar tests
npm test

# Con coverage
npm run test:coverage

# CI mode
npm run test:ci
```

### Tests E2E (Playwright)

```bash
# Instalar navegadores
npx playwright install

# Ejecutar tests E2E
npm run e2e
```

### Coverage

El proyecto mantiene los siguientes umbrales de coverage:
- Statements: 80%
- Branches: 70%
- Functions: 80%
- Lines: 80%

## 🔧 Configuración

### Variables de Entorno

Crea un archivo `.env` basado en `.env.example`:

```bash
cp .env.example .env
```

Configura las siguientes variables:

```env
GOOGLE_CLIENT_ID=tu-google-client-id-aqui
API_URL=http://localhost:8080/api/v1
```

### Google OAuth Setup

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un proyecto o selecciona uno existente
3. Habilita la API de Google Identity
4. Ve a "Credenciales" > "Crear credenciales" > "OAuth 2.0"
5. Añade `http://localhost:4200` a "URIs de redirección autorizados"
6. Copia el Client ID a tu archivo `.env`

## 🏗️ Arquitectura

### Componentes Standalone

Todos los componentes usan la nueva arquitectura standalone de Angular 18:

```typescript
@Component({
  selector: 'app-example',
  standalone: true,
  imports: [CommonModule, MatButtonModule],
  template: `<button mat-button>Ejemplo</button>`
})
export class ExampleComponent {}
```

### Gestión de Estado con Signals

Utilizamos Angular Signals para gestión de estado reactivo:

```typescript
@Injectable()
export class ExampleService {
  private _data = signal<Data[]>([]);
  readonly data = this._data.asReadonly();
  
  updateData(newData: Data[]) {
    this._data.set(newData);
  }
}
```

### Interceptores HTTP

- **AuthInterceptor**: Añade token de autenticación
- **ErrorInterceptor**: Maneja errores globalmente
- **LoadingInterceptor**: Gestiona estado de carga

### Guards

- **authGuard**: Protege rutas que requieren autenticación
- **publicGuard**: Redirige usuarios autenticados desde páginas públicas

## 🎨 Styling

### Material Design

Utiliza Angular Material con tema personalizado:

```scss
$primary-palette: mat.define-palette(mat.$blue-palette, 600);
$accent-palette: mat.define-palette(mat.$green-palette, 500);
```

### Clases Utilitarias

```scss
.w-100 { width: 100%; }
.h-100 { height: 100%; }
.d-flex { display: flex; }
.text-center { text-align: center; }
```

## 📱 PWA

La aplicación está configurada como PWA con:

- Service Worker para cache
- Manifest para instalación
- Estrategias de cache configurables

## ♿ Accesibilidad

- Cumplimiento WCAG 2.2 AA
- Tests de accesibilidad integrados
- Soporte para lectores de pantalla
- Navegación por teclado

## 🚀 Deploy

### Desarrollo Local con Docker

```bash
# Desde la raíz del proyecto
./devops/scripts/dev-start.sh
```

### Build de Producción

```bash
npm run build:prod
```

Los archivos se generan en `dist/financial-nomad-frontend/`.

## 📊 Performance

### Métricas Target

- First Contentful Paint: < 1.5s
- Largest Contentful Paint: < 2.5s
- Cumulative Layout Shift: < 0.1
- First Input Delay: < 100ms

### Optimizaciones

- Lazy loading de módulos
- Tree shaking automático
- Bundle optimization
- Service Worker caching

## 🤝 Contribución

1. Fork del proyecto
2. Crear feature branch (`git checkout -b feature/nueva-caracteristica`)
3. Commit de cambios (`git commit -am 'Añadir nueva característica'`)
4. Push al branch (`git push origin feature/nueva-caracteristica`)
5. Crear Pull Request

## 📄 Licencia

Este proyecto es privado y confidencial.