# 🚀 Crear Google OAuth - Guía Rápida

## Paso 1: Acceder a Google Cloud Console
1. Ve a https://console.cloud.google.com/
2. Inicia sesión con tu cuenta `javier.torron.diaz@gmail.com`

## Paso 2: Crear/Seleccionar Proyecto
1. Haz clic en el selector de proyecto (esquina superior izquierda)
2. Haz clic en "NEW PROJECT" 
3. Nombre: `financial-nomad-dev`
4. Haz clic en "CREATE"

## Paso 3: Habilitar Google+ API
1. Ve a **APIs & Services** → **Library**
2. Busca "Google+ API" 
3. Haz clic en "ENABLE"

## Paso 4: Configurar OAuth Consent Screen
1. Ve a **APIs & Services** → **OAuth consent screen**
2. Selecciona **External**
3. Completa:
   - App name: `Financial Nomad`
   - User support email: `javier.torron.diaz@gmail.com`
   - Developer contact: `javier.torron.diaz@gmail.com`
4. Haz clic en "SAVE AND CONTINUE"
5. En "Scopes" → "SAVE AND CONTINUE" (usar defaults)
6. En "Test users" → Agregar: `javier.torron.diaz@gmail.com`
7. Haz clic en "SAVE AND CONTINUE"

## Paso 5: Crear Credenciales OAuth
1. Ve a **APIs & Services** → **Credentials**
2. Haz clic en **+ CREATE CREDENTIALS**
3. Selecciona **OAuth client ID**
4. Application type: **Web application**
5. Name: `Financial Nomad Web Client`
6. **Authorized JavaScript origins:**
   ```
   http://localhost:4200
   http://localhost
   http://127.0.0.1:4200
   ```
7. **Authorized redirect URIs:**
   ```
   http://localhost:4200/auth/callback
   http://localhost:4200
   ```
8. Haz clic en **CREATE**

## Paso 6: Copiar Client ID
1. Se abrirá un popup con las credenciales
2. **COPIA el Client ID** (formato: `123456789-abc123.apps.googleusercontent.com`)
3. Guárdalo en un lugar seguro

## Paso 7: Configurar en la Aplicación
Ejecuta este comando reemplazando `TU_CLIENT_ID_AQUÍ`:

```bash
# Ir al directorio del proyecto
cd /home/lordvermiis/source/financial-nomad

# Parar servicios
docker compose -f devops/docker-compose/docker-compose.dev.yml down

# Actualizar docker-compose con tu Client ID
sed -i 's/GOOGLE_CLIENT_ID=.*/GOOGLE_CLIENT_ID=TU_CLIENT_ID_AQUÍ/' devops/docker-compose/docker-compose.dev.yml

# Reiniciar servicios
docker compose -f devops/docker-compose/docker-compose.dev.yml up -d
```

## Paso 8: Probar
1. Ve a http://localhost:4200
2. Haz clic en "Continuar con Google"
3. Debería funcionar correctamente

---

## 🆘 Si tienes problemas:

### Error: "redirect_uri_mismatch"
- Verifica que las URLs en GCP coincidan exactamente
- Asegúrate de incluir `http://localhost:4200` (no `https://`)

### Error: "access_blocked"  
- Verifica que tu email esté en "Test users"
- O cambia la app a "In production" (requiere verificación)

### Error: "invalid_client" persiste
- Verifica que el Client ID se copió completamente
- Asegúrate de que no hay espacios extra

---

💡 **Tip:** Una vez que funcione, puedes obtener el Client Secret para integraciones futuras desde la misma página de credenciales.