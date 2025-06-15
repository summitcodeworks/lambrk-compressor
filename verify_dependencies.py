#!/usr/bin/env python3
"""
Dependency Verification Script for Lambrk Video Compressor
This script checks that all required dependencies are installed and working properly.
"""

import sys
import importlib

def check_dependency(module_name, package_name=None, description=""):
    """Check if a dependency is available and working"""
    if package_name is None:
        package_name = module_name
    
    try:
        module = importlib.import_module(module_name)
        version = getattr(module, '__version__', 'Unknown')
        print(f"✅ {package_name:<20} {version:<15} - {description}")
        return True
    except ImportError as e:
        print(f"❌ {package_name:<20} {'MISSING':<15} - {description}")
        print(f"   Error: {e}")
        return False

def check_builtin_modules():
    """Check built-in Python modules used by the application"""
    print("🔍 Checking Built-in Python Modules:")
    builtin_modules = [
        ('tkinter', 'tkinter', 'GUI framework'),
        ('threading', 'threading', 'Multi-threading support'),
        ('multiprocessing', 'multiprocessing', 'Process management'),
        ('concurrent.futures', 'concurrent.futures', 'Concurrent execution'),
        ('subprocess', 'subprocess', 'External process execution'),
        ('os', 'os', 'Operating system interface'),
        ('json', 'json', 'JSON handling'),
        ('time', 'time', 'Time operations'),
        ('datetime', 'datetime', 'Date and time handling'),
        ('random', 'random', 'Random number generation'),
        ('tempfile', 'tempfile', 'Temporary file creation'),
    ]
    
    all_available = True
    for module, package, desc in builtin_modules:
        if not check_dependency(module, package, desc):
            all_available = False
    
    return all_available

def check_external_dependencies():
    """Check external dependencies from requirements.txt"""
    print("\n🔍 Checking External Dependencies:")
    external_deps = [
        ('psutil', 'psutil', 'System resource monitoring'),
        ('psycopg2', 'psycopg2-binary', 'PostgreSQL database connectivity'),
        ('sqlalchemy', 'sqlalchemy', 'ORM and database operations'),
        ('alembic', 'alembic', 'Database migrations'),
        ('typing_extensions', 'typing-extensions', 'Extended type hints'),
        ('dotenv', 'python-dotenv', 'Environment file support'),
    ]
    
    all_available = True
    for module, package, desc in external_deps:
        if not check_dependency(module, package, desc):
            all_available = False
    
    return all_available

def check_application_imports():
    """Check if our application modules can be imported"""
    print("\n🔍 Checking Application Modules:")
    app_modules = [
        ('database_models', 'Database Models'),
        ('crud_service', 'CRUD Service Layer'),
        ('video_compression', 'Main Application'),
    ]
    
    all_available = True
    for module, desc in app_modules:
        try:
            importlib.import_module(module)
            print(f"✅ {module:<20} {'OK':<15} - {desc}")
        except ImportError as e:
            print(f"❌ {module:<20} {'FAILED':<15} - {desc}")
            print(f"   Error: {e}")
            all_available = False
    
    return all_available

def check_optional_tools():
    """Check optional tools that enhance functionality"""
    print("\n🔍 Checking Optional Tools:")
    optional_tools = [
        ('pytest', 'pytest', 'Testing framework'),
        ('black', 'black', 'Code formatting'),
        ('flake8', 'flake8', 'Code linting'),
    ]
    
    for module, package, desc in optional_tools:
        check_dependency(module, package, f"{desc} (optional)")

def generate_requirements_summary():
    """Generate a summary of current installed packages"""
    print("\n📋 Generating Requirements Summary:")
    try:
        import pkg_resources
        installed_packages = {pkg.project_name.lower(): pkg.version 
                            for pkg in pkg_resources.working_set}
        
        required_packages = [
            'psutil', 'psycopg2-binary', 'sqlalchemy', 'alembic', 
            'typing-extensions', 'python-dotenv'
        ]
        
        print("Current versions of required packages:")
        for package in required_packages:
            # Handle name variations
            names_to_try = [package, package.replace('-', '_'), package.replace('_', '-')]
            found = False
            for name in names_to_try:
                if name.lower() in installed_packages:
                    print(f"  {package}: {installed_packages[name.lower()]}")
                    found = True
                    break
            if not found:
                print(f"  {package}: NOT INSTALLED")
                
    except Exception as e:
        print(f"Error generating summary: {e}")

def main():
    """Main verification function"""
    print("🎬 Lambrk Video Compressor - Dependency Verification")
    print("=" * 60)
    
    # Check Python version
    python_version = sys.version_info
    print(f"🐍 Python Version: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    if python_version < (3, 6):
        print("❌ Python 3.6+ is required!")
        return False
    else:
        print("✅ Python version is compatible")
    
    print()
    
    # Run all checks
    builtin_ok = check_builtin_modules()
    external_ok = check_external_dependencies()
    app_ok = check_application_imports()
    
    # Check optional tools
    check_optional_tools()
    
    # Generate summary
    generate_requirements_summary()
    
    # Final result
    print("\n" + "=" * 60)
    if builtin_ok and external_ok and app_ok:
        print("🎉 ALL DEPENDENCIES VERIFIED! The application is ready to run.")
        print("\nNext steps:")
        print("1. Run: python setup_database.py  (for PostgreSQL setup)")
        print("2. Run: python video_compression.py  (to start the application)")
        print("3. Run: python test_database.py  (to test database features)")
        return True
    else:
        print("❌ SOME DEPENDENCIES ARE MISSING!")
        print("\nTo install missing dependencies:")
        print("pip install -r requirements.txt")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 