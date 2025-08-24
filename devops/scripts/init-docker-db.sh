#!/bin/bash

# Script para inicializar la base de datos en Docker
echo "🐳 Inicializando base de datos en Docker..."

# Esperar a que el backend esté saludable
echo "⏳ Esperando a que el backend esté listo..."
until curl -f http://localhost:8080/api/v1/health > /dev/null 2>&1; do
    echo "   Backend no está listo, esperando 5 segundos..."
    sleep 5
done

echo "✅ Backend está listo"

# Crear usuario maestro
echo "👤 Creando usuario maestro..."
response=$(curl -s -X POST http://localhost:8080/api/v1/auth/init-master)

if echo "$response" | grep -q "error"; then
    echo "⚠️  Error al crear usuario maestro:"
    echo "$response"
else
    echo "✅ Usuario maestro creado correctamente"
    echo "$response" | jq . 2>/dev/null || echo "$response"
fi

echo ""
echo "🎉 ¡Configuración de Docker completada!"
echo ""
echo "📝 Credenciales del usuario maestro:"
echo "   Email: javier.torron.diaz@gmail.com"
echo "   Contraseña: fI07.08511982#"
echo ""
echo "🌐 Servicios disponibles:"
echo "   - Frontend: http://localhost:4200"
echo "   - Backend API: http://localhost:8080/docs"
echo "   - Firestore UI: http://localhost:4000"
echo "   - MailHog: http://localhost:8025"
echo "   - Redis: localhost:6379"