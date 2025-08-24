#!/bin/bash

# Script para inicializar la base de datos Firestore con datos de ejemplo
# Uso: ./scripts/init_db.sh

set -e  # Salir en caso de error

echo "🔥 Financial Nomad - Inicialización de Base de Datos"
echo "=================================================="

# Verificar que estamos en el directorio correcto
if [ ! -f "src/main.py" ]; then
    echo "❌ Error: Ejecuta este script desde el directorio backend/"
    exit 1
fi

# Verificar que existe el script de Python
if [ ! -f "scripts/init_database.py" ]; then
    echo "❌ Error: No se encuentra el script scripts/init_database.py"
    exit 1
fi

# Verificar variables de entorno
if [ -z "$PYTHONPATH" ]; then
    echo "🔧 Configurando PYTHONPATH..."
    export PYTHONPATH=$(pwd)
fi

echo "📦 Verificando dependencias..."

# Verificar que Python está disponible
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 no está instalado"
    exit 1
fi

echo "🚀 Ejecutando inicialización de base de datos..."
echo ""

# Ejecutar el script de inicialización
python3 scripts/init_database.py

echo ""
echo "✅ Script de inicialización completado"
echo "🌐 La API está disponible en: http://localhost:8080"
echo "📚 Documentación de la API: http://localhost:8080/docs"