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
from queue import Queue, PriorityQueue
import multiprocessing
from datetime import datetime
import shutil
import hashlib

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

class AdvancedResourceMonitor:
    """Enhanced resource monitoring with intelligent scaling and memory management."""
    
    def __init__(self):
        self.cpu_threshold_high = 85  # Critical CPU usage
        self.cpu_threshold_medium = 70  # Moderate CPU usage
        self.memory_threshold_high = 85  # Critical memory usage
        self.memory_threshold_medium = 70  # Moderate memory usage
        self.disk_threshold = 90  # Don't exceed 90% disk usage
        
        self.min_concurrent = 1
        self.max_concurrent = min(multiprocessing.cpu_count(), 6)  # Increased cap for better utilization
        
        # Performance tracking
        self.performance_history = []
        self.max_history = 20
        
        # Memory per task estimation (in MB)
        self.estimated_memory_per_task = 500  # Conservative estimate
        
    def get_system_usage(self):
        """Returns comprehensive system usage metrics."""
        cpu_percent = psutil.cpu_percent(interval=0.5)  # Faster interval
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'memory_available_gb': memory.available / (1024**3),
            'disk_percent': disk.percent,
            'disk_free_gb': disk.free / (1024**3)
        }
    
    def get_optimal_concurrent_count(self, task_complexity="medium"):
        """Determines optimal concurrent processes with advanced logic."""
        metrics = self.get_system_usage()
        cpu_percent = metrics['cpu_percent']
        memory_percent = metrics['memory_percent']
        memory_available_gb = metrics['memory_available_gb']
        
        # Base concurrent count on CPU cores
        base_count = self.max_concurrent
        
        # Adjust based on CPU usage
        if cpu_percent > self.cpu_threshold_high:
            cpu_factor = 0.3  # Severely reduce
        elif cpu_percent > self.cpu_threshold_medium:
            cpu_factor = 0.6  # Moderately reduce
        else:
            cpu_factor = 1.0  # Full utilization
        
        # Adjust based on memory usage
        if memory_percent > self.memory_threshold_high:
            memory_factor = 0.3
        elif memory_percent > self.memory_threshold_medium:
            memory_factor = 0.7
        else:
            # Also consider available memory for tasks
            estimated_tasks_by_memory = int(memory_available_gb * 1024 / self.estimated_memory_per_task)
            memory_factor = min(1.0, estimated_tasks_by_memory / base_count)
        
        # Task complexity adjustment
        complexity_factors = {
            "low": 1.2,     # Can handle more simple tasks
            "medium": 1.0,   # Standard
            "high": 0.8,    # Reduce for complex tasks
            "ultra": 0.6    # Significantly reduce for 4K+ videos
        }
        complexity_factor = complexity_factors.get(task_complexity, 1.0)
        
        # Calculate final count
        optimal_count = int(base_count * cpu_factor * memory_factor * complexity_factor)
        optimal_count = max(self.min_concurrent, min(optimal_count, self.max_concurrent))
        
        # Store performance data
        self.performance_history.append({
            'timestamp': time.time(),
            'cpu_percent': cpu_percent,
            'memory_percent': memory_percent,
            'optimal_count': optimal_count,
            'task_complexity': task_complexity
        })
        
        # Keep history limited
        if len(self.performance_history) > self.max_history:
            self.performance_history.pop(0)
        
        return optimal_count
    
    def get_performance_trend(self):
        """Analyze performance trends for better prediction."""
        if len(self.performance_history) < 3:
            return "stable"
        
        recent_cpu = [entry['cpu_percent'] for entry in self.performance_history[-5:]]
        cpu_trend = sum(recent_cpu[-3:]) / 3 - sum(recent_cpu[:2]) / 2
        
        if cpu_trend > 10:
            return "increasing_load"
        elif cpu_trend < -10:
            return "decreasing_load"
        else:
            return "stable"

# Global resource monitor
resource_monitor = AdvancedResourceMonitor()

