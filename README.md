# Lambrk Video Compressor - PostgreSQL CRUD Edition

A powerful video compression tool with concurrent processing, intelligent resource monitoring, and complete PostgreSQL database integration with CRUD operations.

## 🚀 Features

### Core Compression Features
- **Multiple Quality Levels**: Supports 8 different quality levels from 144p to 4K (2160p)
- **HDR Support**: Handles HDR metadata for high-quality 4K content
- **Portrait & Landscape**: Automatically detects video orientation and applies appropriate settings
- **Dolby Atmos Audio**: Support for high-quality audio compression

### 🔥 Concurrent Processing Features
- **Multi-threaded Compression**: Process multiple videos simultaneously without waiting in queue
- **Intelligent Resource Monitoring**: Real-time CPU and memory usage tracking
- **Dynamic Worker Scaling**: Automatically adjusts concurrent processes based on system load
- **Thread-safe GUI**: Real-time progress updates for all concurrent operations
- **Instant Start**: Users can start compression immediately without queuing delays

### 🗄️ **NEW: PostgreSQL Database Integration**
- **Complete CRUD Operations**: Create, Read, Update, Delete for all compression data
- **Job Tracking**: Full job lifecycle management with status tracking
- **Video File Management**: Detailed metadata storage for all processed videos
- **Task Management**: Individual compression task tracking with progress monitoring
- **System Metrics Storage**: Historical resource usage data for analysis
- **Jobs History Viewer**: GUI interface to view, manage, and delete compression jobs
- **Database Dashboard**: Real-time statistics and job progress tracking
- **Persistent Storage**: All compression history and metadata stored permanently

### 📊 Resource Management
- **CPU Monitoring**: Visual progress bars showing current CPU usage
- **Memory Monitoring**: Real-time memory usage tracking
- **Smart Scaling**: 
  - Maximum 4 concurrent processes on multi-core systems
  - Automatically reduces workers when CPU > 80% or Memory > 80%
  - Scales up when system resources are available
- **Background Processing**: Non-blocking GUI operations

## 🔧 System Requirements
- Python 3.6+
- FFmpeg with VideoToolbox support (macOS)
- PostgreSQL 12+ (for database features)
- psutil for resource monitoring
- psycopg2-binary for PostgreSQL connectivity
- SQLAlchemy 2.0+ for ORM operations
- tkinter (usually included with Python)

## 📦 Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd lambrk-compressor
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install and setup PostgreSQL:
```bash
# macOS with Homebrew
brew install postgresql

# Start PostgreSQL
brew services start postgresql

# Create database user (optional)
createuser -s postgres
```

4. Setup database (Interactive):
```bash
python setup_database.py
```

5. Ensure FFmpeg is installed:
```bash
# macOS with Homebrew
brew install ffmpeg

# Check installation
ffmpeg -version
```

## 🎯 Usage

### GUI Application
```bash
python video_compression.py
```

### Key GUI Features:
1. **Input/Output Folder Selection**: Browse and select folders
2. **Database Job Management**: 
   - Custom job naming with auto-generated timestamps
   - Jobs history viewer with full CRUD operations
   - Real-time progress tracking in database
3. **Real-time Resource Monitoring**: 
   - CPU usage bar (Green < 60%, Yellow 60-80%, Red > 80%)
   - Memory usage bar with same color coding
   - Active concurrent workers display
4. **Concurrent Compression**: Start multiple video processing immediately
5. **Live Progress Log**: Thread-safe logging of all operations
6. **Database Features**:
   - View/Delete compression jobs
   - Track job progress and completion times
   - System metrics storage and analysis
7. **Stop Function**: Ability to halt compression process

### Video Quality Levels
The application automatically generates the following quality levels:

#### Landscape Videos:
- 256x144 @ 150k bitrate
- 426x240 @ 200k bitrate  
- 640x360 @ 300k bitrate
- 854x480 @ 500k bitrate
- 1280x720 @ 1000k bitrate
- 1920x1080 @ 2000k bitrate
- 2560x1440 @ 4000k bitrate
- 3840x2160 @ 6000k bitrate (HDR)

