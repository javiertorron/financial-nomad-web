#!/bin/bash

# Script para actualizar Google Client ID rápidamente
# Uso: ./actualizar_client_id.sh "tu-nuevo-client-id.apps.googleusercontent.com"

if [ -z "$1" ]; then
    echo "❌ Error: Debes proporcionar el Client ID"
    echo "Uso: $0 \"123456789-abc123.apps.googleusercontent.com\""
    exit 1
fi

NEW_CLIENT_ID="$1"
COMPOSE_FILE="devops/docker-compose/docker-compose.dev.yml"

echo "🔄 Actualizando Google Client ID..."
echo "📝 Nuevo Client ID: $NEW_CLIENT_ID"

# Verificar que el archivo existe
if [ ! -f "$COMPOSE_FILE" ]; then
    echo "❌ Error: No se encontró $COMPOSE_FILE"
    exit 1
fi

# Crear backup
cp "$COMPOSE_FILE" "$COMPOSE_FILE.backup.$(date +%Y%m%d_%H%M%S)"
echo "💾 Backup creado: $COMPOSE_FILE.backup.$(date +%Y%m%d_%H%M%S)"

# Actualizar Client ID en frontend
sed -i "s|GOOGLE_CLIENT_ID=.*|GOOGLE_CLIENT_ID=$NEW_CLIENT_ID|g" "$COMPOSE_FILE"

# Actualizar Client ID en backend  
sed -i "s|GOOGLE_CLIENT_ID=.*|GOOGLE_CLIENT_ID=$NEW_CLIENT_ID|g" "$COMPOSE_FILE"

echo "✅ Client ID actualizado en $COMPOSE_FILE"

# Reiniciar servicios
echo "🔄 Reiniciando servicios..."
docker compose -f "$COMPOSE_FILE" down
docker compose -f "$COMPOSE_FILE" up -d

echo "🎉 ¡Listo! Los servicios se están reiniciando con el nuevo Client ID."
echo "📱 Accede a http://localhost:4200 en unos minutos"
echo ""
echo "🔍 Para verificar que se cargó correctamente:"
echo "   curl -s http://localhost:8080/api/v1/config | grep googleClientId"