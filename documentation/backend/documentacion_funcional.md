# Documentación Funcional — Backend Financial Nomad (con Integración Asana por usuario)

> **Ámbito**: documentación funcional (sin arquitectura ni contratos de API).  
> **Enfoque**: security‑first. Sólo el backend accede a la base de datos.  
> **Novedad**: configuración por usuario de Asana (proyecto y tableros/columnas de trabajo) y flujo de ingestión/marcado de tareas.

---

## 1. Alcance del sistema

El backend proporciona una API segura para gestionar finanzas personales y sincronizar tareas desde Asana. Sus responsabilidades funcionales son:

- Autenticación de usuarios con Google y alta por invitación.
- Gestión de **cuentas**, **categorías**, **transacciones**, **fijos** (ingresos/gastos periódicos), **presupuestos**.
- Gestión de **proyectos de ahorro** (objetivo, prioridad, progreso) y **pagos diferidos** (préstamos/hipotecas/aplazados).
- Configuración de usuario de ahorro: **mínimo fijo (€)** y **% objetivo** (sobre ingresos).
- **Integración Asana por usuario**: elección de **proyecto** y mapeo de **tableros** (columnas/secciones) para:
  - **Gastos pendientes**
  - **Gastos procesados**
  - **Ingresos pendientes**
  - **Ingresos procesados**
- **Ingesta desde Asana**: leer tareas en “pendientes”, crear transacciones correspondientes en la base de datos y **mover** las tareas a los tableros de “procesados”.
- Exportaciones para LLMs (snapshots normalizados, sin PII).
- Gestión de invitaciones y auditoría de acciones clave.

---

## 2. Usuarios y roles

- **Usuario estándar**: gestiona únicamente sus propios recursos e integra su propia cuenta de Asana.
- **Administrador**: emite/revoca invitaciones y accede a operaciones globales (sin acceso a Asana individual de otros usuarios).

---

## 3. Entidades funcionales

### 3.1 Usuario
- Identificado por `uid` y correo verificado.
- Preferencias (idioma, moneda) y configuración de ahorro (mínimo fijo €, % objetivo).

### 3.2 Invitación
- Código único + email, con caducidad y estado (pendiente/consumida/expirada/revocada).

### 3.3 Cuenta
- Nombre, tipo (banco/efectivo/tarjeta), últimos 4 dígitos, moneda, balance visible.

### 3.4 Categoría
- Tipo: **ingreso** | **gasto**; jerarquía simple (padre opcional), nombre único por tipo.

### 3.5 Transacción
- Tipo: **ingreso** | **gasto**; cantidad (en céntimos), moneda, fecha, categoría, cuenta, descripción etiquetada.

### 3.6 Fijo (ingreso/gasto periódico)
- Monto, moneda, periodicidad (mensual/semanal/anual/personalizada), inicio y fin opcional, estado (activo/inactivo).

### 3.7 Presupuesto
- Categoría, periodo, límite, estado de consumo.

### 3.8 Proyecto de ahorro
- Nombre, descripción, **objetivo (€)**, prioridad relativa, gastos asociados, estado (en curso/completado/cancelado), progreso.

### 3.9 Pago diferido
- Tipo (préstamo/hipoteca/aplazado), importe inicial, intereses, calendario de cuotas, pagado/restante, intereses pagados/restantes, estado.

### 3.10 Exportación LLM
- Id, fecha, rango temporal, tipos incluidos, enlace temporal de descarga, estado (listo/expirado).

### 3.11 Integración Asana (configuración por usuario)
- Estado de conexión (conectado/desconectado).
- **Proyecto seleccionado** (id/nombre) desde el que se leerán y actualizarán tareas.
- **Mapeo de tableros (secciones/columnas) dentro del proyecto**:
  - `expenses_pending_section_id`
  - `expenses_processed_section_id`
  - `incomes_pending_section_id`
  - `incomes_processed_section_id`
- Preferencias de mapeo de campos (opcional): reglas para extraer **monto**, **fecha**, **categoría** y **cuenta** a partir de título, notas o campos personalizados de la tarea.
- Última fecha de sincronización exitosa y bitácora de resultados (contadores o resumen).

