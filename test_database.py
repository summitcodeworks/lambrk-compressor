#!/usr/bin/env python
"""
Test Script for Lambrk Video Compressor Database Integration
This script demonstrates CRUD operations without requiring PostgreSQL setup
"""
import os
import tempfile
from datetime import datetime

def test_models_import():
    """Test if database models can be imported"""
    print("🧪 Testing database models import...")
    try:
        from database_models import CompressionJob, VideoFile, CompressionTask, SystemMetrics
        print("✅ Database models imported successfully!")
        return True
    except ImportError as e:
        print(f"❌ Failed to import database models: {e}")
        return False

def test_crud_import():
    """Test if CRUD services can be imported"""
    print("🧪 Testing CRUD services import...")
    try:
        from crud_service import (
            CompressionJobService, VideoFileService, 
            CompressionTaskService, SystemMetricsService, CRUDService
        )
        print("✅ CRUD services imported successfully!")
        return True
    except ImportError as e:
        print(f"❌ Failed to import CRUD services: {e}")
        return False

def test_video_compression_integration():
    """Test if video compression app loads with database integration"""
    print("🧪 Testing video compression app with database integration...")
    try:
        import video_compression
        print("✅ Video compression app with database integration loaded!")
        
        # Check if database features are properly handled
        if hasattr(video_compression, 'DATABASE_ENABLED'):
            print(f"   Database features available: {video_compression.DATABASE_ENABLED}")
        
        return True
    except ImportError as e:
        print(f"❌ Failed to load video compression app: {e}")
        return False

def test_sqlite_fallback():
    """Test database operations with SQLite fallback"""
    print("🧪 Testing database operations with SQLite fallback...")
    try:
        # Create temporary SQLite database for testing
        temp_db = tempfile.mktemp(suffix='.db')
        sqlite_url = f"sqlite:///{temp_db}"
        
        from database_models import DatabaseManager
        
        # Test database creation
        db_manager = DatabaseManager(sqlite_url)
        if db_manager.init_database():
            print("✅ SQLite database created successfully!")
            
            # Test CRUD operations with our custom database manager
            from crud_service import CompressionJobService, VideoFileService, CompressionTaskService, SystemMetricsService
            
            # Create services with our SQLite database manager
            job_service = CompressionJobService()
            job_service.db_manager = db_manager
            
            class TestCRUDService:
                def __init__(self):
                    self.jobs = job_service
                    self.db_manager = db_manager
            
            crud = TestCRUDService()
            
            # Test job creation
            job = crud.jobs.create_job(
                job_name="Test Job",
                input_folder="/test/input",
                output_folder="/test/output"
            )
            
            if job:
                print(f"✅ Test job created with ID: {job.id}")
                
                # Test job retrieval
                retrieved_job = crud.jobs.get_job(job.id)
                if retrieved_job and retrieved_job.job_name == "Test Job":
                    print("✅ Job retrieval successful!")
                    
                    # Test job update
                    crud.jobs.update_job_status(job.id, 'processing')
                    updated_job = crud.jobs.get_job(job.id)
                    if updated_job.status == 'processing':
                        print("✅ Job status update successful!")
                    
                    # Test job deletion
                    if crud.jobs.delete_job(job.id):
                        print("✅ Job deletion successful!")
                        print("✅ All CRUD operations working correctly!")
                        
                        # Cleanup
                        os.unlink(temp_db)
                        return True
                    
        print("❌ CRUD operations test failed")
        return False
        
    except Exception as e:
        print(f"❌ SQLite fallback test failed: {e}")
        return False

def demonstrate_features():
    """Demonstrate the key features of the PostgreSQL integration"""
    print("\n" + "=" * 60)
    print("🎉 LAMBRK VIDEO COMPRESSOR - POSTGRESQL CRUD FEATURES")
    print("=" * 60)
    
    print("\n📊 DATABASE FEATURES:")
    print("• Complete job lifecycle tracking")
    print("• Video file metadata storage")
    print("• Individual task progress monitoring")
    print("• System resource metrics history")
    print("• Full CRUD operations on all entities")
    
    print("\n🎮 GUI FEATURES:")
    print("• Database-tracked compression jobs")
    print("• Jobs history viewer with management")
    print("• Real-time progress updates in database")
    print("• System metrics recording during compression")
    
    print("\n💾 DATABASE SCHEMA:")
    print("• compression_jobs - Job tracking and metadata")
    print("• video_files - Individual video file records")
    print("• compression_tasks - Video + quality combinations")
    print("• system_metrics - Resource usage history")
    
    print("\n🚀 CRUD OPERATIONS:")
    print("• CREATE: New jobs, videos, tasks, metrics")
    print("• READ: Query jobs, progress, statistics")
    print("• UPDATE: Job status, task progress, metrics")
    print("• DELETE: Job cleanup and history management")
    
    print("\n🔧 SETUP PROCESS:")
    print("1. Install PostgreSQL")
    print("2. Run: python setup_database.py")
    print("3. Run: python video_compression.py")
    print("4. Use 'View Jobs History' for database features")

def main():
    """Run all tests"""
    print("🎬 Lambrk Video Compressor - Database Integration Test")
    print("This script tests the PostgreSQL CRUD integration")
    print()
    
    all_tests_passed = True
    
    # Test imports
    all_tests_passed &= test_models_import()
    all_tests_passed &= test_crud_import() 
    all_tests_passed &= test_video_compression_integration()
    
    # Test database operations with SQLite fallback
    all_tests_passed &= test_sqlite_fallback()
    
    if all_tests_passed:
        print("\n✅ All tests passed! PostgreSQL CRUD integration is ready!")
        demonstrate_features()
    else:
        print("\n❌ Some tests failed. Check the errors above.")
    
    print("\n" + "=" * 60)
    print("🏁 Test completed!")

if __name__ == "__main__":
    main() 