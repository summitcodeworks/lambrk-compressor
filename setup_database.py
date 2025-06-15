#!/usr/bin/env python
"""
Database Setup Script for Lambrk Video Compressor
This script helps set up the PostgreSQL database and tables
"""
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError

def create_database_if_not_exists(database_url, database_name):
    """Create the database if it doesn't exist"""
    try:
        # Connect to PostgreSQL server (not specific database)
        postgres_url = database_url.replace(f"/{database_name}", "/postgres")
        engine = create_engine(postgres_url)
        
        with engine.connect() as conn:
            # Check if database exists
            result = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname = '{database_name}'"))
            if not result.fetchone():
                # Create database
                conn.execute(text("COMMIT"))  # End any existing transaction
                conn.execute(text(f"CREATE DATABASE {database_name}"))
                print(f"✅ Database '{database_name}' created successfully!")
            else:
                print(f"✅ Database '{database_name}' already exists")
        
        engine.dispose()
        return True
        
    except Exception as e:
        print(f"❌ Error creating database: {e}")
        return False

def setup_database():
    """Set up the complete database with tables"""
    print("🚀 Starting Lambrk Video Compressor Database Setup")
    print("=" * 50)
    
    # Get database configuration
    database_host = input("Enter PostgreSQL host (default: localhost): ").strip() or "localhost"
    database_port = input("Enter PostgreSQL port (default: 5432): ").strip() or "5432"
    database_user = input("Enter PostgreSQL username (default: postgres): ").strip() or "postgres"
    database_password = input("Enter PostgreSQL password: ").strip()
    database_name = input("Enter database name (default: lambrk_compressor): ").strip() or "lambrk_compressor"
    
    # Construct database URL
    database_url = f"postgresql://{database_user}:{database_password}@{database_host}:{database_port}/{database_name}"
    
    print(f"\n📝 Database URL: postgresql://{database_user}:***@{database_host}:{database_port}/{database_name}")
    
    # Test connection to PostgreSQL server
    print("\n🔌 Testing PostgreSQL connection...")
    try:
        postgres_url = f"postgresql://{database_user}:{database_password}@{database_host}:{database_port}/postgres"
        test_engine = create_engine(postgres_url)
        with test_engine.connect():
            print("✅ PostgreSQL connection successful!")
        test_engine.dispose()
    except Exception as e:
        print(f"❌ Failed to connect to PostgreSQL: {e}")
        print("Please check your PostgreSQL installation and credentials.")
        return False
    
    # Create database if it doesn't exist
    print(f"\n🗃️ Creating database '{database_name}' if needed...")
    if not create_database_if_not_exists(database_url, database_name):
        return False
    
    # Create tables using our models
    print("\n📋 Creating database tables...")
    try:
        from database_models import DatabaseManager
        
        db_manager = DatabaseManager(database_url)
        if db_manager.init_database():
            print("✅ Database tables created successfully!")
        else:
            print("❌ Failed to create database tables")
            return False
            
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False
    
    # Create environment configuration
    print("\n⚙️ Creating environment configuration...")
    env_content = f"""# Lambrk Video Compressor Database Configuration
DATABASE_URL=postgresql://{database_user}:{database_password}@{database_host}:{database_port}/{database_name}

# Alternative format for connection components
DB_HOST={database_host}
DB_PORT={database_port}
DB_USER={database_user}
DB_PASSWORD={database_password}
DB_NAME={database_name}
"""
    
    try:
        with open('.env', 'w') as f:
            f.write(env_content)
        print("✅ Environment file (.env) created!")
        print("   You can modify database settings in this file if needed.")
    except Exception as e:
        print(f"⚠️ Warning: Could not create .env file: {e}")
    
    # Test the complete setup
    print("\n🧪 Testing complete database setup...")
    try:
        from crud_service import get_crud_service
        
        crud = get_crud_service()
        
        # Test creating a sample job
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
        else:
            print("❌ Database CRUD test failed")
            return False
            
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 Database setup completed successfully!")
    print("\nNext steps:")
    print("1. Run: python video_compression.py")
    print("2. The application will automatically connect to your database")
    print("3. Use 'View Jobs History' to see all compression jobs")
    print("\n📊 Database Features Available:")
    print("• Job tracking and history")
    print("• Video file management")
    print("• Task progress monitoring")
    print("• System resource metrics")
    print("• Complete CRUD operations")
    
    return True

def check_dependencies():
    """Check if required dependencies are installed"""
    print("🔍 Checking dependencies...")
    
    required_packages = [
        ('psycopg2', 'psycopg2-binary'),
        ('sqlalchemy', 'sqlalchemy'),
        ('alembic', 'alembic')
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
    print("🎬 Lambrk Video Compressor - Database Setup")
    print("This script will help you set up PostgreSQL for video compression tracking")
    print()
    
    # Check dependencies first
    if not check_dependencies():
        print("\n❌ Please install missing dependencies and run this script again.")
        sys.exit(1)
    
    # Run database setup
    if setup_database():
        print("\n✨ Setup completed! You can now run the video compressor with full database support.")
        sys.exit(0)
    else:
        print("\n❌ Setup failed. Please check the errors above and try again.")
        sys.exit(1)

if __name__ == "__main__":
    main() 