---

## 4. Funcionalidades

### 4.1 Autenticación y registro por invitación
- Inicio de sesión con Google (email verificado).
- Alta sólo si existe invitación válida asociada al email.

### 4.2 Gestión de cuentas, categorías, transacciones, fijos y presupuestos
- CRUD de cada entidad y consultas con filtros/paginación.
- Importación de transacciones desde **YAML** (previsualización + validación).

### 4.3 Proyectos de ahorro
- Crear/editar proyectos con objetivo (€) y prioridad.
- Asociar gastos (transacciones) a proyectos.
- Calcular y consultar progreso; completar/cancelar proyectos.

### 4.4 Pagos diferidos
- Registrar préstamos/hipotecas/aplazados con calendario de cuotas.
- Consultar en cualquier momento: total pagado, restante, intereses pagados/restantes.
- Editar, pausar o cerrar un esquema de pago diferido.

### 4.5 Exportaciones para LLMs
- Generar snapshot sin PII (IDs y códigos), normalizado (ISO‑8601, céntimos).
- Consultar y eliminar exportes anteriores.

### 4.6 Integración Asana por usuario (configuración)
- **Conectar Asana**: flujo OAuth del usuario para conceder acceso al proyecto.
- **Elegir proyecto** desde su espacio de Asana (listado de proyectos accesibles por el usuario).
- **Seleccionar tableros (secciones/columnas)** dentro del proyecto que actuarán como:
  - “Gastos pendientes” (origen de ingestión de gastos).
  - “Gastos procesados” (destino tras integrar).
  - “Ingresos pendientes” (origen de ingestión de ingresos).
  - “Ingresos procesados” (destino tras integrar).
- **Guardar configuración**; puede modificarse en cualquier momento.
- **Desconectar Asana**: revoca permisos y limpia metadatos de conexión (no borra transacciones ya creadas).

### 4.7 Ingesta y procesamiento desde Asana
**Objetivo:** leer tareas en “pendientes”, crear transacciones en la base de datos y mover las tareas a “procesados”.

- **Disparo**: manual desde la UI (“Sincronizar ahora”) o cuando el usuario complete la configuración.  
- **Ámbito**: sólo el **proyecto y secciones** configurados por el usuario.  
- **Reglas de ingestión**:
  - **Gastos**: tareas encontradas en el tablero configurado como “gastos pendientes” → se crean transacciones tipo **gasto**.
  - **Ingresos**: tareas encontradas en el tablero configurado como “ingresos pendientes” → se crean transacciones tipo **ingreso**.
- **Extracción de datos** (mapeo por defecto; ajustable por preferencias del usuario):
  - **Monto**: se detecta en el título o en notas (`€123,45`, `123.45 EUR`); si hay campo personalizado designado, prevalece.
  - **Fecha**: due date de la tarea o fecha actual si no existe.
  - **Categoría**: etiqueta/section/hashtag en título o notas; si no se identifica, categoría “Sin clasificar” (por tipo).
  - **Cuenta**: predeterminada del usuario o mapeo por palabra clave; si no se identifica, cuenta “General”.
  - **Descripción**: título de la tarea (conservando referencia al id de Asana).
- **Idempotencia**:
  - Una tarea de Asana **no debe crear duplicados**. Se registra un vínculo `externalRef` con el id de la tarea Asana para detectar ingestas previas.
- **Post‑proceso**:
  - Al crear con éxito la transacción correspondiente, **mover la tarea** a la sección “gastos procesados” o “ingresos procesados” según su tipo.
  - Añadir un comentario en la tarea con la referencia de la transacción creada (opcional).
- **Errores parciales**:
  - Si no se puede extraer el **monto**, la tarea queda en “pendientes” y se registra como **requiere revisión**.
  - Si falla el movimiento a “procesados” pero la transacción ya se creó, se reintenta en la siguiente sincronización y se marca la ingesta como **pendiente de mover**.
- **Resumen de sincronización**: número de tareas leídas, creadas, ignoradas, con errores, movidas a procesados.

