"""
Database models for Lambrk Video Compressor
"""
import datetime
import os
import sys
from typing import Optional, Dict, Any
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, JSON, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from sqlalchemy.exc import OperationalError, ProgrammingError

Base = declarative_base()

class CompressionJob(Base):
    """Model for tracking video compression jobs"""
    __tablename__ = 'compression_jobs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_name = Column(String(255), nullable=False)
    input_folder = Column(String(500), nullable=False)
    output_folder = Column(String(500), nullable=False)
    status = Column(String(50), default='pending')  # pending, processing, completed, failed, cancelled
    created_at = Column(DateTime, default=func.now())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    total_videos = Column(Integer, default=0)
    processed_videos = Column(Integer, default=0)
    failed_videos = Column(Integer, default=0)
    total_tasks = Column(Integer, default=0)
    completed_tasks = Column(Integer, default=0)
    concurrent_workers = Column(Integer, default=1)
    dolby_atmos_enabled = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    
    # Relationships
    videos = relationship("VideoFile", back_populates="job")
    tasks = relationship("CompressionTask", back_populates="job")
    metrics = relationship("SystemMetrics", back_populates="job")
    
    def __repr__(self):
        return f"<CompressionJob(id={self.id}, name='{self.job_name}', status='{self.status}')>"
    
    @property
    def duration_seconds(self):
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    @property
    def progress_percentage(self):
        if self.total_tasks > 0:
            return (self.completed_tasks / self.total_tasks) * 100
        return 0

class VideoFile(Base):
    """Model for tracking individual video files"""
    __tablename__ = 'video_files'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey('compression_jobs.id'), nullable=False)
    filename = Column(String(500), nullable=False)
    filepath = Column(String(1000), nullable=False)
    original_size_mb = Column(Float, nullable=True)
    original_width = Column(Integer, nullable=True)
    original_height = Column(Integer, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    is_portrait = Column(Boolean, default=False)
    status = Column(String(50), default='pending')  # pending, processing, completed, failed
    processed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Relationships
    job = relationship("CompressionJob", back_populates="videos")
    tasks = relationship("CompressionTask", back_populates="video")
    
    def __repr__(self):
        return f"<VideoFile(id={self.id}, filename='{self.filename}', status='{self.status}')>"

class CompressionTask(Base):
    """Model for tracking individual compression tasks (video + quality combination)"""
    __tablename__ = 'compression_tasks'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey('compression_jobs.id'), nullable=False)
    video_id = Column(Integer, ForeignKey('video_files.id'), nullable=False)
    quality_profile = Column(String(100), nullable=False)  # e.g., "1920x1080_2000k"
    bitrate = Column(String(20), nullable=False)
    resolution = Column(String(20), nullable=False)
    hdr_metadata = Column(JSON, nullable=True)
    status = Column(String(50), default='pending')  # pending, processing, completed, failed
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    output_filepath = Column(String(1000), nullable=True)
    output_size_mb = Column(Float, nullable=True)
    compression_ratio = Column(Float, nullable=True)
    worker_id = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    ffmpeg_command = Column(Text, nullable=True)
    
    # Relationships
    job = relationship("CompressionJob", back_populates="tasks")
    video = relationship("VideoFile", back_populates="tasks")
    
    def __repr__(self):
        return f"<CompressionTask(id={self.id}, quality='{self.quality_profile}', status='{self.status}')>"
    
    @property
    def duration_seconds(self):
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

class SystemMetrics(Base):
    """Model for tracking system resource usage during compression"""
    __tablename__ = 'system_metrics'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey('compression_jobs.id'), nullable=True)
    timestamp = Column(DateTime, default=func.now())
    cpu_percent = Column(Float, nullable=False)
    memory_percent = Column(Float, nullable=False)
    active_workers = Column(Integer, nullable=False)
    pending_tasks = Column(Integer, default=0)
    completed_tasks = Column(Integer, default=0)
    
    # Relationships
    job = relationship("CompressionJob", back_populates="metrics")
    
    def __repr__(self):
        return f"<SystemMetrics(id={self.id}, cpu={self.cpu_percent}%, memory={self.memory_percent}%)>"

