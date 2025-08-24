# Documentación Funcional Completa (Web): Financial Nomad

> **Conversión desde versión Android nativa → versión Web (Angular + FastAPI + Firestore + GCP).**  
> Esta especificación adapta la documentación original para Android a una arquitectura web moderna con autenticación Google OAuth, registro por invitación, backups en Google Drive, integración con Asana y generación de documentos para LLMs. La estructura, UX y alcance se han mantenido cuando aporta valor y se han sustituido componentes móviles por equivalentes web. (Basado en la doc original de Android aportada por el usuario).

## 1. Visión general del producto (Web)

**Financial Nomad (Web)** es una aplicación de finanzas personales centrada en la privacidad y la claridad visual, con **front-end Angular** y **backend Python (FastAPI)**. Los datos se almacenan en **Firestore** y se protegen con reglas de seguridad por usuario. El sistema soporta **registro por invitación**, **OAuth con Google**, **exportes para LLMs**, **backups automáticos a Google Drive** y **sincronización con Asana** para flujos de trabajo.

- **Tipo:** Web app responsive (desktop-first con soporte móvil/tablet) + **PWA** opcional para capacidades offline limitadas (caché de assets y lectura de últimos datos).  
- **Diseño:** Angular Material (M3) + Tailwind opcional; sistema de color sobrio con semántica financiera (ingresos/verde, gastos/rojo).  
- **Objetivo:** Gestión de balance, transacciones, categorías, presupuestos y exportes analíticos, con foco en rendimiento y DX para “vibe coding” con IA.

## 2. Arquitectura técnica

### 2.1 Capas y tecnologías
- **Frontend (Angular 18+)**  
  - Standalone Components, Signals/Signal Store o NgRx para estado global.  
  - Angular Material (M3), CDK, formularios reactivos, i18n (es/en).  
  - Ruteo con lazy loading, guards de **auth** e **invitation**.  
  - Gráficos (Recharts/ngx-charts) y accesibilidad **WCAG 2.2 AA**.  
  - PWA (Workbox) opcional para cache estática y lectura de últimos snapshots.
- **Backend (Python, FastAPI)**  
  - OpenAPI/Swagger nativo; validación con Pydantic v2.  
  - Endpoints mínimos: auth session, invites, cuentas, transacciones, categorías, presupuestos, exports LLM, tareas Asana, backups.  
  - Tareas en background (FastAPI BackgroundTasks o Cloud Tasks/Workflows).  
- **Datos (Firestore, modo nativo)**  
  - Colecciones por `uid` y agregados para analytics.  
  - **Reglas de seguridad**: acceso por `request.auth.uid` y pertenencia a invitación aceptada.  
  - Índices compuestos (fecha+categoría, cuenta+fecha).
- **Infra GCP (free tier-friendly)**  
  - Hosting: Firebase Hosting (frontend).  
  - Backend: Cloud Run.  
  - Orquestación: Cloud Scheduler + Cloud Functions/Run para jobs (backups/Drive, sync Asana).  
  - Secret Manager + KMS para credenciales.  
- **Integraciones**  
  - **Autenticación básica** (email/password con bcrypt) + registro **por invitación** (código firmado).  
  - **Asana API** (OAuth, webhooks) y SDK Python.  
  - **Drive API** para replicar backups de Firestore exportados a GCS.

### 2.2 Modelo de datos (Firestore)
- `users/{uid}`: email, password_hash, perfil, preferencias, flags (onboarding, consent), role (admin/user).  
- `invites/{code}`: email, issuedBy, expiresAt, consumedBy.  
- `accounts/{uid}/bank_accounts/{id}`  
- `accounts/{uid}/categories/{id}`  
- `accounts/{uid}/transactions/{id}` (monto, fecha, cuenta, categoría, notas, adjuntos)  
- `accounts/{uid}/budgets/{id}` (periodicidad, límites)  
- `integrations/{uid}/asana` (tokens cifrados, mappings)  
- `reports/{uid}/{reportId}` (metadatos de exportes LLM)

> **Racional:** se conserva la estructura funcional del documento Android (cuentas, categorías, movimientos, presupuestos), sustituyendo la persistencia local por Firestore con seguridad serverless.

## 3. Identidad, acceso y registro por invitación

