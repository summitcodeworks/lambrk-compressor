#!/usr/bin/env python
"""
Database Setup Script for Lambrk Video Compressor
Simple unified setup using the consolidated DatabaseManager
"""
import sys
from database_models import DatabaseManager, initialize_database

def interactive_setup():
    """Interactive database setup with user input"""
    print("🚀 Lambrk Video Compressor - Database Setup")
    print("=" * 50)
    
    # Get database configuration from user
    print("\n📝 Enter your PostgreSQL connection details:")
    host = input("Host (default: localhost): ").strip() or "localhost"
    port = input("Port (default: 5432): ").strip() or "5432"
    user = input("Username (default: postgres): ").strip() or "postgres"
    password = input("Password: ").strip() or "password"
    database = input("Database name (default: lambrk_compressor): ").strip() or "lambrk_compressor"
    
    # Create database manager with user inputs
    try:
        db_manager = DatabaseManager(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database
        )
        
        # Display connection info
        conn_info = db_manager.get_connection_info()
        print(f"\n📝 Connection: {conn_info['url_masked']}")
        
        # Initialize everything
        print("\n🔧 Setting up database...")
        if db_manager.initialize():
            # Create .env file
            db_manager.create_env_file()
            
            # Test with CRUD operations
            print("\n🧪 Testing database operations...")
            if test_crud_operations(db_manager):
                print("\n" + "=" * 50)
                print("🎉 Database setup completed successfully!")
                print("\nNext steps:")
                print("1. Run: python video_compression.py")
                print("2. The application will automatically use your database")
                print("3. Use 'View Jobs History' to see all compression jobs")
                return True
            else:
                print("❌ Database operations test failed")
                return False
        else:
            print("❌ Database setup failed")
            return False
            
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        return False

def quick_setup():
    """Quick setup with default settings"""
    print("🚀 Quick Database Setup (using defaults)")
    print("=" * 40)
    
    try:
        # Use default settings
        if initialize_database():
            print("✅ Database setup completed with defaults!")
            print("Default connection: postgresql://postgres:password@localhost:5432/lambrk_compressor")
            return True
        else:
            print("❌ Quick setup failed")
            return False
    except Exception as e:
        print(f"❌ Quick setup failed: {e}")
        return False

def test_crud_operations(db_manager):
    """Test basic CRUD operations"""
    try:
        from crud_service import CRUDService
        
        # Reset global manager to use our configured one
        from database_models import reset_db_manager
        reset_db_manager()
        
        # Create CRUD service
        crud = CRUDService()
        
        # Test creating a job
        job = crud.jobs.create_job(
            job_name="Database Setup Test",
            input_folder="/test/input",
            output_folder="/test/output"
        )
        
        if job:
            print("✅ Database CRUD operations working!")
            # Clean up test job
            crud.jobs.delete_job(job.id)
            print("✅ Test data cleaned up")
            return True
        else:
            print("❌ Could not create test job")
            return False
            
    except Exception as e:
        print(f"❌ CRUD test failed: {e}")
        return False

def check_dependencies():
    """Check if required dependencies are installed"""
    print("🔍 Checking dependencies...")
    
    required_packages = [
        ('psycopg2', 'psycopg2-binary'),
        ('sqlalchemy', 'sqlalchemy'),
    ]
    
    missing_packages = []
    
    for package, pip_name in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} is installed")
        except ImportError:
            print(f"❌ {package} is missing")
            missing_packages.append(pip_name)
    
    if missing_packages:
        print(f"\n📦 Please install missing packages:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    print("✅ All dependencies are installed!")
    return True

def main():
    """Main setup function"""
    if not check_dependencies():
        print("\n❌ Please install missing dependencies and run this script again.")
        sys.exit(1)
    
    print("\nChoose setup method:")
    print("1. Interactive setup (recommended)")
    print("2. Quick setup with defaults")
    
    choice = input("\nEnter choice (1 or 2): ").strip()
    
    success = False
    if choice == "2":
        success = quick_setup()
    else:
        success = interactive_setup()
    
    if success:
        print("\n✨ Setup completed! You can now run the video compressor with full database support.")
        sys.exit(0)
    else:
        print("\n❌ Setup failed. Please check the errors above and try again.")
        sys.exit(1)

if __name__ == "__main__":
    main() 