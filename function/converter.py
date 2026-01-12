import subprocess
import os

def run_conversion(ffmpeg_path, input_file, output_file, codec="libx264"):
    """
    แปลงไฟล์วิดีโอใดๆ เป็น MP4
    codec: 'libx264' (H.264) หรือ 'libx265' (H.265)
    """
    try:
        if not os.path.exists(input_file):
            return "Error: Input file not found"

        # ตรวจสอบว่า output มีนามสกุล .mp4 หรือไม่
        if not output_file.lower().endswith(".mp4"):
            output_file += ".mp4"

        # คำสั่ง ffmpeg
        # -y: เขียนทับไฟล์เดิมถ้ามีอยู่
        # -c:v: เลือก Video Codec
        # -preset: medium (ความเร็วในการแปลง)
        # -crf: 23 (ค่าคุณภาพไฟล์ ยิ่งน้อยยิ่งชัดแต่ไฟล์ใหญ่ 23 คือค่ามาตรฐาน)
        # -c:a aac: แปลงเสียงเป็น AAC เพื่อให้รองรับกับ MP4 ได้ดีที่สุด
        command = [
            ffmpeg_path,
            "-y",
            "-i", input_file,
            "-c:v", codec,
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "aac",
            output_file
        ]

        # รันคำสั่ง
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode == 0:
            return f"Success: Converted to {output_file}"
        else:
            return f"Error: {result.stderr.splitlines()[-1]}"

    except Exception as e:
        return f"Error: {str(e)}"