class DatabaseManager:
    """
    Comprehensive Database Manager for Lambrk Video Compressor
    Handles all database connections, setup, initialization, and configuration in one place
    """
    
    def __init__(self, database_url: Optional[str] = None, 
                 host: Optional[str] = None, port: Optional[str] = None,
                 user: Optional[str] = None, password: Optional[str] = None,
                 database: Optional[str] = None):
        """
        Initialize database manager with flexible configuration options
        
        Args:
            database_url: Complete database URL (takes precedence if provided)
            host, port, user, password, database: Individual connection parameters
        """
        self.database_url = self._build_database_url(database_url, host, port, user, password, database)
        self.engine = None
        self.SessionLocal = None
        self._initialize_engine()
    
    def _build_database_url(self, database_url: Optional[str] = None,
                           host: Optional[str] = None, port: Optional[str] = None,
                           user: Optional[str] = None, password: Optional[str] = None,
                           database: Optional[str] = None) -> str:
        """Build database URL from various input methods"""
        
        # If complete URL provided, use it
        if database_url:
            return database_url
        
        # Try to get from environment variables first
        env_url = os.getenv('DATABASE_URL')
        if env_url:
            return env_url
        
        # Build from individual parameters or environment variables
        host = host or os.getenv('DB_HOST', 'localhost')
        port = port or os.getenv('DB_PORT', '5432')
        user = user or os.getenv('DB_USER', 'postgres')
        password = password or os.getenv('DB_PASSWORD', 'password')
        database = database or os.getenv('DB_NAME', 'lambrk')
        
        return f"postgresql://{user}:{password}@{host}:{port}/{database}"
    
    def _initialize_engine(self):
        """Initialize SQLAlchemy engine and session factory"""
        try:
            self.engine = create_engine(self.database_url, echo=False)
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        except Exception as e:
            print(f"❌ Error initializing database engine: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            print(f"❌ Database connection test failed: {e}")
            return False
    
    def create_database_if_not_exists(self) -> bool:
        """Create the database if it doesn't exist (PostgreSQL only)"""
        try:
            # Extract database name from URL
            database_name = self.database_url.split('/')[-1]
            
            # Connect to PostgreSQL server (not specific database)
            postgres_url = self.database_url.replace(f"/{database_name}", "/postgres")
            postgres_engine = create_engine(postgres_url)
            
            with postgres_engine.connect() as conn:
                # Check if database exists
                result = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname = '{database_name}'"))
                if not result.fetchone():
                    # Create database
                    conn.execute(text("COMMIT"))  # End any existing transaction
                    conn.execute(text(f"CREATE DATABASE {database_name}"))
                    print(f"✅ Database '{database_name}' created successfully!")
                else:
                    print(f"✅ Database '{database_name}' already exists")
            
            postgres_engine.dispose()
            return True
            
        except Exception as e:
            print(f"❌ Error creating database: {e}")
            return False
    
    def create_tables(self) -> bool:
        """Create all database tables if they don't exist"""
        try:
            # Check which tables already exist
            existing_tables = set()
            with self.engine.connect() as conn:
                try:
                    # Get list of existing tables
                    result = conn.execute(text("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = 'public'
                    """))
                    existing_tables = {row[0] for row in result}
                except Exception as e:
                    print(f"⚠️ Could not query existing tables: {e}")
            
            # Get all table names that should exist
            expected_tables = {table.name for table in Base.metadata.tables.values()}
            
            # Determine which tables need to be created
            tables_to_create = expected_tables - existing_tables
            
            if existing_tables & expected_tables:
                print(f"✅ Found existing tables: {', '.join(existing_tables & expected_tables)}")
            
            if tables_to_create:
                print(f"🔄 Creating new tables: {', '.join(tables_to_create)}")
            else:
                print("✅ All required tables already exist")
            
            # Create all tables (SQLAlchemy's create_all only creates missing tables)
            Base.metadata.create_all(bind=self.engine)
            
            if tables_to_create:
                print("✅ New database tables created successfully!")
            else:
                print("✅ Database tables verification completed!")
            
            return True
        except Exception as e:
            print(f"❌ Error creating database tables: {e}")
            return False
    
    def get_session(self):
        """Get a database session"""
        if not self.SessionLocal:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self.SessionLocal()
    
    def initialize(self, create_database: bool = True, create_tables: bool = True) -> bool:
        """
        Complete database initialization
        
        Args:
            create_database: Whether to create the database if it doesn't exist
            create_tables: Whether to create tables
        """
        try:
            # Test basic connection to PostgreSQL server
            if create_database:
                if not self.create_database_if_not_exists():
                    return False
            
            # Test connection to our specific database
            if not self.test_connection():
                print("❌ Failed to connect to database after creation")
                return False
            
            # Create tables
            if create_tables:
                if not self.create_tables():
                    return False
            
            print("✅ Database initialization completed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
            return False
    
    def create_env_file(self) -> bool:
        """Create .env file with current database configuration"""
        try:
            # Parse URL to get components
            url_parts = self.database_url.replace('postgresql://', '').split('@')
            user_pass = url_parts[0].split(':')
            host_port_db = url_parts[1].split('/')
            host_port = host_port_db[0].split(':')
            
            user = user_pass[0]
            password = user_pass[1] if len(user_pass) > 1 else ''
            host = host_port[0]
            port = host_port[1] if len(host_port) > 1 else '5432'
            database = host_port_db[1] if len(host_port_db) > 1 else ''
            
            env_content = f"""# Lambrk Video Compressor Database Configuration
DATABASE_URL={self.database_url}

# Alternative format for connection components
DB_HOST={host}
DB_PORT={port}
DB_USER={user}
DB_PASSWORD={password}
DB_NAME={database}
"""
            
            with open('.env', 'w') as f:
                f.write(env_content)
            print("✅ Environment file (.env) created!")
            return True
            
        except Exception as e:
            print(f"⚠️ Warning: Could not create .env file: {e}")
            return False
    
    def get_connection_info(self) -> Dict[str, str]:
        """Get connection information for display"""
        try:
            url_parts = self.database_url.replace('postgresql://', '').split('@')
            user_pass = url_parts[0].split(':')
            host_port_db = url_parts[1].split('/')
            host_port = host_port_db[0].split(':')
            
            return {
                'user': user_pass[0],
                'host': host_port[0],
                'port': host_port[1] if len(host_port) > 1 else '5432',
                'database': host_port_db[1] if len(host_port_db) > 1 else '',
                'url_masked': f"postgresql://{user_pass[0]}:***@{host_port[0]}:{host_port[1] if len(host_port) > 1 else '5432'}/{host_port_db[1] if len(host_port_db) > 1 else ''}"
            }
        except:
            return {'error': 'Could not parse connection info'}
    
    def close(self):
        """Close database connections"""
        if self.engine:
            self.engine.dispose()
    
    def init_database(self):
        """Legacy method name for backwards compatibility"""
        return self.initialize(create_database=True, create_tables=True)

# Global database manager instance
_db_manager: Optional[DatabaseManager] = None

def get_db_manager(database_url: Optional[str] = None, **kwargs) -> DatabaseManager:
    """
    Get the global database manager instance
    
    Args:
        database_url: Database URL (only used on first call)
        **kwargs: Additional connection parameters (only used on first call)
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(database_url=database_url, **kwargs)
    return _db_manager

def initialize_database(database_url: Optional[str] = None, **kwargs) -> bool:
    """
    Initialize the database with full setup
    
    Args:
        database_url: Database URL
        **kwargs: Additional connection parameters
    """
    db_manager = get_db_manager(database_url=database_url, **kwargs)
    return db_manager.initialize()

def reset_db_manager():
    """Reset the global database manager (useful for testing)"""
    global _db_manager
    if _db_manager:
        _db_manager.close()
    _db_manager = None

# Backwards compatibility functions
def init_database():
    """Legacy function for backwards compatibility"""
    return initialize_database() 