#### Portrait Videos:
- Same quality levels with adjusted resolutions based on aspect ratio

## 🏗️ Architecture

### Database Schema
```python
# Core Tables:
CompressionJob     # Job tracking and metadata
VideoFile         # Individual video file records  
CompressionTask   # Video + quality combinations
SystemMetrics     # Resource usage history

# Relationships:
Job -> Videos -> Tasks
Job -> Metrics
```

### CRUD Services Layer
```python
CompressionJobService    # Job lifecycle management
VideoFileService        # Video metadata operations
CompressionTaskService  # Task progress tracking
SystemMetricsService    # Resource monitoring data
CRUDService            # Combined service layer
```

### Resource Monitoring System
```python
class ResourceMonitor:
    - cpu_threshold: 80%      # Reduce workers above this
    - memory_threshold: 80%   # Reduce workers above this  
    - min_concurrent: 1       # Minimum workers
    - max_concurrent: 4       # Maximum workers (CPU cores limited)
```

### Concurrent Processing Flow
1. **Database Job Creation**: Create job record with metadata
2. **Task Creation**: Each video + quality combination becomes a tracked task
3. **ThreadPoolExecutor**: Manages concurrent ffmpeg processes
4. **Progress Updates**: Real-time database updates for job progress
5. **System Metrics**: Continuous resource monitoring storage
6. **Error Handling**: Database-tracked failure states and error messages

### Thread Safety & Database Integration
- **GUI Updates**: Uses `root.after()` for thread-safe GUI updates
- **Database Operations**: Thread-safe CRUD operations with session management
- **Logging**: Thread-safe logging system with database storage
- **Resource Updates**: Separate monitoring thread storing metrics in database

## 🎛️ Advanced Configuration

### Adjusting Concurrent Workers
Edit the `ResourceMonitor` class to customize:
```python
self.max_concurrent = min(multiprocessing.cpu_count(), 6)  # Increase max workers
self.cpu_threshold = 70  # More aggressive CPU management
```

### Custom Quality Profiles
Modify the quality arrays in `_run_compression()` method to add/remove quality levels.

## 🚦 Performance Optimization

### System Resource Guidelines:
- **Light Load** (CPU < 60%, Memory < 60%): Full concurrent workers
- **Medium Load** (CPU 60-80%, Memory 60-80%): Reduced workers  
- **Heavy Load** (CPU > 80%, Memory > 80%): Minimum workers (1-2)

### Best Practices:
1. **SSD Storage**: Use SSD for input/output folders for better I/O performance
2. **Close Other Apps**: Free up system resources before large batch processing
3. **Monitor Temperatures**: Ensure adequate cooling for sustained processing
4. **Batch Size**: Process in smaller batches if system becomes unstable

## 🐛 Troubleshooting

### Common Issues:
1. **FFmpeg Not Found**: Ensure FFmpeg is in system PATH
2. **High Resource Usage**: Application automatically manages this, but manual intervention available via Stop button
3. **GUI Freezing**: All processing is done in background threads - GUI should remain responsive
4. **Memory Leaks**: Process monitoring helps prevent excessive memory usage

### Error Handling:
- Individual task failures don't stop the entire batch
- Detailed error logging for each failed compression
- Graceful degradation when system resources are constrained

## 📈 Performance Benefits

### Before (Sequential Processing):
- Process videos one at a time
- User waits for entire queue
- Underutilized system resources
- No resource awareness

### After (Concurrent Processing):
- **3-5x faster processing** on multi-core systems
- **Immediate start** - no waiting in queue
- **Intelligent resource management**
- **Better user experience** with real-time feedback
- **Scalable performance** based on system capabilities

## 🔮 Future Enhancements
- GPU acceleration support
- Network/cloud processing capabilities  
- Priority queue system
- Resume interrupted batches
- Advanced scheduling options

## 📄 License
This project is licensed under the MIT License.

## 🤝 Contributing
Contributions are welcome! Please ensure any new features maintain thread safety and resource monitoring capabilities.
