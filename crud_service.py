"""
CRUD Service Layer for Lambrk Video Compressor
Handles all database operations for compression jobs, videos, tasks, and metrics
"""
import os
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_, or_

from database_models import (
    CompressionJob, VideoFile, CompressionTask, SystemMetrics,
    get_db_manager, Base
)

class CompressionJobService:
    """Service for managing compression jobs"""
    
    def __init__(self):
        self.db_manager = get_db_manager()
    
    def create_job(self, job_name: str, input_folder: str, output_folder: str, 
                   dolby_atmos_enabled: bool = True) -> CompressionJob:
        """Create a new compression job"""
        session = self.db_manager.get_session()
        try:
            job = CompressionJob(
                job_name=job_name,
                input_folder=input_folder,
                output_folder=output_folder,
                dolby_atmos_enabled=dolby_atmos_enabled,
                status='pending'
            )
            session.add(job)
            session.commit()
            session.refresh(job)
            return job
        finally:
            session.close()
    
    def get_job(self, job_id: int) -> Optional[CompressionJob]:
        """Get a compression job by ID"""
        session = self.db_manager.get_session()
        try:
            return session.query(CompressionJob).filter(CompressionJob.id == job_id).first()
        finally:
            session.close()
    
    def get_all_jobs(self, limit: int = 100, offset: int = 0) -> List[CompressionJob]:
        """Get all compression jobs with pagination"""
        session = self.db_manager.get_session()
        try:
            return session.query(CompressionJob)\
                         .order_by(desc(CompressionJob.created_at))\
                         .offset(offset)\
                         .limit(limit)\
                         .all()
        finally:
            session.close()
    
    def get_jobs_by_status(self, status: str) -> List[CompressionJob]:
        """Get jobs by status (pending, processing, completed, failed, cancelled)"""
        session = self.db_manager.get_session()
        try:
            return session.query(CompressionJob)\
                         .filter(CompressionJob.status == status)\
                         .order_by(desc(CompressionJob.created_at))\
                         .all()
        finally:
            session.close()
    
    def update_job_status(self, job_id: int, status: str, error_message: str = None) -> bool:
        """Update job status"""
        session = self.db_manager.get_session()
        try:
            job = session.query(CompressionJob).filter(CompressionJob.id == job_id).first()
            if job:
                job.status = status
                if error_message:
                    job.error_message = error_message
                if status == 'processing' and not job.started_at:
                    job.started_at = datetime.now()
                elif status in ['completed', 'failed', 'cancelled']:
                    job.completed_at = datetime.now()
                session.commit()
                return True
            return False
        finally:
            session.close()
    
    def update_job_progress(self, job_id: int, completed_tasks: int = None, 
                           total_tasks: int = None, concurrent_workers: int = None) -> bool:
        """Update job progress information"""
        session = self.db_manager.get_session()
        try:
            job = session.query(CompressionJob).filter(CompressionJob.id == job_id).first()
            if job:
                if completed_tasks is not None:
                    job.completed_tasks = completed_tasks
                if total_tasks is not None:
                    job.total_tasks = total_tasks
                if concurrent_workers is not None:
                    job.concurrent_workers = concurrent_workers
                session.commit()
                return True
            return False
        finally:
            session.close()
    
    def delete_job(self, job_id: int) -> bool:
        """Delete a compression job and all related data"""
        session = self.db_manager.get_session()
        try:
            job = session.query(CompressionJob).filter(CompressionJob.id == job_id).first()
            if job:
                session.delete(job)
                session.commit()
                return True
            return False
        finally:
            session.close()

class VideoFileService:
    """Service for managing video files"""
    
    def __init__(self):
        self.db_manager = get_db_manager()
    
    def create_video(self, job_id: int, filename: str, filepath: str, 
                    original_size_mb: float = None, original_width: int = None,
                    original_height: int = None, duration_seconds: float = None,
                    is_portrait: bool = False) -> VideoFile:
        """Create a new video file record"""
        session = self.db_manager.get_session()
        try:
            video = VideoFile(
                job_id=job_id,
                filename=filename,
                filepath=filepath,
                original_size_mb=original_size_mb,
                original_width=original_width,
                original_height=original_height,
                duration_seconds=duration_seconds,
                is_portrait=is_portrait,
                status='pending'
            )
            session.add(video)
            session.commit()
            session.refresh(video)
            return video
        finally:
            session.close()
    
    def get_videos_by_job(self, job_id: int) -> List[VideoFile]:
        """Get all videos for a specific job"""
        session = self.db_manager.get_session()
        try:
            return session.query(VideoFile)\
                         .filter(VideoFile.job_id == job_id)\
                         .all()
        finally:
            session.close()
    
    def update_video_status(self, video_id: int, status: str, error_message: str = None) -> bool:
        """Update video processing status"""
        session = self.db_manager.get_session()
        try:
            video = session.query(VideoFile).filter(VideoFile.id == video_id).first()
            if video:
                video.status = status
                if error_message:
                    video.error_message = error_message
                if status in ['completed', 'failed']:
                    video.processed_at = datetime.now()
                session.commit()
                return True
            return False
        finally:
            session.close()

