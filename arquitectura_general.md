# Arquitectura General del Proyecto (GCP · $0 dentro de los límites free)

> **Objetivo:** describir la arquitectura *end-to-end* del proyecto sin detallar backend o frontend, usando **solo opciones gratuitas** (dentro de los límites del Free Tier / no-cost quotas).  
> **Nota importante sobre “$0”**: algunos productos de Google Cloud requieren **tener facturación habilitada** para aplicar el **Always Free** (aunque el uso se facture a $0 si no se superan límites). Por ejemplo **Cloud Run**. **Firestore** y **Firebase Hosting** disponen de cuotas gratuitas documentadas. Recomendamos vigilar el uso y fijar límites/alertas.

---

## 1) Alcance funcional (vista global)

Funcionalidades que el sistema debe cubrir:

- **Acceso e identidad:** inicio de sesión con Google OAuth; alta **por invitación** vía email.
- **Datos financieros núcleo:** cuentas, categorías (ingresos/gastos), transacciones, **importación YAML**.
- **Ingresos/gastos fijos:** gestión separada de los fijos (p. ej., salario, alquiler).
- **Presupuestos** por categoría/periodo y su consumo.
- **Proyectos de ahorro:** objetivo (€), progreso y **prioridades**; vinculación a uno o más gastos.
- **Pagos diferidos:** préstamos/hipotecas/compras aplazadas con cálculo de cuotas, capital vs. intereses, pagado/restante.
- **Configuración de usuario de ahorro:** mínimo fijo (en €) + % objetivo (sobre ingresos).
- **Exportaciones para LLMs:** snapshots normalizados (sin PII) en JSON/CSV.
- **Integración con Asana:** OAuth, sincronización y webhooks.
- **Copias/descargas de datos:** exportación bajo demanda; réplica manual de backups a Google Drive (ver §6.3).
- **Operación básica sin coste:** observabilidad mínima, límites y guardarraíles para no salir del free tier.

---

## 2) Vista de componentes (sin entrar en detalle por capa)

```
[Usuario]
   │  (HTTPS, OAuth Google)
   ▼
[Aplicación Web (SPA/PWA)]
   │  (HTTPS, Bearer ID Token)
   ▼
[API pública · Cloud Run]
   │──────────► [Firestore (datos)]
   │──────────► [Google Drive API (exportes / réplica manual)]
   │──────────► [Asana API (OAuth + webhooks)]
   └──────────► [Logging/Monitoring básicos]
```

**Principios clave**
- **Solo el backend** (API) accede a la base de datos.  
- Todo tráfico es **HTTPS**; autenticación vía **Google ID Token**.  
- Las tareas “en segundo plano” **se ejecutan on-demand** (usuario/operador) para evitar servicios de cron de pago.

---

## 3) Productos de Google usados en modo gratuito

- **Cloud Run** (API): *Always Free* con 2M requests/mes y computación incluida en el nivel gratuito (en regiones elegibles). Mantener **instancias mínimas = 0** para evitar consumo fuera de peticiones.
- **Firestore (modo nativo)**: cuota gratuita diaria (aprox.: 50k lecturas/día, 20k escrituras/día, 1GiB almacenamiento; ver tabla oficial; reseteo diario). Evitar características que requieren billing (TTL, PITR, backups gestionados, restore/clones).
- **Firebase Hosting** (para entregar la SPA): almacenamiento y transferencia con límites sin coste (p. ej., 10 GB almacenamiento y cuota de transferencia documentada). Adecuado para MVP bajo tráfico.
- **Cloud Logging/Monitoring**: uso bajo (logs básicos). Alertas simples; vigilar cuotas. *(Alerta: algunos tipos de alerting avanzados tienen cambios de facturación en el tiempo, revisar políticas vigentes).* 
- **Google Drive API**: utilizado desde la API para **replicar exportes/manual**. No requiere producto de pago adicional si el uso es bajo.

> **No incluidos por coste**: **Cloud Scheduler**, **Firestore Backups gestionados**, **Workflows** si exceden gratis, y funciones con facturación forzosa. En su lugar, se ofrecen **acciones manuales** o disparadas desde el usuario (ver §6).

---

## 4) Flujos funcionales principales (alto nivel)

### 4.1 Onboarding por invitación
1) Admin emite invitación (email + caducidad).  
2) Usuario entra con Google; la app envía **ID Token + código** a la API.  
3) La API valida email ↔ invitación y crea el perfil de usuario.

### 4.2 Gestión financiera
- **Transacciones** (ingreso/gasto) + **importación YAML** (previsualización y validación).  
- **Fijos** separados: altas/bajas/pausas y cálculo de próximas ocurrencias.  
- **Presupuestos**: fijación por categoría/periodo y cálculo de consumo.  
- **Proyectos de ahorro**: objetivo, prioridad y progreso (asociación a gastos).  
- **Pagos diferidos**: cuota, intereses/capital, progreso pagado/restante.

### 4.3 Exportes para LLMs
- Usuario solicita snapshot (rango temporal, elección de entidades).  
- API genera artefacto **sin PII** y ofrece descarga temporal.

