import subprocess
import os

def video_merge(ffmpeg_path, video_list, output_filename):
    if not video_list:
        return "⚠️ Error: Video list is empty."

    # 1. สร้างไฟล์รายการวิดีโอ (list.txt) เพื่อส่งให้ FFmpeg
    list_file = "merge_list.txt"
    try:
        with open(list_file, "w", encoding="utf-8") as f:
            for path in video_list:
                # FFmpeg ต้องการ Path ที่ใช้ forward slash (/) และต้อง escape single quote
                abs_path = os.path.abspath(path).replace("'", "'\\''")
                f.write(f"file '{abs_path}'\n")

        # 2. เตรียมคำสั่ง FFmpeg
        # -f concat: ใช้โหมดต่อไฟล์
        # -safe 0: อนุญาตให้ใช้ Absolute Path
        # -c copy: ใช้การก๊อปปี้ Stream (ไม่ Encode ใหม่) ทำให้เร็วมาก!
        command = [
            ffmpeg_path,
            "-y",               # เขียนทับถ้ามีไฟล์ชื่อซ้ำ
            "-f", "concat",
            "-safe", "0",
            "-i", list_file,
            "-c", "copy",       # ความเร็วจะเร็วเหมือนก๊อปปี้ไฟล์
            output_filename
        ]

        # 3. รัน Process
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            encoding="utf-8",
            creationflags=subprocess.CREATE_NO_WINDOW # ไม่เปิดหน้าต่างดำ
        )

        # อ่าน Log และส่งออก Console (ถ้าต้องการ)
        for line in process.stdout:
            print(f"FFmpeg: {line.strip()}")

        process.wait()

        if process.returncode == 0:
            return f"✅ Success: Merged into '{output_filename}'"
        else:
            return f"⚠️ Error: FFmpeg failed (Code {process.returncode})"

    except Exception as e:
        return f"⚠️ Error: {str(e)}"
    
    finally:
        # ลบไฟล์รายการชั่วคราว
        if os.path.exists(list_file):
            os.remove(list_file)