- **Flujo de registro:** Email/password + código de invitación → validar invitación → hash password (bcrypt) → crear usuario en Firestore.  
- **Flujo de login:** Email/password → verificar hash → generar JWT → sesión del backend (cookie httpOnly + CSRF).  
- **Flujo de invitación:**  
  1) Admin emite invitación (`invites/{code}`) con email y expiración.  
  2) Se envía email con link firmado (`?invite=CODE`).  
  3) Usuario se registra con email/password; el backend valida que el email coincide con la invitación y marca `consumedBy`.  
- **Usuario maestro:** `javier.torron.diaz@gmail.com` con rol admin, preconfigurado en el sistema.  
- **Seguridad:** bcrypt para passwords, JWT con expiración, rate limiting, bloqueo por intentos, auditoría de acceso, Data Loss Prevention para exportes.  
- **GDPR:** consentimiento, derecho de supresión (borrado de Firestore + señal a backups).

## 4. UX y especificación de pantallas (Web)

> Se adapta la especificación de Activities y modales de Android a **rutas y componentes Angular**. Se mantienen conceptos UI (dashboard, listas, modales) con equivalentes Material para web.

### 4.1 Dashboard y Movimientos (`/app`)
**Layout responsive:**  
- **Header** con AppBar (título “Financial Nomad”, menú usuario).  
- **Segmented buttons**: “Balance” | “Movimientos”.  
- **Filtros de fecha**: “Mes actual” (default) | “Rango” | “Mes/Año”.  
- **Balance view**:  
  - Card principal con “Balance Total” y monto (animación count-up).  
  - Cards “Ingresos del mes” y “Gastos del mes” con iconos y colores semánticos.  
- **Movimientos view**:  
  - **Search bar** y botón **filtros**.  
  - **Tabla/lista virtualizada** con descripción, categoría, fecha y monto (color por tipo).  
  - **Paginación/Infinite scroll**.

**Acción principal:** FAB “Agregar” (modal).

### 4.2 Modal “Agregar movimiento”
- Selector “Gasto / Ingreso”.  
- **Importar YAML** (arrastrar/soltar o pegar texto).  
- Campos: monto (con formato moneda), descripción, categoría, fecha (date picker), método de pago.  
- Validación reactiva con mensajes accesibles.  
- Botones: Cancelar / Guardar (solo si válido).

### 4.3 Categorías (`/app/categories`)
- AppBar con “Categorías” y acción “Agregar”.  
- Tabs: “Gastos” | “Ingresos”.  
- Lista agrupada por categoría principal, items con acciones (editar/eliminar).  
- Modal editar con nombre, icono y color.

### 4.4 Cuentas y métodos de pago (`/app/accounts`)
- Secciones “Cuentas bancarias” y “Métodos de pago”.  
- Cards por cuenta con nombre banco, últimos 4 dígitos, tipo y balance.  
- Wizard para agregar cuenta (3 pasos): tipo → datos básicos → configuración.

### 4.5 Presupuestos (`/app/budgets`)
- Card resumen con progreso del mes (donut/circular).  
- Grid por categorías con barras de progreso (umbral <70% ok, 70–90% warning, >90% error).  
- Modal de configuración por categoría y exporte de análisis.

### 4.6 Configuración (`/app/settings`)
- Ingresos fijos, objetivos de ahorro (sliders), datos y privacidad (exportar/eliminar), “Sobre la app”.

### 4.7 Accesibilidad y responsive
- **WCAG 2.2 AA**: contraste ≥ 4.5:1, foco visible, navegación teclado, labels aria, prefer-reduced-motion.  
- **Responsive**: grid de 12 columnas, breakpoints para móvil/tablet/desktop; rail lateral en ≥ 1024px.

## 5. Importación YAML (Web)

Se mantiene el **formato YAML de Android** para continuidad (gastos/ingresos, con posibilidad de desglose de productos).  
- Validaciones: fecha ISO/locale configurable, montos > 0, categorías válidas, coherencia de subtotales, YAML bien formado.  
- Flujo web: arrastrar/soltar o pegar → validación en tiempo real → preview → confirmación → resumen (“X movimientos importados”).

> Ver formato en el anexo “Especificación YAML” (idéntico al de Android, con notas web).

## 6. Animaciones y Motion (Web)

- Transiciones de ruta: fade/slide con Angular Animations.  
- Microinteracciones: elevación/hover, ripple Material, skeleton loading (shimmer) en listas.  
- Charts con animación de entrada (path draw/height grow) y tooltips accesibles.  
- Respeta `prefers-reduced-motion` y ofrece alternativas sin movimiento.

## 7. Performance y optimización

