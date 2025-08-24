#!/usr/bin/env python3
"""
Script para configurar Firestore y crear el usuario maestro inicial.
"""
import asyncio
import os
import sys
from pathlib import Path

# Cargar variables de entorno desde .env
from dotenv import load_dotenv
load_dotenv()

# Agregar el directorio backend al path para imports
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from src.config import get_settings
from src.infrastructure.firestore import get_firestore
from src.services.auth import get_auth_service


async def setup_firestore():
    """Configurar Firestore y crear el usuario maestro."""
    print("🔥 Configurando Firestore para Financial Nomad...")
    
    try:
        # Verificar configuración
        settings = get_settings()
        print(f"📋 Configuración:")
        print(f"   - Proyecto: {settings.firestore_project_id}")
        print(f"   - Emulador: {'Sí' if settings.use_firestore_emulator else 'No'}")
        if settings.use_firestore_emulator:
            print(f"   - Host emulador: {settings.firestore_emulator_host}")
        
        # Probar conexión a Firestore
        firestore_service = get_firestore()
        print("✅ Conexión a Firestore establecida")
        
        # Crear el usuario maestro
        auth_service = get_auth_service()
        print("👤 Creando usuario maestro...")
        
        master_user = await auth_service.create_master_user()
        print(f"✅ Usuario maestro creado:")
        print(f"   - ID: {master_user.id}")
        print(f"   - Email: {master_user.email}")
        print(f"   - Nombre: {master_user.name}")
        print(f"   - Rol: {master_user.role}")
        
        print("🎉 ¡Configuración completada!")
        print("\n📝 Credenciales del usuario maestro:")
        print(f"   Email: {master_user.email}")
        print(f"   Contraseña: fI07.08511982#")
        
    except Exception as e:
        print(f"❌ Error durante la configuración: {e}")
        sys.exit(1)


async def check_environment():
    """Verificar variables de entorno necesarias."""
    print("🔍 Verificando variables de entorno...")
    
    required_vars = [
        "FIRESTORE_PROJECT_ID",
        "JWT_SECRET_KEY"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Variables de entorno faltantes: {', '.join(missing_vars)}")
        print("\n📋 Crea un archivo .env con las siguientes variables:")
        for var in missing_vars:
            if var == "JWT_SECRET_KEY":
                print(f"{var}=tu-clave-secreta-jwt-muy-segura")
            elif var == "FIRESTORE_PROJECT_ID":
                print(f"{var}=tu-proyecto-firestore")
        print("\n💡 Puedes usar .env.example como plantilla")
        return False
    
    print("✅ Variables de entorno configuradas")
    return True


async def main():
    """Función principal."""
    print("🚀 Setup de Firestore para Financial Nomad")
    print("=" * 50)
    
    # Verificar variables de entorno
    if not await check_environment():
        sys.exit(1)
    
    print()
    
    # Configurar Firestore
    await setup_firestore()
    
    print("\n" + "=" * 50)
    print("✨ Setup completado. Ya puedes:")
    print("1. Iniciar el backend: python -m uvicorn src.main:app --reload")
    print("2. Iniciar el frontend: ng serve")
    print("3. Hacer login con las credenciales del usuario maestro")


if __name__ == "__main__":
    asyncio.run(main())