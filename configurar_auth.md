# Configurar Google OAuth en GCP

## 📋 Resumen
Esta guía explica cómo configurar Google OAuth en Google Cloud Platform (GCP) para la aplicación Financial Nomad.

## 🚀 Pasos de Configuración

### 1. Crear/Acceder al Proyecto GCP

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. **Crear nuevo proyecto** o seleccionar proyecto existente:
   - Nombre sugerido: `financial-nomad-dev`
   - ID del proyecto: `financial-nomad-dev-[número]`

### 2. Habilitar APIs Necesarias

En Cloud Console, ve a **APIs & Services > Library** y habilita:

```
✅ Google+ API
✅ Identity and Access Management (IAM) API
✅ Cloud Firestore API
```

**Comando gcloud alternativo:**
```bash
gcloud services enable plus.googleapis.com
gcloud services enable iam.googleapis.com  
gcloud services enable firestore.googleapis.com
```

### 3. Configurar OAuth Consent Screen

1. Ve a **APIs & Services > OAuth consent screen**
2. Selecciona **External** (para testing)
3. Completa la información requerida:

```yaml
App name: Financial Nomad
User support email: tu-email@gmail.com
Developer contact information: tu-email@gmail.com
Application home page: http://localhost:4200
Application privacy policy: http://localhost:4200/privacy (opcional para dev)
Application terms of service: http://localhost:4200/terms (opcional para dev)
```

4. **Scopes**: Agregar estos scopes esenciales:
   - `openid`
   - `email` 
   - `profile`

5. **Test users** (para desarrollo):
   - Agregar tu email y emails de otros desarrolladores
   - Máximo 100 usuarios en modo testing

### 4. Crear Credenciales OAuth

1. Ve a **APIs & Services > Credentials**
2. Clic en **+ CREATE CREDENTIALS > OAuth client ID**
3. Selecciona **Web application**
4. Configurar:

```yaml
Name: Financial Nomad Web Client
Authorized JavaScript origins:
  - http://localhost:4200
  - http://localhost:80
  - http://127.0.0.1:4200
Authorized redirect URIs:
  - http://localhost:4200/auth/callback
  - http://localhost:4200/login
  - http://localhost:4200
```

5. **Descargar credenciales JSON** (guardar seguro)

### 5. Obtener Client ID

Después de crear las credenciales:

1. Copia el **Client ID** (formato: `123456789-abcdefgh.apps.googleusercontent.com`)
2. Guarda también el **Client Secret** (para futuras integraciones server-side)

## 🔧 Configurar en el Proyecto

### 6. Variables de Entorno - Desarrollo

Crear archivo `.env` en la raíz del proyecto:

```bash
# Google OAuth
GOOGLE_CLIENT_ID=tu-client-id-aqui.apps.googleusercontent.com

# Backend
SECRET_KEY=tu-secret-key-seguro-para-jwt
FIRESTORE_PROJECT_ID=financial-nomad-dev-123456
```

### 7. Variables de Entorno - Docker

En `devops/docker-compose/docker-compose.dev.yml`, actualizar:

```yaml
services:
  frontend:
    environment:
      - GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
      # ... otras variables

  backend:
    environment:
      - GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
      - SECRET_KEY=${SECRET_KEY}
      - FIRESTORE_PROJECT_ID=${FIRESTORE_PROJECT_ID}
      # ... otras variables
```

### 8. Configurar Angular

En `frontend/src/environments/environment.ts`:

```typescript
export const environment = {
  production: false,
  apiUrl: 'http://localhost:8080/api/v1',
  googleClientId: 'tu-client-id-aqui.apps.googleusercontent.com'
};
```

## 🧪 Testing de Configuración

### 9. Verificar Setup

1. **Reiniciar servicios Docker:**
```bash
cd /home/lordvermiis/source/financial-nomad
docker compose -f devops/docker-compose/docker-compose.dev.yml down
docker compose -f devops/docker-compose/docker-compose.dev.yml up -d
```

2. **Verificar variables están cargadas:**
```bash
# Verificar frontend
docker compose -f devops/docker-compose/docker-compose.dev.yml exec frontend env | grep GOOGLE

# Verificar backend  
docker compose -f devops/docker-compose/docker-compose.dev.yml exec backend env | grep GOOGLE
```

3. **Test de login:**
   - Abrir http://localhost:4200
   - Hacer clic en "Login with Google" 
   - Debería abrir popup de Google OAuth
   - Permitir permisos solicitados
   - Redireccionar de vuelta a la app autenticado

## 🔒 Consideraciones de Seguridad

### Para Desarrollo
- ✅ Usar `http://localhost` está permitido por Google
- ✅ Client ID puede ser público (va en frontend)
- ❌ Client Secret debe mantenerse privado
- ⚠️ Modo "Testing" permite máximo 100 usuarios

### Para Producción
- 🔒 Cambiar a **Internal** si es solo para tu organización
- 🔒 O completar **OAuth Verification** para público general  
- 🔒 Usar HTTPS obligatorio para producción
- 🔒 Configurar dominios reales en lugar de localhost

## 📚 Enlaces Útiles

- [Google OAuth Documentation](https://developers.google.com/identity/protocols/oauth2)
- [Google Console](https://console.cloud.google.com/)
- [Angular Google OAuth Guide](https://developers.google.com/identity/gsi/web/guides/overview)

## 🆘 Troubleshooting

### Error: "redirect_uri_mismatch"
- Verificar que las URLs en GCP coincidan exactamente con las de la app
- Incluir tanto `localhost` como `127.0.0.1`

### Error: "access_blocked" 
- Verificar que el email está en la lista de test users
- O cambiar app a modo "In production" (requiere verificación)

### Frontend no carga Client ID
- Verificar variable de entorno `GOOGLE_CLIENT_ID` 
- Reiniciar contenedor frontend después de cambios

### Backend no valida tokens
- Verificar `GOOGLE_CLIENT_ID` en backend coincide con frontend
- Verificar Secret Key está configurado

---

**💡 Tip:** Guarda el Client ID y Client Secret en un lugar seguro. Los necesitarás para configuraciones futuras y despliegues en producción.