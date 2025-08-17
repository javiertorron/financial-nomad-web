#!/usr/bin/env python3
"""
Script to verify the project structure is correct.
"""

import os
import sys
from pathlib import Path

def check_file_exists(file_path: str, description: str) -> bool:
    """Check if a file exists."""
    if os.path.exists(file_path):
        print(f"✅ {description}: {file_path}")
        return True
    else:
        print(f"❌ {description}: {file_path} - NOT FOUND")
        return False

def check_directory_exists(dir_path: str, description: str) -> bool:
    """Check if a directory exists."""
    if os.path.isdir(dir_path):
        print(f"✅ {description}: {dir_path}")
        return True
    else:
        print(f"❌ {description}: {dir_path} - NOT FOUND")
        return False

def main():
    """Main verification function."""
    print("🔍 Verifying Financial Nomad Backend Project Structure...")
    print("=" * 60)
    
    # Change to backend directory
    backend_dir = Path(__file__).parent.parent
    os.chdir(backend_dir)
    
    checks_passed = 0
    total_checks = 0
    
    # Core files
    files_to_check = [
        ("src/main.py", "FastAPI main application"),
        ("src/config.py", "Configuration module"),
        ("src/__init__.py", "Source package init"),
        ("requirements.txt", "Main dependencies"),
        ("requirements-test.txt", "Test dependencies"),
        ("requirements-dev.txt", "Development dependencies"),
        ("pyproject.toml", "Project configuration"),
        ("Dockerfile", "Docker configuration"),
        ("docker-compose.yml", "Docker Compose"),
        (".env.example", "Environment template"),
        (".gitignore", "Git ignore rules"),
        ("README.md", "Project documentation"),
    ]
    
    for file_path, description in files_to_check:
        if check_file_exists(file_path, description):
            checks_passed += 1
        total_checks += 1
    
    print("\n" + "=" * 60)
    
    # Directories
    directories_to_check = [
        ("src/models", "Pydantic models"),
        ("src/routers", "FastAPI routers"),
        ("src/services", "Business logic services"),
        ("src/infrastructure", "External service clients"),
        ("src/middleware", "Custom middleware"),
        ("src/utils", "Utility functions"),
        ("tests/unit", "Unit tests"),
        ("tests/integration", "Integration tests"),
        ("tests/e2e", "End-to-end tests"),
        ("tests/factories", "Test data factories"),
        ("tests/mocks", "Test mocks"),
        ("scripts", "Utility scripts"),
        (".github/workflows", "CI/CD workflows"),
    ]
    
    for dir_path, description in directories_to_check:
        if check_directory_exists(dir_path, description):
            checks_passed += 1
        total_checks += 1
    
    print("\n" + "=" * 60)
    
    # Check some key implementation files
    key_files = [
        ("src/utils/exceptions.py", "Custom exceptions"),
        ("src/utils/validators.py", "Custom validators"),
        ("src/utils/constants.py", "Application constants"),
        ("src/middleware/error_handler.py", "Error handling middleware"),
        ("src/middleware/logging.py", "Logging middleware"),
        ("src/middleware/security.py", "Security middleware"),
        ("src/routers/health.py", "Health check endpoints"),
        ("src/routers/auth.py", "Authentication endpoints"),
        ("tests/conftest.py", "Pytest configuration"),
        ("tests/unit/test_config.py", "Configuration tests"),
        ("tests/factories/user_factory.py", "User data factory"),
        ("tests/factories/financial_factory.py", "Financial data factory"),
    ]
    
    for file_path, description in key_files:
        if check_file_exists(file_path, description):
            checks_passed += 1
        total_checks += 1
    
    print("\n" + "=" * 60)
    print(f"📊 SUMMARY: {checks_passed}/{total_checks} checks passed")
    
    if checks_passed == total_checks:
        print("🎉 All structure checks passed! Project is ready for development.")
        return 0
    else:
        print("⚠️  Some files/directories are missing. Please review the structure.")
        return 1

if __name__ == "__main__":
    sys.exit(main())