- **Frontend**: lazy loading, change detection afinada, preconnect a Firestore, virtual scroll para listas grandes, memoized selectors.  
- **Backend**: endpoints idempotentes, paginación, filtros y ordenación; caching de lecturas calientes; límites de tamaño en exportes.  
- **Firestore**: reglas selectivas, batch writes, índices adecuados; evitar lecturas N+1.  
- **PWA**: cache first para estáticos, network first para datos, fallback de lectura a último snapshot.

## 8. Seguridad y privacidad

- **Auth**: Email/password con bcrypt; JWT + sesiones httpOnly + SameSite; revocación/rotación.  
- **Firestore Rules**: acceso por `uid` y validación de invitación aceptada; validación de esquemas básicos.  
- **Secret Manager**: tokens Asana/Drive cifrados; acceso por servicio mínimo necesario.  
- **Backups**: exportes automáticos de Firestore a GCS; job de réplica a Google Drive (carpeta privada); retención 7/4/12 (días/semanas/meses).  
- **PII mínima** y procedimientos de borrado (incluida señal a backups para purga programada cuando sea posible).

## 9. Backups a Google Drive (job)

1) Cloud Scheduler invoca Cloud Run/Function.  
2) El job localiza el **último export** de Firestore en GCS, comprime y segmenta si es necesario.  
3) Sube a **Drive** en carpeta segura (propietario del proyecto).  
4) Registra auditoría y conserva inventario.  
5) Estrategia de retención configurable (7 diarios, 4 semanales, 12 mensuales).

## 10. Integración con Asana

- **OAuth Asana** con scopes mínimos; almacenamiento cifrado.  
- **Mapping** sugerido: tareas para conciliación de transacciones/presupuestos; comentarios con referencias a `transactionId`.  
- **Webhooks** para cambios; **rate limiting** con reintentos exponenciales e idempotencia (`X-Request-Id`).  
- Endpoints backend: `/asana/oauth/callback`, `/asana/sync`, `/asana/webhook` (ver OpenAPI).

## 11. Exportes para LLMs

- **Snapshot** por usuario: `snapshot.json` (datos normalizados), `instructions.md` (qué análisis pedimos) y `constraints.md` (privacidad).  
- **Esquema**: ISO8601 para fechas, `amount` en céntimos, `currency` ISO-4217, `source`.  
- **Privacidad**: eliminar PII y nombres propios; sustitución por IDs/códigos de categoría.  
- **Uso**: descarga directa o envío temporal a un bucket firmado; TTL corto.

## 12. Roadmap (Web)

### MVP – Fase 1
- Auth básica email/password + **registro por invitación**.  
- Usuario maestro preconfigurado.  
- CRUD de transacciones, categorías, cuentas, presupuestos.  
- Importación YAML y dashboard con métricas básicas.  
- Reglas Firestore + tests + CI mínima.

### Fase 2 – Integraciones
- **Asana** (OAuth, sync, webhooks).  
- **Backups** GCS → réplica **Drive** (Scheduler + Run).  
- Exportes para **LLMs** (snapshot + instrucciones).

### Fase 3 – Optimización/Analytics
- Agregados mensuales, alertas de presupuesto, charts avanzados.  
- Auditoría y mejores prácticas de rendimiento.  
- Experiencia PWA mejorada.

## 13. Testing

- **Frontend**: unit (Jest/Vitest) + e2e (Playwright) para flujos críticos.  
- **Backend**: unit (pytest) + integración (Firestore emulator).  
- **Reglas**: tests con Firebase Emulator Suite.  
- **Accesibilidad**: AXE y pruebas manuales con lector de pantalla.

## 14. Anexo – Especificación YAML (resumen)

Se mantiene el **mismo formato YAML** para **gastos** (individual y con desglose) e **ingresos** definido en la doc original Android, con estas notas Web:  
- Se aceptan fechas **DD/MM/AAAA** o **AAAA-MM-DD** (configurable).  
- Se validan categorías contra catálogo del usuario.  
- El parser rechaza valores no numéricos y subtotales incoherentes.  
- Informe de importación: lista de entradas aceptadas/descartadas y motivos.

---

### Notas de trazabilidad
- Esta conversión toma como base la **documentación funcional Android** (estructura, UX, catálogos, YAML) y la adapta a tecnologías web y a la arquitectura objetivo (Angular + FastAPI + Firestore + GCP). Donde procede, se reemplaza el enfoque **offline-first local** por **serverless con PWA** y controles de seguridad/backup en la nube.
