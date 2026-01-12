import requests
import os
import shutil
import subprocess
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor

LIST_FILENAME = "input_list.txt"

def download_file(url, local_filename):
    try:
        with requests.get(url, stream=True, timeout=10) as r:
            r.raise_for_status()
            with open(local_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

def download_segment_worker(index, url, temp_dir):
    # เปลี่ยนนามสกุลเป็น .ts เพื่อความมาตรฐานของไฟล์วิดีโอส่วนย่อย
    filename = os.path.join(temp_dir, f"segment_{index:05d}.ts")
    return download_file(url, filename)

def create_concat_list(directory, list_filename):
    list_path = os.path.join(directory, list_filename)
    # รองรับทั้งไฟล์ .ts และรูปภาพที่อาจถูกนำมาเรียงเป็นวิดีโอ
    files = sorted([f for f in os.listdir(directory) if f.endswith(('.ts', '.jpg', '.jpeg', '.png'))])
    if not files: return None
    with open(list_path, "w") as f:
        for filename in files:
            f.write(f"file '{filename}'\n") 
    return list_path

def run_m3u8_download(ffmpeg_path, manifest_url, save_dir, filename, max_workers):
    """ฟังก์ชันหลักสำหรับ M3U8 พร้อมระบบเลือก Directory"""
    
    # 1. จัดการ Path ให้ถูกต้อง
    os.makedirs(save_dir, exist_ok=True)
    final_output_path = os.path.abspath(os.path.join(save_dir, filename))
    
    # สร้าง Temp ในโฟลเดอร์ปลายทางเพื่อป้องกันการย้ายไฟล์ข้าม Drive ซึ่งจะช้า
    temp_dir = os.path.join(save_dir, "m3u8_temp_" + os.path.splitext(filename)[0])
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        # 2. ดึงข้อมูล Manifest
        m3u8_content = requests.get(manifest_url, timeout=10).text
        base_url = manifest_url.rsplit('/', 1)[0] + '/'
        image_urls = [urljoin(base_url, l.strip()) for l in m3u8_content.splitlines() 
                      if l.strip() and not l.startswith('#')]
        
        if not image_urls: return "Error: No segments found"

        # 3. ดาวน์โหลด Segments แบบขนาน
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(download_segment_worker, i, url, temp_dir) 
                       for i, url in enumerate(image_urls)]
            for _ in futures: _.result()

        # 4. รวมไฟล์ด้วย FFmpeg
        list_path = create_concat_list(temp_dir, LIST_FILENAME)
        if not list_path: return "Error: No segments downloaded"
        
        command = [
            ffmpeg_path, '-f', 'concat', '-safe', '0', '-i', LIST_FILENAME, 
            '-c', 'copy', '-bsf:a', 'aac_adtstoasc', '-y', final_output_path
        ]
        
        # รัน FFmpeg ในโฟลเดอร์ Temp
        subprocess.run(command, check=True, cwd=temp_dir, capture_output=True)
        
        # 5. ลบไฟล์ชั่วคราว
        shutil.rmtree(temp_dir)
        return f"Success: Saved to {final_output_path}"
        
    except Exception as e:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        return f"Error: {str(e)}"

def run_normal_download(url, save_path):
    """ฟังก์ชันหลักสำหรับดาวน์โหลดไฟล์ปกติ"""
    try:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        if download_file(url, save_path):
            return f"Success: Saved to {save_path}"
        return "Error: Download failed"
    except Exception as e:
        return f"Error: {str(e)}"