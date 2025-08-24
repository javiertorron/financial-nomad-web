#!/bin/bash

# Script para iniciar el emulador de Firestore
echo "🔥 Iniciando emulador de Firestore..."

# Verificar si Firebase CLI está instalado
if ! command -v firebase &> /dev/null; then
    echo "❌ Firebase CLI no está instalado"
    echo "📦 Instala Firebase CLI:"
    echo "   npm install -g firebase-tools"
    exit 1
fi

# Verificar si los puertos están libres
for port in 8082 4002; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
        echo "⚠️  El puerto $port ya está en uso"
        echo "🔄 Matando procesos en el puerto $port..."
        lsof -ti:$port | xargs kill -9 2>/dev/null || true
    fi
done

echo "🚀 Iniciando emulador en puerto 8082..."
echo "🌐 UI del emulador: http://localhost:4002"
echo "📡 Endpoint del emulador: localhost:8082"
echo ""
echo "💡 Para detener el emulador presiona Ctrl+C"
echo ""

# Iniciar el emulador
firebase emulators:start --project financial-nomad-web
