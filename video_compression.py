import os
import json
import random
import tkinter as tk
from tkinter import filedialog, scrolledtext
import subprocess

input_directory = ""
output_base_directory = ""

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

def compress_video(input_file, output_dir, bitrate, resolution, hdr_metadata=None, dolby_atmos=False):
    """Compresses a single video file with specified settings."""
    # Extract video information
    video_info = get_video_info(input_file)
    video_length = float(video_info['format']['duration'])
    original_width = video_info['streams'][0]['width']
    original_height = video_info['streams'][0]['height']
    video_quality = f"{original_width}x{original_height}"
    
    print("lambrkinfo: video_quality: ", video_quality)
    print("lambrkinfo: resolution: ", resolution)
    print("lambrkinfo: resolution matched " + resolution <= video_quality)

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
    os.system(command)

    # Check if output file was created successfully
    if os.path.exists(output_file):
        print(f"Compression successful: {output_file}")
    else:
        print(f"Compression failed: {output_file}")


def compress_videos(input_dir, output_base_dir, landscape_qualities, portrait_qualities, dolby_atmos=False):
    """Compresses all videos in the input directory with specified qualities."""
    print(f"Compressing videos in input directory: {input_dir}")

    input_files = [f for f in os.listdir(input_dir) if f.endswith(('.mp4', '.MOV'))]

    if not input_files:
        print("No videos to compress")
        return

    for input_file in input_files:
        input_path = os.path.join(input_dir, input_file)

        # Create a unique output directory for this input video
        output_dir = create_output_directory(output_base_dir)

        video_info = get_video_info(input_path)
        original_width = video_info['streams'][0]['width']
        original_height = video_info['streams'][0]['height']
        video_quality = f"{original_width}x{original_height}"
        # Compress video with specified qualities
        if is_portrait(original_width, original_height):
            # If portrait, set resolution to target a specific height
            for bitrate, resolution, hdr in portrait_qualities:
                    compress_video(input_path, output_dir, bitrate, resolution, hdr_metadata=hdr, dolby_atmos=dolby_atmos)
        else:
            for bitrate, resolution, hdr in landscape_qualities:
                compress_video(input_path, output_dir, bitrate, resolution, hdr_metadata=hdr, dolby_atmos=dolby_atmos)
            
            
class LambrkCompressorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Lambrk Compressor")
        
         # Input folder selection
        self.input_folder_label = tk.Label(root, text="Input Folder:")
        self.input_folder_label.pack()
        self.input_folder_button = tk.Button(root, text="Browse", command=self.select_input_folder)
        self.input_folder_button.pack()
        self.input_folder_path = tk.Entry(root, width=50)
        self.input_folder_path.pack()
        self.input_folder_display = tk.Label(root, text="", fg="blue")
        self.input_folder_display.pack()
        
        # Output folder selection
        self.output_folder_label = tk.Label(root, text="Output Folder:")
        self.output_folder_label.pack()
        self.output_folder_button = tk.Button(root, text="Browse", command=self.select_output_folder)
        self.output_folder_button.pack()
        self.output_folder_path = tk.Entry(root, width=50)
        self.output_folder_path.pack()
        self.output_folder_display = tk.Label(root, text="", fg="blue")
        self.output_folder_display.pack()
        
        # Compression button
        self.compress_button = tk.Button(root, text="Compress Videos", command=self.compress_videos)
        self.compress_button.pack()
        
        # Log display
        self.log_text = scrolledtext.ScrolledText(root, width=60, height=20)
        self.log_text.pack()
    
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
    
    def compress_videos(self):
        input_folder = self.input_folder_path.get()
        output_folder = self.output_folder_path.get()
        
        # List of video qualities (bitrate, resolution, HDR metadata)
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
            # Add higher quality settings cautiously
            # ("8000k", "7680x4320", {
            #     "color_primaries": "bt2020",
            #     "transfer_characteristics": "smpte2084",
            #     "mastering_display_color_primaries": "bt2020",
            #     "mastering_display_luminance": "1000"
            # })
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
            # Add higher quality settings cautiously
            # ("8000k", "7680x4320", {
            #     "color_primaries": "bt2020",
            #     "transfer_characteristics": "smpte2084",
            #     "mastering_display_color_primaries": "bt2020",
            #     "mastering_display_luminance": "1000"
            # })
        ]

        # Compress videos in the input directory using specified qualities with Dolby Atmos audio support
        
        if not input_folder or not output_folder:
            self.log_text.insert(tk.END, "Please select both input and output folders.\n")
            return
        
        self.log_text.insert(tk.END, f"Compressing videos from {input_folder} to {output_folder}\n")
        
        compress_videos(input_folder, output_folder, landscape_qualities, portrait_qualities, dolby_atmos=True)
        
        
        if not input_folder or not output_folder:
            self.log_text.insert(tk.END, "Please select both input and output folders.\n")
            return
        
        self.log_text.insert(tk.END, f"Compressing videos from {input_folder} to {output_folder}\n")
        
        # for root, dirs, files in os.walk(input_folder):
        #     for file in files:
        #         if file.endswith((".mp4", ".mkv", ".mov")):
        #             input_path = os.path.join(root, file)
        #             output_path = os.path.join(output_folder, file)
                    # self.compress_video(input_path, output_path)
                    
        

if __name__ == "__main__":
    root = tk.Tk()
    app = LambrkCompressorGUI(root)
    root.mainloop()
    

    
    
    
    

