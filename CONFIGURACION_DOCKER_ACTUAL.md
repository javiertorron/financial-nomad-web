# Estado Actual de Docker

## 🐳 **Configuración de Docker actualizada**

He corregido el `docker-compose.dev.yml` para que funcione con el nuevo sistema de autenticación email/password:

### **✅ Cambios realizados:**
- ❌ Eliminado `GOOGLE_CLIENT_ID` (ya no se usa)
- ✅ Agregado `JWT_SECRET_KEY` para autenticación
- ✅ Agregado `SESSION_EXPIRE_HOURS=24`
- ✅ Configurado `CORS_ORIGINS` para el frontend
- ✅ Actualizado nombres de contenedores con sufijo `-dev`

### **⚠️ Problema actual:**
El emulador de Firestore no está configurándose correctamente. Está usando IPv6 en lugar de IPv4.

## 🔧 **Para usar la configuración simplificada:**

Mientras solucionamos Docker, puedes usar la configuración local que creé:

### **Opción 1: Desarrollo local (más simple)**
```bash
# 1. Instalar Firebase CLI
npm install -g firebase-tools

# 2. Iniciar emulador local
./backend/scripts/start_firestore_emulator.sh

# 3. En otra terminal, configurar BD
cd backend
python scripts/setup_firestore.py

# 4. Iniciar backend
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8080

# 5. Iniciar frontend
cd ../frontend
ng serve
```

### **Opción 2: Solo usar servicios auxiliares de Docker**
```bash
# Usar solo Redis y MailHog de Docker
docker run -d --name redis-dev -p 6379:6379 redis:7-alpine
docker run -d --name mailhog-dev -p 1025:1025 -p 8025:8025 mailhog/mailhog

# Y correr backend/frontend localmente como en Opción 1
```

## 🎯 **Lo que funciona actualmente:**
- ✅ **Backend**: Configuración actualizada con JWT
- ✅ **Autenticación**: Email/password con bcrypt
- ✅ **Frontend**: Formularios de login/registro
- ✅ **Documentación**: Políticas actualizadas

## 🔄 **Próximos pasos:**
1. **Probar con configuración local** (más rápido)
2. **Corregir Docker Firestore** (para entorno completo)

¿Prefieres probar primero con la configuración local para verificar que todo funciona?