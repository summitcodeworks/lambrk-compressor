import os
import json
import random
import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk, messagebox
import subprocess
import threading
import time
import psutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue
import multiprocessing
from datetime import datetime

# Database imports
try:
    from crud_service import get_crud_service
    from database_models import init_database
    DATABASE_ENABLED = True
except ImportError as e:
    print(f"Database modules not available: {e}")
    DATABASE_ENABLED = False

input_directory = ""
output_base_directory = ""

class ResourceMonitor:
    """Monitors system resources to determine optimal concurrent processes."""
    
    def __init__(self):
        self.cpu_threshold = 80  # Don't exceed 80% CPU usage
        self.memory_threshold = 80  # Don't exceed 80% memory usage
        self.min_concurrent = 1
        self.max_concurrent = min(multiprocessing.cpu_count(), 4)  # Cap at 4 concurrent processes
    
    def get_system_usage(self):
        """Returns current CPU and memory usage."""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory_percent = psutil.virtual_memory().percent
        return cpu_percent, memory_percent
    
    def get_optimal_concurrent_count(self):
        """Determines optimal number of concurrent processes based on current system load."""
        cpu_percent, memory_percent = self.get_system_usage()
        
        # If system is under heavy load, reduce concurrent processes
        if cpu_percent > self.cpu_threshold or memory_percent > self.memory_threshold:
            return max(1, self.max_concurrent // 2)
        elif cpu_percent > 60 or memory_percent > 60:
            return max(2, self.max_concurrent - 1)
        else:
            return self.max_concurrent

# Global resource monitor
resource_monitor = ResourceMonitor()

def get_video_info(input_file):
    """Extracts video information using ffprobe."""
    command = f"ffprobe -v quiet -print_format json -show_format -show_streams '{input_file}'"
    output = os.popen(command).read()
    return json.loads(output)

def generate_random_hex():
    """Generates a random 12-digit hexadecimal string."""
    return ''.join(random.choices('0123456789abcdef', k=12))

def create_output_directory(base_dir):
    """Creates a new directory within the base directory with a random hex name."""
    new_dir_name = generate_random_hex()
    new_dir_path = os.path.join(base_dir, new_dir_name)

    if not os.path.exists(new_dir_path):
        os.makedirs(new_dir_path)
        print(f"Created new directory: {new_dir_path}")
    else:
        print(f"Directory already exists: {new_dir_path}")

    return new_dir_path

def is_portrait(width, height):
    """Checks if the video is in portrait orientation based on dimensions."""
    return height > width

def compress_video_with_progress(input_file, output_dir, bitrate, resolution, hdr_metadata=None, dolby_atmos=False, progress_callback=None):
    """Compresses a single video file with progress reporting."""
    try:
        # Extract video information
        video_info = get_video_info(input_file)
        video_length = float(video_info['format']['duration'])
        original_width = video_info['streams'][0]['width']
        original_height = video_info['streams'][0]['height']
        video_quality = f"{original_width}x{original_height}"
        
        if progress_callback:
            progress_callback(f"Starting compression: {os.path.basename(input_file)} -> {resolution}")
        
        print("lambrkinfo: video_quality: ", video_quality)
        print("lambrkinfo: resolution: ", resolution)
        print("lambrkinfo: resolution matched " + str(resolution <= video_quality))

        # Determine resolution based on orientation (portrait or landscape)
        if is_portrait(original_width, original_height):
            # If portrait, set resolution to target a specific height
            target_height = int(resolution.split('x')[1])
            target_width = int(original_width * (target_height / original_height))
            resolution = f"{target_width}x{target_height}"

        # Construct output file path based on input file and specified resolution
        output_file = os.path.join(output_dir, os.path.splitext(os.path.basename(input_file))[0] + f"_{resolution}.mp4")

        # Determine HDR metadata if available
        if hdr_metadata is None or not isinstance(hdr_metadata, dict):
            hdr_metadata = {}  # Use an empty dictionary if hdr_metadata is None

        # Extract HDR metadata attributes
        color_primaries = hdr_metadata.get('color_primaries', 'bt709')
        transfer_characteristics = hdr_metadata.get('transfer_characteristics', 'bt709')
        mastering_display_color_primaries = hdr_metadata.get('mastering_display_color_primaries', 'bt709')
        mastering_display_luminance = hdr_metadata.get('mastering_display_luminance', '100')

        # Construct ffmpeg command for video compression
        command = (
            f"ffmpeg -hwaccel videotoolbox -i '{input_file}' "
            f"-vf scale={resolution} "
            f"-c:v h264_videotoolbox -b:v {bitrate} -preset fast -crf 23 "
            f"-metadata:s:v:0 color_primaries={color_primaries} "
            f"-metadata:s:v:0 transfer_characteristics={transfer_characteristics} "
            f"-metadata:s:v:0 mastering_display_color_primaries={mastering_display_color_primaries} "
            f"-metadata:s:v:0 mastering_display_luminance={mastering_display_luminance} "
        )

        if dolby_atmos:
            command += " -c:a eac3"
        else:
            command += " -c:a aac"

        command += f" '{output_file}'"

        # Execute ffmpeg command
        print(f"Executing command: {command}")
        
        if progress_callback:
            progress_callback(f"Processing: {os.path.basename(input_file)} -> {resolution}")
        
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        
        # Check if output file was created successfully
        if os.path.exists(output_file):
            if progress_callback:
                progress_callback(f"✓ Completed: {os.path.basename(input_file)} -> {resolution}")
            print(f"Compression successful: {output_file}")
            return True, output_file
        else:
            if progress_callback:
                progress_callback(f"✗ Failed: {os.path.basename(input_file)} -> {resolution}")
            print(f"Compression failed: {output_file}")
            return False, output_file
            
    except Exception as e:
        if progress_callback:
            progress_callback(f"✗ Error: {os.path.basename(input_file)} -> {str(e)}")
        print(f"Error compressing {input_file}: {str(e)}")
        return False, None

def compress_video(input_file, output_dir, bitrate, resolution, hdr_metadata=None, dolby_atmos=False):
    """Original compress_video function for backward compatibility."""
    success, output_file = compress_video_with_progress(input_file, output_dir, bitrate, resolution, hdr_metadata, dolby_atmos)
    return success

def compress_videos_concurrent(input_dir, output_base_dir, landscape_qualities, portrait_qualities, dolby_atmos=False, progress_callback=None):
    """Compresses videos concurrently with resource monitoring."""
    print(f"Compressing videos in input directory: {input_dir}")

    input_files = [f for f in os.listdir(input_dir) if f.endswith(('.mp4', '.MOV'))]

    if not input_files:
        print("No videos to compress")
        if progress_callback:
            progress_callback("No videos found to compress")
        return

    # Create compression tasks
    compression_tasks = []
    
    for input_file in input_files:
        input_path = os.path.join(input_dir, input_file)
        output_dir = create_output_directory(output_base_dir)
        
        video_info = get_video_info(input_path)
        original_width = video_info['streams'][0]['width']
        original_height = video_info['streams'][0]['height']
        
        # Determine qualities based on orientation
        if is_portrait(original_width, original_height):
            qualities = portrait_qualities
        else:
            qualities = landscape_qualities
        
        # Create task for each quality
        for bitrate, resolution, hdr in qualities:
            task = {
                'input_path': input_path,
                'output_dir': output_dir,
                'bitrate': bitrate,
                'resolution': resolution,
                'hdr_metadata': hdr,
                'dolby_atmos': dolby_atmos,
                'task_id': f"{os.path.basename(input_file)}_{resolution}"
            }
            compression_tasks.append(task)
    
    if progress_callback:
        progress_callback(f"Starting compression of {len(compression_tasks)} tasks for {len(input_files)} videos")
    
    # Process tasks concurrently with dynamic resource monitoring
    completed_tasks = 0
    total_tasks = len(compression_tasks)
    
    # Use ThreadPoolExecutor for concurrent processing
    max_workers = resource_monitor.get_optimal_concurrent_count()
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_task = {
            executor.submit(
                compress_video_with_progress,
                task['input_path'],
                task['output_dir'],
                task['bitrate'],
                task['resolution'],
                task['hdr_metadata'],
                task['dolby_atmos'],
                progress_callback
            ): task for task in compression_tasks
        }
        
        # Process completed tasks
        for future in as_completed(future_to_task):
            task = future_to_task[future]
            try:
                success, output_file = future.result()
                completed_tasks += 1
                
                if progress_callback:
                    progress_callback(f"Progress: {completed_tasks}/{total_tasks} tasks completed")
                
                # Dynamically adjust concurrent workers based on system load
                if completed_tasks % 5 == 0:  # Check every 5 completions
                    optimal_workers = resource_monitor.get_optimal_concurrent_count()
                    if optimal_workers != max_workers:
                        max_workers = optimal_workers
                        if progress_callback:
                            progress_callback(f"Adjusted concurrent workers to {max_workers} based on system load")
                
            except Exception as exc:
                if progress_callback:
                    progress_callback(f"Task failed: {task['task_id']} - {str(exc)}")
                print(f"Task {task['task_id']} generated an exception: {exc}")
    
    if progress_callback:
        progress_callback(f"All compression tasks completed! ({completed_tasks}/{total_tasks})")

class LambrkCompressorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Lambrk Compressor - PostgreSQL CRUD Edition")
        self.root.geometry("900x800")
        
        # Compression status
        self.is_compressing = False
        self.compression_thread = None
        self.current_job_id = None
        
        # Database integration
        self.database_enabled = DATABASE_ENABLED
        self.crud_service = None
        
        if self.database_enabled:
            try:
                self.crud_service = get_crud_service()
                if self.crud_service.initialize_database():
                    self.log_message("Database connected successfully!")
                else:
                    self.log_message("Failed to connect to database - running in standalone mode")
                    self.database_enabled = False
            except Exception as e:
                self.log_message(f"Database initialization failed: {e}")
                self.database_enabled = False
        else:
            self.log_message("Running in standalone mode - no database features available")
        
        # Input folder selection
        self.input_folder_label = tk.Label(root, text="Input Folder:")
        self.input_folder_label.pack(pady=5)
        self.input_folder_button = tk.Button(root, text="Browse", command=self.select_input_folder)
        self.input_folder_button.pack()
        self.input_folder_path = tk.Entry(root, width=60)
        self.input_folder_path.pack(pady=5)
        self.input_folder_display = tk.Label(root, text="", fg="blue", wraplength=700)
        self.input_folder_display.pack()
        
        # Output folder selection
        self.output_folder_label = tk.Label(root, text="Output Folder:")
        self.output_folder_label.pack(pady=5)
        self.output_folder_button = tk.Button(root, text="Browse", command=self.select_output_folder)
        self.output_folder_button.pack()
        self.output_folder_path = tk.Entry(root, width=60)
        self.output_folder_path.pack(pady=5)
        self.output_folder_display = tk.Label(root, text="", fg="blue", wraplength=700)
        self.output_folder_display.pack()
        
        # Resource monitoring frame
        self.resource_frame = tk.Frame(root)
        self.resource_frame.pack(pady=10, fill='x', padx=10)
        
        self.resource_label = tk.Label(self.resource_frame, text="System Resources:")
        self.resource_label.pack(anchor='w')
        
        # CPU usage
        self.cpu_frame = tk.Frame(self.resource_frame)
        self.cpu_frame.pack(fill='x', pady=2)
        tk.Label(self.cpu_frame, text="CPU:").pack(side='left')
        self.cpu_progress = ttk.Progressbar(self.cpu_frame, length=200, mode='determinate')
        self.cpu_progress.pack(side='left', padx=(5, 10))
        self.cpu_label = tk.Label(self.cpu_frame, text="0%")
        self.cpu_label.pack(side='left')
        
        # Memory usage
        self.memory_frame = tk.Frame(self.resource_frame)
        self.memory_frame.pack(fill='x', pady=2)
        tk.Label(self.memory_frame, text="Memory:").pack(side='left')
        self.memory_progress = ttk.Progressbar(self.memory_frame, length=200, mode='determinate')
        self.memory_progress.pack(side='left', padx=(5, 10))
        self.memory_label = tk.Label(self.memory_frame, text="0%")
        self.memory_label.pack(side='left')
        
        # Concurrent workers info
        self.workers_label = tk.Label(self.resource_frame, text="Concurrent Workers: 0", fg="green")
        self.workers_label.pack(anchor='w', pady=2)
        
        # Database status and job name
        if self.database_enabled:
            self.db_frame = tk.Frame(root)
            self.db_frame.pack(pady=10, fill='x', padx=10)
            
            tk.Label(self.db_frame, text="Job Name:").pack(side='left')
            self.job_name_entry = tk.Entry(self.db_frame, width=30)
            self.job_name_entry.pack(side='left', padx=5)
            self.job_name_entry.insert(0, f"Job_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            
            self.view_jobs_button = tk.Button(self.db_frame, text="View Jobs History", 
                                            command=self.show_jobs_history, bg="blue", fg="white")
            self.view_jobs_button.pack(side='right', padx=5)
            
            self.db_status_label = tk.Label(self.db_frame, text="Database: Connected", fg="green")
            self.db_status_label.pack(side='right', padx=10)
        
        # Compression button
        self.button_frame = tk.Frame(root)
        self.button_frame.pack(pady=10)
        
        compress_text = "Start Database-Tracked Compression" if self.database_enabled else "Start Concurrent Compression"
        self.compress_button = tk.Button(self.button_frame, text=compress_text, 
                                       command=self.compress_videos, bg="green", fg="white", 
                                       font=("Arial", 12, "bold"))
        self.compress_button.pack(side='left', padx=5)
        
        self.stop_button = tk.Button(self.button_frame, text="Stop", 
                                   command=self.stop_compression, bg="red", fg="white",
                                   state='disabled')
        self.stop_button.pack(side='left', padx=5)
        
        # Progress bar
        self.progress_frame = tk.Frame(root)
        self.progress_frame.pack(fill='x', padx=10, pady=5)
        tk.Label(self.progress_frame, text="Overall Progress:").pack(anchor='w')
        self.overall_progress = ttk.Progressbar(self.progress_frame, length=400, mode='indeterminate')
        self.overall_progress.pack(fill='x', pady=2)
        
        # Log display
        self.log_label = tk.Label(root, text="Compression Log:")
        self.log_label.pack(anchor='w', padx=10)
        self.log_text = scrolledtext.ScrolledText(root, width=80, height=15)
        self.log_text.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Start resource monitoring
        self.start_resource_monitoring()
    
    def select_input_folder(self):
        folder_selected = filedialog.askdirectory()
        self.input_folder_path.delete(0, tk.END)
        self.input_folder_path.insert(0, folder_selected)
        self.input_folder_display.config(text=folder_selected)
    
    def select_output_folder(self):
        folder_selected = filedialog.askdirectory()
        self.output_folder_path.delete(0, tk.END)
        self.output_folder_path.insert(0, folder_selected)
        self.output_folder_display.config(text=folder_selected)
    
    def start_resource_monitoring(self):
        """Start continuous resource monitoring."""
        self.update_resource_display()
    
    def update_resource_display(self):
        """Update the resource display with current system usage."""
        try:
            cpu_percent, memory_percent = resource_monitor.get_system_usage()
            
            # Update CPU progress bar and label
            self.cpu_progress['value'] = cpu_percent
            self.cpu_label.config(text=f"{cpu_percent:.1f}%")
            
            # Update Memory progress bar and label
            self.memory_progress['value'] = memory_percent
            self.memory_label.config(text=f"{memory_percent:.1f}%")
            
            # Update concurrent workers count
            if not self.is_compressing:
                optimal_workers = resource_monitor.get_optimal_concurrent_count()
                self.workers_label.config(text=f"Available Concurrent Workers: {optimal_workers}")
            
            # Color code based on usage
            if cpu_percent > 80:
                self.cpu_progress.configure(style="Red.Horizontal.TProgressbar")
            elif cpu_percent > 60:
                self.cpu_progress.configure(style="Yellow.Horizontal.TProgressbar")
            else:
                self.cpu_progress.configure(style="Green.Horizontal.TProgressbar")
                
            if memory_percent > 80:
                self.memory_progress.configure(style="Red.Horizontal.TProgressbar")
            elif memory_percent > 60:
                self.memory_progress.configure(style="Yellow.Horizontal.TProgressbar")
            else:
                self.memory_progress.configure(style="Green.Horizontal.TProgressbar")
                
        except Exception as e:
            print(f"Error updating resource display: {e}")
        
        # Schedule next update
        self.root.after(2000, self.update_resource_display)  # Update every 2 seconds
    
    def log_message(self, message):
        """Thread-safe logging to the GUI."""
        def _log():
            self.log_text.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {message}\n")
            self.log_text.see(tk.END)
        
        if threading.current_thread() == threading.main_thread():
            _log()
        else:
            self.root.after(0, _log)
    
    def stop_compression(self):
        """Stop the compression process."""
        self.is_compressing = False
        self.log_message("Stopping compression...")
        self.compress_button.config(state='normal', text="Start Concurrent Compression")
        self.stop_button.config(state='disabled')
        self.overall_progress.stop()
    
    def compress_videos(self):
        """Start concurrent video compression with database tracking."""
        if self.is_compressing:
            self.log_message("Compression already in progress!")
            return
            
        input_folder = self.input_folder_path.get()
        output_folder = self.output_folder_path.get()
        
        if not input_folder or not output_folder:
            self.log_message("Please select both input and output folders.")
            return
        
        if not os.path.exists(input_folder):
            self.log_message("Input folder does not exist!")
            return
            
        if not os.path.exists(output_folder):
            self.log_message("Output folder does not exist!")
            return
        
        # Check for video files
        video_files = [f for f in os.listdir(input_folder) if f.endswith(('.mp4', '.MOV', '.mov', '.avi', '.mkv'))]
        if not video_files:
            self.log_message("No video files found in the input folder!")
            return
        
        # Create database job if database is enabled
        if self.database_enabled and self.crud_service:
            try:
                job_name = self.job_name_entry.get() if hasattr(self, 'job_name_entry') else f"Job_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                # Get quality profiles
                landscape_qualities, portrait_qualities = self._get_quality_profiles()
                all_qualities = landscape_qualities + portrait_qualities  # For counting
                
                # Create full file paths
                video_file_paths = [os.path.join(input_folder, f) for f in video_files]
                
                # Create database job
                job = self.crud_service.create_compression_batch(
                    job_name=job_name,
                    input_folder=input_folder,
                    output_folder=output_folder,
                    video_files=video_file_paths,
                    quality_profiles=landscape_qualities,  # Use one set for calculation
                    dolby_atmos_enabled=True
                )
                
                if job:
                    self.current_job_id = job.id
                    self.log_message(f"Created database job: {job_name} (ID: {job.id})")
                else:
                    self.log_message("Failed to create database job - proceeding without database tracking")
                    self.current_job_id = None
            except Exception as e:
                self.log_message(f"Database error: {e} - proceeding without database tracking")
                self.current_job_id = None
        
        # Start compression
        self.is_compressing = True
        self.compress_button.config(state='disabled', text="Compressing...")
        self.stop_button.config(state='normal')
        self.overall_progress.start()
        
        self.log_message(f"Found {len(video_files)} video(s) to compress")
        self.log_message(f"Input: {input_folder}")
        self.log_message(f"Output: {output_folder}")
        
        # Update job status to processing if database is enabled
        if self.current_job_id and self.crud_service:
            self.crud_service.jobs.update_job_status(self.current_job_id, 'processing')
        
        # Start compression in a separate thread
        self.compression_thread = threading.Thread(target=self._run_compression, args=(input_folder, output_folder))
        self.compression_thread.daemon = True
        self.compression_thread.start()
    
    def _run_compression(self, input_folder, output_folder):
        """Run the compression process with database integration."""
        try:
            # Get quality profiles
            landscape_qualities, portrait_qualities = self._get_quality_profiles()
            
            # Update worker count display and record metrics during compression
            def update_worker_display():
                if self.is_compressing:
                    optimal_workers = resource_monitor.get_optimal_concurrent_count()
                    self.root.after(0, lambda: self.workers_label.config(
                        text=f"Active Concurrent Workers: {optimal_workers}", fg="orange"))
                    
                    # Record system metrics to database
                    self._record_system_metrics()
            
            # Start worker display updates and metrics recording
            def worker_update_loop():
                while self.is_compressing:
                    time.sleep(5)  # Update every 5 seconds
                    update_worker_display()
                    
            worker_update_thread = threading.Thread(target=worker_update_loop)
            worker_update_thread.daemon = True
            worker_update_thread.start()
            
            # Create enhanced progress callback that updates database
            def database_progress_callback(message):
                self.log_message(message)
                
                # Update job progress in database if enabled
                if self.current_job_id and self.crud_service:
                    try:
                        # Get current task statistics
                        stats = self.crud_service.tasks.get_task_statistics(self.current_job_id)
                        
                        # Update job progress
                        self.crud_service.jobs.update_job_progress(
                            job_id=self.current_job_id,
                            completed_tasks=stats.get('completed_tasks', 0)
                        )
                    except Exception as e:
                        print(f"Error updating job progress: {e}")
            
            # Run concurrent compression
            compress_videos_concurrent(
                input_folder, 
                output_folder, 
                landscape_qualities, 
                portrait_qualities, 
                dolby_atmos=True,
                progress_callback=database_progress_callback
            )
            
        except Exception as e:
            self.log_message(f"Error during compression: {str(e)}")
            
            # Mark job as failed in database
            if self.current_job_id and self.crud_service:
                try:
                    self.crud_service.jobs.update_job_status(
                        self.current_job_id, 'failed', error_message=str(e)
                    )
                except Exception as db_error:
                    print(f"Error updating job status: {db_error}")
        finally:
            # Reset UI state
            self.is_compressing = False
            self.root.after(0, self._compression_finished)
    
    def _get_quality_profiles(self):
        """Get quality profiles for landscape and portrait videos."""
        landscape_qualities = [
            ("150k", "256x144", {}),
            ("200k", "426x240", {}),
            ("300k", "640x360", {}),
            ("500k", "854x480", {}),
            ("1000k", "1280x720", {}),
            ("2000k", "1920x1080", {}),
            ("4000k", "2560x1440", {}),
            ("6000k", "3840x2160", {
                "color_primaries": "bt2020",
                "transfer_characteristics": "smpte2084",
                "mastering_display_color_primaries": "bt2020",
                "mastering_display_luminance": "1000"
            }),
        ]
        
        portrait_qualities = [
            ("150k", "256x144", {}),
            ("200k", "426x240", {}),
            ("300k", "640x360", {}),
            ("500k", "854x480", {}),
            ("1000k", "1280x720", {}),
            ("2000k", "1920x1080", {}),
            ("4000k", "2560x1440", {}),
            ("6000k", "3840x2160", {
                "color_primaries": "bt2020",
                "transfer_characteristics": "smpte2084",
                "mastering_display_color_primaries": "bt2020",
                "mastering_display_luminance": "1000"
            }),
        ]
        
        return landscape_qualities, portrait_qualities
    
    def show_jobs_history(self):
        """Show jobs history in a new window."""
        if not self.database_enabled or not self.crud_service:
            messagebox.showwarning("Database Not Available", "Database features are not available.")
            return
        
        try:
            # Create new window for jobs history
            history_window = tk.Toplevel(self.root)
            history_window.title("Compression Jobs History")
            history_window.geometry("1000x600")
            
            # Create treeview for jobs
            columns = ('ID', 'Job Name', 'Status', 'Created', 'Videos', 'Tasks', 'Progress', 'Duration')
            tree = ttk.Treeview(history_window, columns=columns, show='headings')
            
            # Define headings
            for col in columns:
                tree.heading(col, text=col)
                tree.column(col, width=120)
            
            # Get jobs data
            jobs = self.crud_service.jobs.get_all_jobs(limit=50)
            
            for job in jobs:
                duration = ""
                if job.duration_seconds:
                    duration = f"{job.duration_seconds:.1f}s"
                
                values = (
                    job.id,
                    job.job_name,
                    job.status.upper(),
                    job.created_at.strftime("%Y-%m-%d %H:%M"),
                    job.processed_videos,
                    f"{job.completed_tasks}/{job.total_tasks}",
                    f"{job.progress_percentage:.1f}%",
                    duration
                )
                tree.insert('', 'end', values=values)
            
            # Add scrollbar
            scrollbar = ttk.Scrollbar(history_window, orient="vertical", command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            
            # Pack widgets
            tree.pack(side='left', fill='both', expand=True)
            scrollbar.pack(side='right', fill='y')
            
            # Add buttons frame
            buttons_frame = tk.Frame(history_window)
            buttons_frame.pack(side='bottom', fill='x', padx=10, pady=10)
            
            def delete_selected_job():
                selected = tree.selection()
                if selected:
                    job_id = tree.item(selected[0])['values'][0]
                    if messagebox.askyesno("Confirm Delete", f"Delete job ID {job_id}?"):
                        if self.crud_service.jobs.delete_job(job_id):
                            tree.delete(selected[0])
                            messagebox.showinfo("Success", "Job deleted successfully!")
                        else:
                            messagebox.showerror("Error", "Failed to delete job!")
            
            def refresh_jobs():
                # Clear existing items
                for item in tree.get_children():
                    tree.delete(item)
                
                # Reload jobs
                jobs = self.crud_service.jobs.get_all_jobs(limit=50)
                for job in jobs:
                    duration = ""
                    if job.duration_seconds:
                        duration = f"{job.duration_seconds:.1f}s"
                    
                    values = (
                        job.id,
                        job.job_name,
                        job.status.upper(),
                        job.created_at.strftime("%Y-%m-%d %H:%M"),
                        job.processed_videos,
                        f"{job.completed_tasks}/{job.total_tasks}",
                        f"{job.progress_percentage:.1f}%",
                        duration
                    )
                    tree.insert('', 'end', values=values)
            
            tk.Button(buttons_frame, text="Refresh", command=refresh_jobs).pack(side='left', padx=5)
            tk.Button(buttons_frame, text="Delete Selected", command=delete_selected_job, bg="red", fg="white").pack(side='left', padx=5)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load jobs history: {e}")
    
    def _record_system_metrics(self):
        """Record system metrics to database if enabled."""
        if self.current_job_id and self.crud_service and self.is_compressing:
            try:
                cpu_percent, memory_percent = resource_monitor.get_system_usage()
                active_workers = resource_monitor.get_optimal_concurrent_count()
                
                # Get current task statistics
                stats = self.crud_service.tasks.get_task_statistics(self.current_job_id)
                
                self.crud_service.metrics.record_metrics(
                    job_id=self.current_job_id,
                    cpu_percent=cpu_percent,
                    memory_percent=memory_percent,
                    active_workers=active_workers,
                    pending_tasks=stats.get('pending_tasks', 0),
                    completed_tasks=stats.get('completed_tasks', 0)
                )
            except Exception as e:
                print(f"Error recording metrics: {e}")
    
    def _compression_finished(self):
        """Reset GUI state after compression is finished."""
        # Update job status in database
        if self.current_job_id and self.crud_service:
            try:
                self.crud_service.jobs.update_job_status(self.current_job_id, 'completed')
                self.log_message(f"Database job {self.current_job_id} marked as completed")
            except Exception as e:
                self.log_message(f"Error updating job status: {e}")
            finally:
                self.current_job_id = None
        
        compress_text = "Start Database-Tracked Compression" if self.database_enabled else "Start Concurrent Compression"
        self.compress_button.config(state='normal', text=compress_text)
        self.stop_button.config(state='disabled')
        self.overall_progress.stop()
        self.workers_label.config(text=f"Available Concurrent Workers: {resource_monitor.get_optimal_concurrent_count()}", fg="green")
        self.log_message("=== Compression process completed ===")
        
def compress_videos(input_dir, output_base_dir, landscape_qualities, portrait_qualities, dolby_atmos=False):
    """Legacy function for backward compatibility - redirects to concurrent version."""
    compress_videos_concurrent(input_dir, output_base_dir, landscape_qualities, portrait_qualities, dolby_atmos)
                    
        

if __name__ == "__main__":
    root = tk.Tk()
    app = LambrkCompressorGUI(root)
    root.mainloop()
    

    
    
    
    

