import os
import json

def get_video_info(input_file):
    """Extracts video information using ffprobe."""
    command = f"ffprobe -v quiet -print_format json -show_format -show_streams '{input_file}'"
    output = os.popen(command).read()
    return json.loads(output)

def compress_video(input_file, output_file, bitrate, resolution, hdr_metadata=None):
    """Compresses a single video file with specified settings."""
    # Construct ffmpeg command for video compression
    command = (
        f"ffmpeg -hwaccel videotoolbox -i '{input_file}' "
        f"-vf scale={resolution} "
        f"-b:v {bitrate} "
        f"-metadata:s:v:0 color_primaries={hdr_metadata.get('color_primaries', 'bt709')} "
        f"-metadata:s:v:0 transfer_characteristics={hdr_metadata.get('transfer_characteristics', 'bt709')} "
        f"-metadata:s:v:0 mastering_display_color_primaries={hdr_metadata.get('mastering_display_color_primaries', 'bt709')} "
        f"-metadata:s:v:0 mastering_display_luminance={hdr_metadata.get('mastering_display_luminance', '100')} "
        f"-c:v h264_videotoolbox -preset fast -crf 23 "
        f"-c:a aac -b:a 128k '{output_file}'"
    )

    # Execute ffmpeg command
    print(f"Executing command: {command}")
    os.system(command)

    # Check if output file was created successfully
    if os.path.exists(output_file):
        print(f"Compression successful: {output_file}")
    else:
        print(f"Compression failed: {output_file}")

def compress_videos(input_dir, output_dir, qualities):
    """Compresses all videos in the input directory with specified qualities."""
    print("Compressing videos...")
    input_files = [f for f in os.listdir(input_dir) if f.endswith(('.mp4', '.MOV'))]

    if not input_files:
        print("No videos to compress")
        return

    for input_file in input_files:
        input_path = os.path.join(input_dir, input_file)
        video_info = get_video_info(input_path)

        # Extract video information
        video_length = float(video_info['format']['duration'])
        video_quality = video_info['streams'][0]['width']  # Assuming width represents quality
        hdr_metadata = video_info['streams'][0].get('side_data_list', [{}])[0].get('hdr', None)

        print(f"Video: {input_file}")
        print(f"Length: {video_length} seconds")
        print(f"Quality: {video_quality}")
        print(f"HDR: {hdr_metadata}")

        for bitrate, resolution, hdr in qualities:
            output_file = os.path.splitext(input_file)[0] + f"_{resolution}.mp4"
            output_path = os.path.join(output_dir, output_file)

            # Compress video with specified settings
            compress_video(input_path, output_path, bitrate, resolution, hdr)

if __name__ == "__main__":
    input_directory = "lambrk_videos/pending/"
    output_directory = "lambrk_videos/final/"

    # List of video qualities (bitrate, resolution, HDR metadata)
    qualities = [
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

    # Compress videos using specified qualities
    compress_videos(input_directory, output_directory, qualities)
