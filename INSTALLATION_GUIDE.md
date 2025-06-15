# 🚀 Lambrk Video Compressor - Installation Guide

## Quick Start Installation

### 1. **Clone and Setup**
```bash
# Clone the repository
git clone <repository-url>
cd lambrk-compressor

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. **Install Dependencies**
```bash
# Install all required packages
pip install -r requirements.txt

# Verify installation
python verify_dependencies.py
```

### 3. **Install FFmpeg** (Required for video processing)
```bash
# macOS with Homebrew
brew install ffmpeg

# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
```

### 4. **Database Setup** (Optional but recommended)

#### Option A: PostgreSQL (Full features)
```bash
# Install PostgreSQL
brew install postgresql          # macOS
sudo apt install postgresql      # Ubuntu/Debian

# Start PostgreSQL
brew services start postgresql   # macOS
sudo systemctl start postgresql  # Linux

# Setup database
python setup_database.py
```

#### Option B: No Database (Standalone mode)
```bash
# Skip database setup - application will run without database features
python video_compression.py
```

### 5. **Launch Application**
```bash
# Start the video compressor
python video_compression.py
```

## 📋 Files Overview

| File | Purpose |
|------|---------|
| `video_compression.py` | Main application with GUI |
| `database_models.py` | PostgreSQL database schema |
| `crud_service.py` | Database operations layer |
| `setup_database.py` | Interactive database setup |
| `test_database.py` | Test database functionality |
| `verify_dependencies.py` | Check all dependencies |
| `requirements.txt` | Python package dependencies |
| `.gitignore` | Git ignore rules |

## 🧪 Testing

```bash
# Test database integration
python test_database.py

# Verify all dependencies
python verify_dependencies.py
```

## ⚡ Quick Feature Test

1. **Start Application**: `python video_compression.py`
2. **Select Input Folder**: Browse to folder with video files (.mp4, .mov, .avi)
3. **Select Output Folder**: Choose where compressed videos will be saved
4. **Start Compression**: Click "Start Database-Tracked Compression" (or "Start Concurrent Compression" without database)
5. **View History**: Click "View Jobs History" (if database enabled)

## 🛠️ Troubleshooting

### Common Issues:

**1. ModuleNotFoundError**
```bash
pip install -r requirements.txt
python verify_dependencies.py
```

**2. PostgreSQL Connection Failed**
```bash
# Check if PostgreSQL is running
brew services list | grep postgresql  # macOS
sudo systemctl status postgresql      # Linux

# Restart PostgreSQL
brew services restart postgresql      # macOS
sudo systemctl restart postgresql     # Linux
```

**3. FFmpeg Not Found**
```bash
# Check FFmpeg installation
ffmpeg -version

# If not installed, install using package manager
brew install ffmpeg      # macOS
sudo apt install ffmpeg  # Ubuntu/Debian
```

**4. Permission Denied (Database)**
```bash
# Create PostgreSQL user
createuser -s postgres
```

### Getting Help:

1. **Check Dependencies**: `python verify_dependencies.py`
2. **Test Database**: `python test_database.py`
3. **View Logs**: Check application console output
4. **Standalone Mode**: Run without database if PostgreSQL issues persist

## 🎯 What You Get

✅ **Concurrent video compression** - No waiting in queues  
✅ **Real-time resource monitoring** - CPU/Memory tracking  
✅ **Database job tracking** - Never lose compression history  
✅ **Professional GUI** - Easy-to-use interface  
✅ **Multiple quality levels** - 144p to 4K compression  
✅ **HDR support** - High-quality video processing  
✅ **Error resilience** - Graceful failure handling  

## 🚀 Ready to Compress!

Once installed, you have a professional-grade video compression tool with enterprise-level database tracking! 