### 4.8 Webhooks Asana (opcional)
- Recepción de eventos de creación/cambio de tareas **solo del proyecto configurado** del usuario.
- Política funcional: los webhooks **no crean** transacciones por sí mismos; únicamente **etiquetan para sincronizar** o disparan una **sincronización inmediata** del usuario afectado, respetando idempotencia y reglas anteriores.

---

## 5. Reglas de negocio

- Un usuario **no** puede acceder ni sincronizar el Asana de otro usuario.
- Se debe mantener **consistencia** entre tareas procesadas y transacciones creadas; si no se puede mover la tarea a “procesados”, la ingesta se considera **incompleta** y se reintentará.
- Las **secciones** configuradas deben existir en el proyecto elegido; si el usuario cambia de proyecto, el sistema requiere **re‑seleccionar** secciones válidas.
- Si el usuario **desconecta Asana**, no se eliminan las transacciones creadas previamente.
- En la configuración de ahorro del usuario, el **mínimo fijo (€)** y el **% objetivo** no pueden estar ambos a cero.
- Los **fijos** se gestionan en apartado separado y **no** se mezclan con la lista general de transacciones.
- Los **pagos diferidos** deben mostrar en todo momento: total pagado, restante y desglose de intereses.
- Un **proyecto de ahorro** no puede completarse si no alcanza el objetivo, salvo cancelación explícita.

---

## 6. Escenarios de uso

1. **Configurar Asana por primera vez**  
   El usuario conecta su cuenta de Asana, elige un proyecto y selecciona las cuatro secciones requeridas. Guarda la configuración.

2. **Sincronización manual**  
   El usuario pulsa “Sincronizar ahora”. El backend lee “gastos pendientes” e “ingresos pendientes”, crea transacciones y mueve tareas a “procesados”. Se muestra un resumen.

3. **Fallo de extracción de monto**  
   La tarea carece de monto. Se marca como “requiere revisión” y permanece en “pendientes”. El usuario corrige la tarea en Asana o ajusta el mapeo y vuelve a sincronizar.

4. **Cambio de proyecto**  
   El usuario selecciona otro proyecto; la app le pide re‑elegir las secciones para los cuatro tableros obligatorios antes de permitir sincronizar.

5. **Desconectar Asana**  
   El usuario revoca la conexión. No se pierde histórico de transacciones; simplemente no se permite sincronizar hasta reconectar y configurar secciones.

---

## 7. Requisitos no funcionales asociados (alto nivel funcional)

- **Seguridad**: todas las operaciones autenticadas; validación estricta de propiedad (`uid`) y de configuración Asana por usuario.
- **Idempotencia**: la relación transacción↔tarea Asana evita duplicados en reintentos.
- **Trazabilidad**: cada sincronización genera un resumen consultable por el usuario.
- **Disponibilidad**: la sincronización debe tolerar errores parciales y reintentos.
- **Privacidad**: no persistir datos innecesarios de Asana; almacenar sólo referencias mínimas (ids, nombres de secciones y proyecto).

---

## 8. Métricas funcionales de éxito (MVP)

- Configuración Asana completada por el usuario en < 2 minutos.
- Sincronización típica (< 100 tareas) finalizada con ≥ 95% de éxito sin intervención manual.
- 0 duplicados de transacciones provenientes de Asana en sincronizaciones repetidas.
- Posibilidad de auditar qué tareas se movieron a “procesados” y su transacción asociada.

---

## 9. Definition of Done (funcional, backend)

- [ ] Flujo de **conexión Asana** por usuario, con selección de proyecto y cuatro secciones obligatorias.  
- [ ] **Sincronización** que crea transacciones desde “pendientes” y **mueve** tareas a “procesados”, con idempotencia.  
- [ ] **Resumen** de sincronización disponible para el usuario (conteos y estado).  
- [ ] CRUD completos de cuentas/categorías/transacciones/fijos/presupuestos.  
- [ ] Proyectos de ahorro y pagos diferidos con consultas de progreso/estado.  
- [ ] Exportaciones LLM sin PII y borrables por el usuario.  
- [ ] Auditoría básica de acciones sensibles.
