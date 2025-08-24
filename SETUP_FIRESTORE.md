# Configuración de Firestore para Financial Nomad

Este documento te guiará para configurar Firestore y probar el sistema de autenticación.

## Opción 1: Desarrollo Local con Emulador (Recomendado)

### 1. Instalar Firebase CLI

```bash
npm install -g firebase-tools
```

### 2. Configurar variables de entorno

```bash
# En el directorio backend/
cp .env.development .env

# Edita .env y ajusta los valores necesarios:
# - JWT_SECRET_KEY: Una clave secreta larga y segura
# - FIRESTORE_PROJECT_ID: Nombre de tu proyecto (puede ser cualquiera para el emulador)
```

### 3. Iniciar el emulador de Firestore

```bash
# Desde el directorio raíz del proyecto
./backend/scripts/start_firestore_emulator.sh
```

Esto iniciará:
- **Emulador de Firestore**: `localhost:8080`
- **UI del emulador**: `http://localhost:4000`

### 4. Configurar la base de datos

```bash
# En otra terminal, desde el directorio backend/
cd backend
python scripts/setup_firestore.py
```

Este script:
- Verifica la conexión a Firestore
- Crea el usuario maestro con credenciales predefinidas

### 5. Iniciar el backend

```bash
cd backend
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8080
```

### 6. Probar la autenticación

**Credenciales del usuario maestro:**
- **Email**: `javier.torron.diaz@gmail.com`
- **Contraseña**: `fI07.08511982#`

Puedes probar con:
- Frontend Angular: `http://localhost:4200`
- API directamente: `http://localhost:8080/docs`

## Opción 2: Firestore Real en Google Cloud

### 1. Crear proyecto en Google Cloud

1. Ve a [Google Cloud Console](https://console.cloud.google.com)
2. Crea un nuevo proyecto o selecciona uno existente
3. Habilita la API de Firestore

### 2. Configurar autenticación

```bash
# Crear una cuenta de servicio
gcloud iam service-accounts create financial-nomad-service \
    --description="Service account para Financial Nomad" \
    --display-name="Financial Nomad Service"

# Asignar roles necesarios
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:financial-nomad-service@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/datastore.user"

# Crear clave de servicio
gcloud iam service-accounts keys create service-account-key.json \
    --iam-account=financial-nomad-service@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

### 3. Configurar variables de entorno

```bash
# En el archivo .env
USE_FIRESTORE_EMULATOR=false
FIRESTORE_PROJECT_ID=YOUR_PROJECT_ID
GOOGLE_CREDENTIALS_PATH=/path/to/service-account-key.json
```

### 4. Configurar reglas de seguridad

1. Ve a Firestore en Google Cloud Console
2. Selecciona "Reglas"
3. Copia el contenido de `firestore.rules`

### 5. Continuar con los pasos 4-6 de la opción 1

## Verificación de la configuración

### 1. Health check del backend

```bash
curl http://localhost:8080/api/v1/health
```

### 2. Crear usuario maestro

```bash
curl -X POST http://localhost:8080/api/v1/auth/init-master
```

### 3. Probar login

```bash
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "javier.torron.diaz@gmail.com",
    "password": "fI07.08511982#"
  }'
```

## Estructura de datos en Firestore

```
firestore/
├── users/{userId}                    # Información del usuario
├── invitations/{invitationId}        # Códigos de invitación
├── sessions/{sessionId}              # Sesiones activas
├── accounts/{userId}/
│   ├── bank_accounts/{accountId}     # Cuentas bancarias
│   ├── categories/{categoryId}       # Categorías personalizadas
│   ├── transactions/{transactionId}  # Transacciones
│   └── budgets/{budgetId}           # Presupuestos
├── integrations/{userId}/            # Integraciones externas
└── exports/{userId}/                 # Exportaciones LLM
```

## Troubleshooting

### Error: "FIRESTORE_PROJECT_ID not set"
- Verifica que el archivo `.env` existe y tiene la variable `FIRESTORE_PROJECT_ID`

### Error: "Failed to connect to database"
- Si usas emulador: Verifica que está corriendo en `localhost:8080`
- Si usas Firestore real: Verifica las credenciales y permisos

### Error: "Master user already exists"
- Es normal si ya ejecutaste el setup antes. El usuario maestro solo se crea una vez.

### Error de CORS en el frontend
- Verifica que `CORS_ORIGINS` en `.env` incluye `http://localhost:4200`

## Próximos pasos

Una vez configurado, puedes:

1. **Crear invitaciones** (como admin): Usar el endpoint `/api/v1/auth/invite`
2. **Registrar nuevos usuarios**: Con el código de invitación
3. **Desarrollar funcionalidades**: Las colecciones se crearán automáticamente
4. **Monitorear datos**: Usar la UI del emulador en `http://localhost:4000`

## Seguridad

- ✅ **Contraseñas**: Hasheadas con bcrypt
- ✅ **JWT**: Con expiración automática
- ✅ **Reglas Firestore**: Acceso solo a datos propios
- ✅ **Validación**: En backend y frontend
- ✅ **Invitaciones**: Registro controlado por códigos