def analyze_video_complexity(input_file):
    """Analyze video to determine processing complexity."""
    try:
        video_info = get_video_info(input_file)
        
        # Get video properties
        video_stream = next((s for s in video_info['streams'] if s['codec_type'] == 'video'), None)
        if not video_stream:
            return "medium"
        
        width = video_stream.get('width', 0)
        height = video_stream.get('height', 0)
        pixel_count = width * height
        
        # Determine complexity based on resolution and other factors
        if pixel_count >= 3840 * 2160:  # 4K+
            return "ultra"
        elif pixel_count >= 2560 * 1440:  # 1440p
            return "high"  
        elif pixel_count >= 1920 * 1080:  # 1080p
            return "medium"
        else:
            return "low"
        
    except Exception as e:
        print(f"Error analyzing video complexity: {e}")
        return "medium"

def should_skip_compression(input_file, target_resolution, target_bitrate):
    """Determine if compression should be skipped to avoid quality loss."""
    try:
        video_info = get_video_info(input_file)
        video_stream = next((s for s in video_info['streams'] if s['codec_type'] == 'video'), None)
        
        if not video_stream:
            return False
        
        # Get source properties
        source_width = video_stream.get('width', 0)
        source_height = video_stream.get('height', 0)
        source_bitrate = int(video_info['format'].get('bit_rate', 0))
        
        # Parse target resolution
        target_width, target_height = map(int, target_resolution.split('x'))
        target_bitrate_bps = int(target_bitrate.replace('k', '')) * 1000
        
        # Skip if target resolution is higher than source
        if target_width > source_width or target_height > source_height:
            return True
        
        # Skip if target bitrate is significantly higher than source
        if source_bitrate > 0 and target_bitrate_bps > source_bitrate * 1.5:
            return True
        
        # Skip if resolutions are very close (within 10% difference)
        source_pixels = source_width * source_height
        target_pixels = target_width * target_height
        
        if source_pixels > 0:
            pixel_ratio = target_pixels / source_pixels
            if pixel_ratio > 0.9:  # Less than 10% reduction
                return True
        
        return False
        
    except Exception as e:
        print(f"Error checking if compression should be skipped: {e}")
        return False

