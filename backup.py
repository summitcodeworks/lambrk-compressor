import os
import json

def get_video_info(input_file):
    command = f"ffprobe -v quiet -print_format json -show_format -show_streams '{input_file}'"
    output = os.popen(command).read()
    return json.loads(output)

def compress_videos(input_dir, output_dir, qualities):
    print("Compressing videos...")
    input_files = [f for f in os.listdir(input_dir) if f.endswith(('.mp4', '.MOV'))]
    print("input_files: ".format(input_files))
    
    if len(input_files) == 0:
        print("No videos to compress")
    else:
        for input_file in input_files:
            input_path = os.path.join(input_dir, input_file)
            print("Path: {0}".format(input_path))
            video_info = get_video_info(input_path)
            
            # Check if HDR metadata is available
            if 'side_data_list' in video_info['streams'][0] and video_info['streams'][0]['side_data_list']:
                hdr_info = video_info['streams'][0]['side_data_list'][0].get('hdr', None)
            else:
                hdr_info = None
            
            video_size = video_info['format']['size']
            video_length = float(video_info['format']['duration'])
            video_quality = video_info['streams'][0]['width']  # Assuming width represents quality
            hdr_info = video_info['streams'][0]['side_data_list'][0]['hdr'] if video_info['streams'][0]['side_data_list'] else None
            audio_codec = video_info['streams'][1]['codec_name']
            
            
            
            print(f"Video: {input_file}")
            print(f"Size: {video_size}")
            print(f"Length: {video_length} seconds")
            print(f"Quality: {video_quality}")
            print(f"HDR: {hdr_info}")
            print(f"Audio Codec: {audio_codec}")
            
            for quality in qualities:
                bitrate, resolution, hdr_metadata = quality
                output_file = f"{os.path.splitext(input_file)[0]}_{resolution}.mp4"
                output_path = os.path.join(output_dir, output_file)
                
                # command = (
                #     f"ffmpeg -i '{input_path}' "
                #     f"-vf scale={resolution} "
                #     f"-b:v {bitrate} "
                #     f"-metadata:s:v:0 color_primaries={hdr_metadata.get('color_primaries', 'bt709')} "  # Default to bt709 if HDR metadata not present
                #     f"-metadata:s:v:0 transfer_characteristics={hdr_metadata.get('transfer_characteristics', 'bt709')} "
                #     f"-metadata:s:v:0 mastering_display_color_primaries={hdr_metadata.get('mastering_display_color_primaries', 'bt709')} "
                #     f"-metadata:s:v:0 mastering_display_luminance={hdr_metadata.get('mastering_display_luminance', '100')} "
                #     f"-c:v libx264 -preset fast -crf 23 "
                #     f"-c:a aac -b:a 128k '{output_path}'"
                # )
                
                command = (
                    f"ffmpeg -hwaccel videotoolbox -i '{input_path}' "
                    f"-vf scale={resolution} "
                    f"-b:v {bitrate} "
                    f"-metadata:s:v:0 color_primaries={hdr_metadata.get('color_primaries', 'bt709')} "
                    f"-metadata:s:v:0 transfer_characteristics={hdr_metadata.get('transfer_characteristics', 'bt709')} "
                    f"-metadata:s:v:0 mastering_display_color_primaries={hdr_metadata.get('mastering_display_color_primaries', 'bt709')} "
                    f"-metadata:s:v:0 mastering_display_luminance={hdr_metadata.get('mastering_display_luminance', '100')} "
                    f"-c:v h264_videotoolbox -preset fast -crf 23 "
                    f"-c:a aac -b:a 128k '{output_path}'"
                )
                
                # command = (f"ffmpeg -i '{input_path}' -vf scale={resolution} -c:v libx264 -preset fast -crf 23 -c:a aac -b:a 128k '{output_path}'")
                
                print(f"Executing command: {command}")
                os.system(command)
                
                if os.path.exists(output_path):
                    print(f"Compression successful: {output_path}")
                else:
                    print(f"Compression failed: {output_path}")
    
        

if __name__ == "__main__":
    input_directory = "lambrk_videos/pending/"
    output_directory = "lambrk_videos/final"
    
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
        # ("8000k", "7680x4320", {
        #     "color_primaries": "bt2020",
        #     "transfer_characteristics": "smpte2084",
        #     "mastering_display_color_primaries": "bt2020",
        #     "mastering_display_luminance": "1000"
        # })
    ]
    
    compress_videos(input_directory, output_directory, qualities)
