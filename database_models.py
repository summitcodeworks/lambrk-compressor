"""
Database models for Lambrk Video Compressor
"""
import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
import os

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
    """Database connection and session management"""
    
    def __init__(self, database_url=None):
        if database_url is None:
            # Default to local PostgreSQL
            database_url = os.getenv(
                'DATABASE_URL', 
                'postgresql://postgres:password@localhost:5432/lambrk_compressor'
            )
        
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def create_tables(self):
        """Create all database tables"""
        Base.metadata.create_all(bind=self.engine)
        
    def get_session(self):
        """Get a database session"""
        return self.SessionLocal()
    
    def init_database(self):
        """Initialize database with tables"""
        try:
            self.create_tables()
            print("Database tables created successfully!")
            return True
        except Exception as e:
            print(f"Error creating database tables: {e}")
            return False

# Global database manager instance
db_manager = None

def get_db_manager():
    """Get the global database manager instance"""
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager()
    return db_manager

def init_database():
    """Initialize the database"""
    return get_db_manager().init_database() 