def get_optimized_ffmpeg_params(input_file, target_resolution, target_bitrate, hdr_metadata=None):
    """Generate optimized FFmpeg parameters based on input analysis."""
    try:
        video_info = get_video_info(input_file)
        video_stream = next((s for s in video_info['streams'] if s['codec_type'] == 'video'), None)
        
        if not video_stream:
            return None
        
        # Base parameters - optimized for quality and efficiency
        params = {
            'hwaccel': '-hwaccel videotoolbox',
            'input': f"'{input_file}'",
            'scale': f'-vf scale={target_resolution}:flags=lanczos',  # Better scaling algorithm
            'codec': '-c:v h264_videotoolbox',
            'bitrate': f'-b:v {target_bitrate}',
            'preset': '-preset fast',
            'crf': '-crf 23',
            'audio_codec': '-c:a aac -b:a 128k',  # Consistent audio quality
            'format': '-f mp4',
            'movflags': '-movflags +faststart',  # Better streaming compatibility
            'threads': f'-threads {min(4, multiprocessing.cpu_count())}'  # Limit threads per task
        }
        
        # Advanced encoding parameters for better efficiency
        source_fps = 30  # Default
        try:
            fps_str = video_stream.get('r_frame_rate', '30/1')
            if '/' in fps_str:
                num, den = fps_str.split('/')
                source_fps = float(num) / float(den)
        except:
            pass
        
        # Optimize for frame rate - cap at 30fps for efficiency
        if source_fps > 30:
            params['fps'] = '-r 30'
        
        # HDR metadata handling
        if hdr_metadata and isinstance(hdr_metadata, dict):
            color_primaries = hdr_metadata.get('color_primaries', 'bt709')
            transfer_characteristics = hdr_metadata.get('transfer_characteristics', 'bt709')
            
            params['color_metadata'] = (
                f'-metadata:s:v:0 color_primaries={color_primaries} '
                f'-metadata:s:v:0 transfer_characteristics={transfer_characteristics}'
            )
        
        return params
        
    except Exception as e:
        print(f"Error generating optimized parameters: {e}")
        return None

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
    """Optimized video compression with intelligent quality preservation."""
    try:
        # Pre-compression analysis
        if progress_callback:
            progress_callback(f"Analyzing: {os.path.basename(input_file)}")
        
        # Check if compression should be skipped
        if should_skip_compression(input_file, resolution, bitrate):
            if progress_callback:
                progress_callback(f"⊝ Skipped: {os.path.basename(input_file)} -> {resolution} (quality preservation)")
            print(f"Skipping compression: target quality not beneficial for {input_file}")
            return True, None  # Return success but no output file
        
        # Extract video information
        video_info = get_video_info(input_file)
        video_length = float(video_info['format']['duration'])
        original_width = video_info['streams'][0]['width']
        original_height = video_info['streams'][0]['height']
        video_quality = f"{original_width}x{original_height}"
        
        if progress_callback:
            progress_callback(f"Starting compression: {os.path.basename(input_file)} -> {resolution}")
        
        print(f"lambrkinfo: processing {os.path.basename(input_file)}")
        print(f"lambrkinfo: source quality: {video_quality}")
        print(f"lambrkinfo: target resolution: {resolution}")

        # Intelligent resolution adjustment for portrait videos
        adjusted_resolution = resolution
        if is_portrait(original_width, original_height):
            target_height = int(resolution.split('x')[1])
            target_width = int(original_width * (target_height / original_height))
            # Ensure even dimensions for better encoding
            target_width = target_width - (target_width % 2)
            target_height = target_height - (target_height % 2)
            adjusted_resolution = f"{target_width}x{target_height}"

        # Construct output file path
        output_file = os.path.join(output_dir, os.path.splitext(os.path.basename(input_file))[0] + f"_{adjusted_resolution}.mp4")
        
        # Check if output already exists and skip if so
        if os.path.exists(output_file):
            if progress_callback:
                progress_callback(f"⊝ Skipped: {os.path.basename(input_file)} -> {resolution} (already exists)")
            return True, output_file

        # Get optimized FFmpeg parameters
        ffmpeg_params = get_optimized_ffmpeg_params(input_file, adjusted_resolution, bitrate, hdr_metadata)
        if not ffmpeg_params:
            raise Exception("Failed to generate FFmpeg parameters")

        # Build optimized command
        command_parts = [
            "ffmpeg -y",  # Overwrite output files
            ffmpeg_params['hwaccel'],
            f"-i {ffmpeg_params['input']}",
            ffmpeg_params['scale'],
            ffmpeg_params['codec'],
            ffmpeg_params['bitrate'],
            ffmpeg_params['preset'],
            ffmpeg_params['crf'],
            ffmpeg_params['threads']
        ]
        
        # Add frame rate limitation if needed
        if 'fps' in ffmpeg_params:
            command_parts.append(ffmpeg_params['fps'])
        
        # Add color metadata if present
        if 'color_metadata' in ffmpeg_params:
            command_parts.append(ffmpeg_params['color_metadata'])
        
        # Audio codec selection
        if dolby_atmos:
            command_parts.append("-c:a eac3 -b:a 256k")
        else:
            command_parts.append(ffmpeg_params['audio_codec'])
        
        # Add optimization flags
        command_parts.extend([
            ffmpeg_params['movflags'],
            ffmpeg_params['format'],
            f"'{output_file}'"
        ])
        
        command = " ".join(command_parts)

        # Execute with timeout and resource monitoring
        print(f"Executing optimized command: {command}")
        
        if progress_callback:
            progress_callback(f"Processing: {os.path.basename(input_file)} -> {adjusted_resolution}")
        
        # Use timeout to prevent hanging processes
        timeout_seconds = max(300, video_length * 2)  # At least 5 minutes or 2x video length
        
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                text=True, 
                timeout=timeout_seconds
            )
        except subprocess.TimeoutExpired:
            if progress_callback:
                progress_callback(f"✗ Timeout: {os.path.basename(input_file)} -> {resolution}")
            print(f"Compression timed out for {input_file}")
            return False, None
        
        # Check result and file size
        if os.path.exists(output_file):
            # Verify output file is valid and reasonable size
            try:
                output_info = get_video_info(output_file)
                if 'streams' in output_info and len(output_info['streams']) > 0:
                    input_size = os.path.getsize(input_file)
                    output_size = os.path.getsize(output_file)
                    compression_ratio = output_size / input_size if input_size > 0 else 1
                    
                    if progress_callback:
                        progress_callback(f"✓ Completed: {os.path.basename(input_file)} -> {adjusted_resolution} ({compression_ratio:.2%} of original)")
                    
                    print(f"Compression successful: {output_file} (ratio: {compression_ratio:.2%})")
                    return True, output_file
                else:
                    # Invalid output file
                    os.remove(output_file)
                    raise Exception("Generated file appears to be invalid")
            except Exception as e:
                if os.path.exists(output_file):
                    os.remove(output_file)
                raise Exception(f"Output validation failed: {e}")
        else:
            if progress_callback:
                progress_callback(f"✗ Failed: {os.path.basename(input_file)} -> {resolution}")
            print(f"Compression failed: {output_file}")
            if result.stderr:
                print(f"FFmpeg error: {result.stderr}")
            return False, None
            
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
    """Optimized concurrent video compression with intelligent task scheduling."""
    print(f"Compressing videos in input directory: {input_dir}")

    input_files = [f for f in os.listdir(input_dir) if f.endswith(('.mp4', '.MOV', '.mov', '.avi', '.mkv')) and not f.startswith('._')]

    if not input_files:
        print("No videos to compress")
        if progress_callback:
            progress_callback("No videos found to compress")
        return

    # Analyze all videos first for intelligent scheduling
    video_analysis = {}
    for input_file in input_files:
        input_path = os.path.join(input_dir, input_file)
        try:
            complexity = analyze_video_complexity(input_path)
            file_size = os.path.getsize(input_path) / (1024 * 1024)  # MB
            video_analysis[input_file] = {
                'complexity': complexity,
                'file_size_mb': file_size,
                'input_path': input_path
            }
        except Exception as e:
            print(f"Error analyzing {input_file}: {e}")
            video_analysis[input_file] = {
                'complexity': 'medium',
                'file_size_mb': 100,  # Default
                'input_path': input_path
            }

    # Create prioritized compression tasks
    compression_tasks = []
    task_priorities = []  # For priority queue
    
    for input_file in input_files:
        analysis = video_analysis[input_file]
        input_path = analysis['input_path']
        output_dir = create_output_directory(output_base_dir)
        
        try:
            video_info = get_video_info(input_path)
            original_width = video_info['streams'][0]['width']
            original_height = video_info['streams'][0]['height']
            
            # Determine qualities based on orientation
            if is_portrait(original_width, original_height):
                qualities = portrait_qualities
            else:
                qualities = landscape_qualities
            
            # Create task for each quality with priority
            for i, (bitrate, resolution, hdr) in enumerate(qualities):
                # Calculate priority: lower complexity and smaller files first
                complexity_weight = {'low': 1, 'medium': 2, 'high': 3, 'ultra': 4}
                size_weight = min(4, int(analysis['file_size_mb'] / 100))  # Size in 100MB chunks
                resolution_weight = i  # Process lower resolutions first
                
                priority = complexity_weight.get(analysis['complexity'], 2) + size_weight + resolution_weight
                
                task = {
                    'input_path': input_path,
                    'output_dir': output_dir,
                    'bitrate': bitrate,
                    'resolution': resolution,
                    'hdr_metadata': hdr,
                    'dolby_atmos': dolby_atmos,
                    'task_id': f"{os.path.basename(input_file)}_{resolution}",
                    'complexity': analysis['complexity'],
                    'file_size_mb': analysis['file_size_mb'],
                    'priority': priority
                }
                compression_tasks.append(task)
                task_priorities.append((priority, len(compression_tasks) - 1))  # (priority, task_index)
        
        except Exception as e:
            print(f"Error processing {input_file}: {e}")
            continue
    
    # Sort tasks by priority (lower number = higher priority)
    task_priorities.sort(key=lambda x: x[0])
    sorted_tasks = [compression_tasks[idx] for _, idx in task_priorities]
    
    if progress_callback:
        progress_callback(f"Starting optimized compression of {len(sorted_tasks)} tasks for {len(input_files)} videos")
    
    # Process tasks with dynamic resource management
    completed_tasks = 0
    skipped_tasks = 0
    failed_tasks = 0
    total_tasks = len(sorted_tasks)
    
    # Batch processing to manage resource usage
    batch_size = 20  # Process in batches to manage memory
    
    for batch_start in range(0, total_tasks, batch_size):
        batch_end = min(batch_start + batch_size, total_tasks)
        batch_tasks = sorted_tasks[batch_start:batch_end]
        
        if progress_callback:
            progress_callback(f"Processing batch {batch_start//batch_size + 1} ({batch_start + 1}-{batch_end} of {total_tasks})")
        
        # Determine optimal workers for current batch complexity
        batch_complexities = [task['complexity'] for task in batch_tasks]
        avg_complexity = max(set(batch_complexities), key=batch_complexities.count)  # Most common complexity
        max_workers = resource_monitor.get_optimal_concurrent_count(avg_complexity)
        
        if progress_callback:
            progress_callback(f"Using {max_workers} workers for {avg_complexity} complexity batch")
        
        # Use ThreadPoolExecutor for concurrent processing
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit batch tasks
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
                ): task for task in batch_tasks
            }
            
            # Process completed tasks in this batch
            batch_completed = 0
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    success, output_file = future.result()
                    batch_completed += 1
                    completed_tasks += 1
                    
                    if success:
                        if output_file is None:  # Task was skipped
                            skipped_tasks += 1
                    else:
                        failed_tasks += 1
                    
                    if progress_callback:
                        progress_callback(f"Batch Progress: {batch_completed}/{len(batch_tasks)} | Overall: {completed_tasks}/{total_tasks} (✓{completed_tasks-failed_tasks-skipped_tasks} ⊝{skipped_tasks} ✗{failed_tasks})")
                    
                    # Dynamic worker adjustment within batch
                    if batch_completed % 3 == 0:  # Check every 3 completions
                        trend = resource_monitor.get_performance_trend()
                        if trend == "increasing_load":
                            # System load increasing, consider reducing workers for next batch
                            pass  # Will be handled in next batch
                    
                except Exception as exc:
                    failed_tasks += 1
                    completed_tasks += 1
                    if progress_callback:
                        progress_callback(f"✗ Task failed: {task['task_id']} - {str(exc)}")
                    print(f"Task {task['task_id']} generated an exception: {exc}")
        
        # Brief pause between batches to let system stabilize
        time.sleep(2)
    
    # Final summary
    successful_tasks = completed_tasks - failed_tasks - skipped_tasks
    if progress_callback:
        progress_callback(f"=== Compression Complete ===")
        progress_callback(f"Total: {total_tasks} | Successful: {successful_tasks} | Skipped: {skipped_tasks} | Failed: {failed_tasks}")
        progress_callback(f"Success Rate: {(successful_tasks/total_tasks)*100:.1f}%")
    
    print(f"Compression summary: {successful_tasks} successful, {skipped_tasks} skipped, {failed_tasks} failed out of {total_tasks} total tasks")

class LambrkCompressorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Lambrk Compressor - PostgreSQL CRUD Edition")
        self.root.geometry("900x800")
        
        # Compression status
        self.is_compressing = False
        self.compression_thread = None
        self.current_job_id = None
        
        # Initialize log display early so it's available for database initialization messages
        self.log_label = tk.Label(root, text="Compression Log:")
        self.log_label.pack(anchor='w', padx=10)
        self.log_text = scrolledtext.ScrolledText(root, width=80, height=15)
        self.log_text.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Database integration
        self.database_enabled = DATABASE_ENABLED
        self.crud_service = None
        
        if self.database_enabled:
            try:
                self.crud_service = get_crud_service()
                if self.crud_service.initialize_database():
                    self.log_message("Database connected successfully!")
                else:
                    self.log_message("Failed to connect to database - attempting automatic setup...")
                    if self.auto_setup_database():
                        self.log_message("Database setup completed! Reconnecting...")
                        try:
                            self.crud_service = get_crud_service()
                            if self.crud_service.initialize_database():
                                self.log_message("Database connected successfully after setup!")
                            else:
                                self.log_message("Failed to connect after setup - running in standalone mode")
                                self.database_enabled = False
                        except Exception as reconnect_e:
                            self.log_message(f"Reconnection failed after setup: {reconnect_e}")
                            self.database_enabled = False
                    else:
                        self.log_message("Automatic database setup failed - running in standalone mode")
                        self.database_enabled = False
            except Exception as e:
                self.log_message(f"Database initialization failed: {e}")
                self.log_message("Attempting automatic database setup...")
                if self.auto_setup_database():
                    self.log_message("Database setup completed! Reconnecting...")
                    try:
                        self.crud_service = get_crud_service()
                        if self.crud_service.initialize_database():
                            self.log_message("Database connected successfully after setup!")
                        else:
                            self.log_message("Failed to connect after setup - running in standalone mode")
                            self.database_enabled = False
                    except Exception as reconnect_e:
                        self.log_message(f"Reconnection failed after setup: {reconnect_e}")
                        self.database_enabled = False
                else:
                    self.log_message("Automatic database setup failed - running in standalone mode")
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
        
        # Start resource monitoring
        self.start_resource_monitoring()
    
    def auto_setup_database(self):
        """Automatically set up the database using the consolidated DatabaseManager"""
        try:
            self.log_message("Starting automatic database setup...")
            
            from database_models import DatabaseManager, reset_db_manager
            
            # Use default database configuration
            db_manager = DatabaseManager(
                host="localhost",
                port="5432", 
                user="debarunlahiri",
                password="password",
                database="postgres"
            )
            
            # Display connection info
            conn_info = db_manager.get_connection_info()
            self.log_message(f"Using connection: {conn_info['url_masked']}")
            
            # Initialize everything (database creation, tables, etc.)
            self.log_message("Setting up database and tables...")
            if db_manager.initialize():
                # Create .env file
                db_manager.create_env_file()
                self.log_message("Environment file (.env) created!")
                
                # Test CRUD operations
                self.log_message("Testing database operations...")
                try:
                    from crud_service import CRUDService
                    
                    # Reset global manager to use our configured one
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
                        self.log_message("Database CRUD operations working!")
                        # Clean up test job
                        crud.jobs.delete_job(job.id)
                        self.log_message("Test data cleaned up")
                        self.log_message("Database setup completed successfully!")
                        return True
                    else:
                        self.log_message("Could not create test job")
                        return False
                        
                except Exception as e:
                    self.log_message(f"CRUD test failed: {e}")
                    return False
            else:
                self.log_message("Database initialization failed")
                return False
                
        except Exception as e:
            self.log_message(f"Automatic database setup failed: {e}")
            return False
    
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
            metrics = resource_monitor.get_system_usage()
            cpu_percent = metrics['cpu_percent']
            memory_percent = metrics['memory_percent']
            
            # Update CPU progress bar and label
            self.cpu_progress['value'] = cpu_percent
            self.cpu_label.config(text=f"{cpu_percent:.1f}%")
            
            # Update Memory progress bar and label
            self.memory_progress['value'] = memory_percent
            self.memory_label.config(text=f"{memory_percent:.1f}% ({metrics['memory_available_gb']:.1f}GB free)")
            
            # Update concurrent workers count with complexity awareness
            if not self.is_compressing:
                optimal_workers = resource_monitor.get_optimal_concurrent_count("medium")
                trend = resource_monitor.get_performance_trend()
                trend_indicator = {"stable": "→", "increasing_load": "↑", "decreasing_load": "↓"}.get(trend, "→")
                self.workers_label.config(text=f"Available Workers: {optimal_workers} {trend_indicator}")
            
            # Enhanced color coding with more granular levels
            if cpu_percent > 85:
                self.cpu_progress.configure(style="Red.Horizontal.TProgressbar")
                cpu_color = "red"
            elif cpu_percent > 70:
                self.cpu_progress.configure(style="Yellow.Horizontal.TProgressbar")
                cpu_color = "orange"
            elif cpu_percent > 50:
                cpu_color = "yellow"
            else:
                self.cpu_progress.configure(style="Green.Horizontal.TProgressbar")
                cpu_color = "green"
                
            if memory_percent > 85:
                self.memory_progress.configure(style="Red.Horizontal.TProgressbar")
                memory_color = "red"
            elif memory_percent > 70:
                self.memory_progress.configure(style="Yellow.Horizontal.TProgressbar")
                memory_color = "orange"
            elif memory_percent > 50:
                memory_color = "yellow"
            else:
                self.memory_progress.configure(style="Green.Horizontal.TProgressbar")
                memory_color = "green"
            
            # Update label colors
            self.cpu_label.config(fg=cpu_color)
            self.memory_label.config(fg=memory_color)
            
            # Add disk space warning if needed
            if metrics['disk_percent'] > 90:
                self.workers_label.config(text=f"⚠ Disk Space Low ({metrics['disk_free_gb']:.1f}GB free)", fg="red")
                
        except Exception as e:
            print(f"Error updating resource display: {e}")
        
        # Schedule next update
        self.root.after(1500, self.update_resource_display)  # Slightly faster updates
    
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
        video_files = [f for f in os.listdir(input_folder) if f.endswith(('.mp4', '.MOV', '.mov', '.avi', '.mkv')) and not f.startswith('._')]
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
                    optimal_workers = resource_monitor.get_optimal_concurrent_count("medium")
                    trend = resource_monitor.get_performance_trend()
                    trend_indicator = {"stable": "→", "increasing_load": "↑", "decreasing_load": "↓"}.get(trend, "→")
                    self.root.after(0, lambda: self.workers_label.config(
                        text=f"Active Workers: {optimal_workers} {trend_indicator}", fg="orange"))
                    
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
                metrics = resource_monitor.get_system_usage()
                active_workers = resource_monitor.get_optimal_concurrent_count("medium")
                
                # Get current task statistics
                stats = self.crud_service.tasks.get_task_statistics(self.current_job_id)
                
                self.crud_service.metrics.record_metrics(
                    job_id=self.current_job_id,
                    cpu_percent=metrics['cpu_percent'],
                    memory_percent=metrics['memory_percent'],
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
        self.workers_label.config(text=f"Available Workers: {resource_monitor.get_optimal_concurrent_count('medium')}", fg="green")
        self.log_message("=== Compression process completed ===")
        
def compress_videos(input_dir, output_base_dir, landscape_qualities, portrait_qualities, dolby_atmos=False):
    """Legacy function for backward compatibility - redirects to concurrent version."""
    compress_videos_concurrent(input_dir, output_base_dir, landscape_qualities, portrait_qualities, dolby_atmos)
                    
        

if __name__ == "__main__":
    root = tk.Tk()
    app = LambrkCompressorGUI(root)
    root.mainloop()
    

    
    
    
    