class CompressionTaskService:
    """Service for managing compression tasks"""
    
    def __init__(self):
        self.db_manager = get_db_manager()
    
    def create_task(self, job_id: int, video_id: int, quality_profile: str,
                   bitrate: str, resolution: str, hdr_metadata: dict = None) -> CompressionTask:
        """Create a new compression task"""
        session = self.db_manager.get_session()
        try:
            task = CompressionTask(
                job_id=job_id,
                video_id=video_id,
                quality_profile=quality_profile,
                bitrate=bitrate,
                resolution=resolution,
                hdr_metadata=hdr_metadata,
                status='pending'
            )
            session.add(task)
            session.commit()
            session.refresh(task)
            return task
        finally:
            session.close()
    
    def get_tasks_by_job(self, job_id: int, status: str = None) -> List[CompressionTask]:
        """Get all tasks for a specific job, optionally filtered by status"""
        session = self.db_manager.get_session()
        try:
            query = session.query(CompressionTask).filter(CompressionTask.job_id == job_id)
            if status:
                query = query.filter(CompressionTask.status == status)
            return query.all()
        finally:
            session.close()
    
    def get_pending_tasks(self, job_id: int = None) -> List[CompressionTask]:
        """Get pending tasks, optionally for a specific job"""
        session = self.db_manager.get_session()
        try:
            query = session.query(CompressionTask).filter(CompressionTask.status == 'pending')
            if job_id:
                query = query.filter(CompressionTask.job_id == job_id)
            return query.all()
        finally:
            session.close()
    
    def update_task_status(self, task_id: int, status: str, worker_id: str = None,
                          output_filepath: str = None, output_size_mb: float = None,
                          error_message: str = None, ffmpeg_command: str = None) -> bool:
        """Update task status and related information"""
        session = self.db_manager.get_session()
        try:
            task = session.query(CompressionTask).filter(CompressionTask.id == task_id).first()
            if task:
                task.status = status
                if worker_id:
                    task.worker_id = worker_id
                if output_filepath:
                    task.output_filepath = output_filepath
                if output_size_mb is not None:
                    task.output_size_mb = output_size_mb
                if error_message:
                    task.error_message = error_message
                if ffmpeg_command:
                    task.ffmpeg_command = ffmpeg_command
                
                if status == 'processing' and not task.started_at:
                    task.started_at = datetime.now()
                elif status in ['completed', 'failed']:
                    task.completed_at = datetime.now()
                
                # Calculate compression ratio if we have the data
                if (task.output_size_mb and task.video and 
                    task.video.original_size_mb and task.video.original_size_mb > 0):
                    task.compression_ratio = task.output_size_mb / task.video.original_size_mb
                
                session.commit()
                return True
            return False
        finally:
            session.close()
    
    def get_task_statistics(self, job_id: int = None) -> Dict[str, Any]:
        """Get task statistics for a job or globally"""
        session = self.db_manager.get_session()
        try:
            query = session.query(CompressionTask)
            if job_id:
                query = query.filter(CompressionTask.job_id == job_id)
            
            total_tasks = query.count()
            completed_tasks = query.filter(CompressionTask.status == 'completed').count()
            failed_tasks = query.filter(CompressionTask.status == 'failed').count()
            processing_tasks = query.filter(CompressionTask.status == 'processing').count()
            pending_tasks = query.filter(CompressionTask.status == 'pending').count()
            
            return {
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'failed_tasks': failed_tasks,
                'processing_tasks': processing_tasks,
                'pending_tasks': pending_tasks,
                'success_rate': (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            }
        finally:
            session.close()

class SystemMetricsService:
    """Service for managing system metrics"""
    
    def __init__(self):
        self.db_manager = get_db_manager()
    
    def record_metrics(self, job_id: int, cpu_percent: float, memory_percent: float,
                      active_workers: int, pending_tasks: int = 0, completed_tasks: int = 0) -> SystemMetrics:
        """Record system metrics for a job"""
        session = self.db_manager.get_session()
        try:
            metrics = SystemMetrics(
                job_id=job_id,
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                active_workers=active_workers,
                pending_tasks=pending_tasks,
                completed_tasks=completed_tasks
            )
            session.add(metrics)
            session.commit()
            session.refresh(metrics)
            return metrics
        finally:
            session.close()
    
    def get_metrics_by_job(self, job_id: int, limit: int = 100) -> List[SystemMetrics]:
        """Get system metrics for a specific job"""
        session = self.db_manager.get_session()
        try:
            return session.query(SystemMetrics)\
                         .filter(SystemMetrics.job_id == job_id)\
                         .order_by(desc(SystemMetrics.timestamp))\
                         .limit(limit)\
                         .all()
        finally:
            session.close()
    
    def get_average_metrics_by_job(self, job_id: int) -> Dict[str, float]:
        """Get average system metrics for a job"""
        session = self.db_manager.get_session()
        try:
            result = session.query(
                func.avg(SystemMetrics.cpu_percent).label('avg_cpu'),
                func.avg(SystemMetrics.memory_percent).label('avg_memory'),
                func.avg(SystemMetrics.active_workers).label('avg_workers'),
                func.max(SystemMetrics.active_workers).label('max_workers')
            ).filter(SystemMetrics.job_id == job_id).first()
            
            return {
                'average_cpu_percent': round(result.avg_cpu or 0, 2),
                'average_memory_percent': round(result.avg_memory or 0, 2),
                'average_workers': round(result.avg_workers or 0, 2),
                'max_workers': result.max_workers or 0
            }
        finally:
            session.close()

class CRUDService:
    """Main CRUD service that combines all services"""
    
    def __init__(self):
        self.jobs = CompressionJobService()
        self.videos = VideoFileService()
        self.tasks = CompressionTaskService()
        self.metrics = SystemMetricsService()
        self.db_manager = get_db_manager()
    
    def initialize_database(self) -> bool:
        """Initialize the database with all tables"""
        return self.db_manager.init_database()
    
    def create_compression_batch(self, job_name: str, input_folder: str, output_folder: str,
                                video_files: List[str], quality_profiles: List[tuple],
                                dolby_atmos_enabled: bool = True) -> Optional[CompressionJob]:
        """Create a complete compression batch with job, videos, and tasks"""
        try:
            # Create the job
            job = self.jobs.create_job(job_name, input_folder, output_folder, dolby_atmos_enabled)
            
            total_tasks = 0
            
            # Create video records and tasks
            for video_file in video_files:
                # Get video info (you can extend this to get actual file info)
                video = self.videos.create_video(
                    job_id=job.id,
                    filename=os.path.basename(video_file),
                    filepath=video_file
                )
                
                # Create tasks for each quality profile
                for bitrate, resolution, hdr_metadata in quality_profiles:
                    quality_profile = f"{resolution}_{bitrate}"
                    self.tasks.create_task(
                        job_id=job.id,
                        video_id=video.id,
                        quality_profile=quality_profile,
                        bitrate=bitrate,
                        resolution=resolution,
                        hdr_metadata=hdr_metadata
                    )
                    total_tasks += 1
            
            # Update job with total tasks
            self.jobs.update_job_progress(job.id, total_tasks=total_tasks)
            
            return job
            
        except Exception as e:
            print(f"Error creating compression batch: {e}")
            return None
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get dashboard data with overall statistics"""
        try:
            all_jobs = self.jobs.get_all_jobs(limit=10)
            active_jobs = self.jobs.get_jobs_by_status('processing')
            
            # Overall statistics
            total_jobs = len(self.jobs.get_all_jobs(limit=1000))  # Simple count
            completed_jobs = len(self.jobs.get_jobs_by_status('completed'))
            failed_jobs = len(self.jobs.get_jobs_by_status('failed'))
            
            return {
                'recent_jobs': all_jobs,
                'active_jobs': active_jobs,
                'total_jobs': total_jobs,
                'completed_jobs': completed_jobs,
                'failed_jobs': failed_jobs,
                'success_rate': (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0
            }
        except Exception as e:
            print(f"Error getting dashboard data: {e}")
            return {}

# Global CRUD service instance
crud_service = None

def get_crud_service():
    """Get the global CRUD service instance"""
    global crud_service
    if crud_service is None:
        crud_service = CRUDService()
    return crud_service 