### 4.4 Integración con Asana
- **Conectar** (OAuth) / **Desconectar**.  
- **Sync on-demand** desde la app (evitar cron) y **webhook** de Asana para eventos entrantes.

### 4.5 Copias / Descargas
- **Exportes bajo demanda** (JSON/CSV).  
- **Réplica manual a Drive**: botón en consola operativa que llama a la API (ver §6.3).

---

## 5) Seguridad (postura transversal, sin detalles de implementación)
- **Autenticación**: solo usuarios con **email verificado** (Google).  
- **Autorización**: aislamiento estricto por usuario; rol `admin` solo para invitaciones/operaciones globales.  
- **Datos**: minimización de PII, exportes anonimizados, cifrado en tránsito.  
- **Integraciones**: tokens en **Secret Manager**; callbacks (webhooks Asana) con verificación de firma.  
- **Límites**: tamaño de payload, *rate limits* y *Idempotency-Key* en mutaciones para evitar duplicados.  
- **Auditoría**: registro de acciones sensibles (altas/bajas, exportes, OAuth).

---

## 6) Operación sin costes automáticos

### 6.1 Sin cron de pago
Para mantener $0 dentro de GCP evitamos **Cloud Scheduler**. Las tareas periódicas se reconvierten en:
- **Acciones on-demand** desde la interfaz (el usuario pulsa “Sincronizar ahora”, “Generar snapshot”, “Replicar a Drive”).  
- **Webhooks externos** (solo recepción, no agenda interna de GCP).

### 6.2 Monitorización básica
- Logs y métricas con *sampling* conservador. Alertas mínimas (p. ej. error-rate alzado).

### 6.3 Copias y réplica a Drive (manual)
- La API expone una **acción manual** “Replica a Drive” que:
  1) Localiza el último **exporte**/snapshot (generado bajo demanda).  
  2) Lo sube a **Google Drive** del proyecto (carpeta protegida).  
- *Alternativa*: descargar localmente (por usuario admin) y subir a Drive fuera de GCP.

> *Recordatorio*: las **copias gestionadas de Firestore (backups/restore/PITR)** requieren billing; no se usan en modo $0.

---

## 7) Datos (modelo conceptual, nivel “cajas”)

- **Usuarios**: perfil mínimo + configuración de ahorro (mínimo € y % objetivo).  
- **Invitaciones**: email, estado, caducidad.  
- **Cuentas** y **Categorías** (jerarquía simple).  
- **Transacciones** (eventuales) y **Fijos** (ingresos/gastos periódicos).  
- **Presupuestos** por categoría/periodo.  
- **Proyectos de ahorro**: objetivo, prioridad, gastos asociados, progreso/estado.  
- **Pagos diferidos**: plan de amortización, intereses, saldo pagado/restante.  
- **Exportes LLM**: metadatos + artefactos descargables.  
- **Integración Asana**: tokens/ámbitos y estado de sync.

*(El detalle de campos vive en la documentación funcional.)*

---

## 8) Entornos y despliegue (alto nivel)

- **Desarrollo local**: SPA + API en contenedores; emuladores cuando sea posible.  
- **Producción**:  
  - SPA en **Firebase Hosting** (cuotas gratuitas).  
  - API en **Cloud Run** (Always Free, instancias mínimas 0).  
  - **Firestore** con cuotas gratuitas diarias (vigilar límites).  
- **CI/CD**: pipeline con proveedor gratuito (por ejemplo, GitHub Actions) para *build* y despliegue a Hosting/Run (no implica coste en GCP).

---

## 9) Gobernanza de costes ($0 guardarraíles)

- **Límites técnicos**: *rate limits*, tamaño de payload, `pageSize` máximo, compresión en respuestas.  
- **Control de escalado**: Cloud Run con **minInstances=0** y concurrencia moderada.  
- **Cuotas**: alertas y panel de uso (Hosting, Firestore, Cloud Run).  
- **Fuera de alcance** (por coste): Scheduler, Backups gestionados/PITR de Firestore, cargas masivas frecuentes.

---

## 10) Riesgos y mitigaciones (modo $0)

- **Sin tareas programadas internas** → riesgo de olvidar acciones:  
  - *Mitigación*: botones on-demand visibles + recordatorios en la app.  
- **Cuotas Firestore/Hosting** → bloqueo/limitación al superar:  
  - *Mitigación*: paginación, cache del lado cliente, tamaños contenidos, monitorizar uso.  
- **Frío de Cloud Run** → latencia inicial tras inactividad:  
  - *Mitigación*: UX tolerante al primer acceso; evitar *min instances* para no salir del free tier.

---

## 11) Resumen

Esta arquitectura prioriza **$0 de coste** manteniendo las funcionalidades requeridas y una postura de **seguridad por defecto**. Se apoya en:
- **Cloud Run (Always Free)** para la API,
- **Firestore** con **cuotas gratuitas**,
- **Firebase Hosting** para la SPA,
- **Drive API** para réplicas **manuales**,
- e **integración Asana** bajo demanda.

El sistema evita componentes con coste fijo (p. ej., Scheduler, Backups gestionados) y convierte tareas recurrentes en **acciones on-demand** disparadas por el usuario/operador.
