import threading
from imgui_bundle import imgui, immapp, hello_imgui
import function.downloader as downloader
import function.converter as converter
import function.merger as merger
import os
import sys
import json
import tkinter as tk
from tkinter import filedialog

class MyFont:
    # เก็บอ้างอิงฟอนต์ไว้เรียกใช้
    main_font: imgui.ImFont = None

class AppState:
    def __init__(self):
        self.config_file = "settings.json"
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Config พื้นฐาน
        self.max_workers = 8
        if getattr(sys, 'frozen', False):
            # ถ้า Build เป็น .exe แล้ว
            self.base_path = os.path.dirname(sys.executable)
        else:
            # ถ้ายังรันผ่าน Python ปกติ
            self.base_path = os.path.dirname(os.path.abspath(__file__))

        # ตั้งค่าให้มันหา ffmpeg.exe ในโฟลเดอร์เดียวกับโปรแกรม
        local_ffmpeg = os.path.join(self.base_path, "ffmpeg.exe")
        
        # ถ้าเจอไฟล์ ffmpeg.exe ในโฟลเดอร์ ให้ใช้ตัวนั้นเลย
        if os.path.exists(local_ffmpeg):
            #self.ffmpeg_path = get_resource_path("ffmpeg.exe")
            self.ffmpeg_path = local_ffmpeg
        else:
            # ถ้าไม่เจอ ค่อยไปดึงค่าจาก Setting เดิม
            self.ffmpeg_path = "C:/ffmpeg/bin/ffmpeg.exe"
        
        # โหลดฟอนต์ที่เคยบันทึกไว้ ถ้าไม่มีให้ใช้ Century Gothic เป็น Default
        self.selected_font_path = self.load_config()
        
        # M3U8 & Normal & Converter
        self.m3u8_url = ""
        self.m3u8_save_dir = os.path.join(base_dir, "downloads")
        self.m3u8_output = "video_m3u8.mp4"
        self.normal_url = ""
        self.normal_save_dir = os.path.join(base_dir, "downloads")
        self.normal_filename = "video.mp4"
        self.conv_input = ""
        self.conv_output = "converted_video.mp4"
        self.selected_codec_idx = 0
        self.codecs = ["libx264", "libx265"]

        # merge
        self.merge_list = []
        self.merge_input_path = ""
        self.merge_output_name = "merged_video.mp4"

        # Status
        self.log_msg = "Status: Ready"
        self.is_running = False
        self.logs = ["Welcome to Video Downloader Pro", "System Ready..."]

    def load_config(self):
        """โหลดค่าฟอนต์จากไฟล์ JSON"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    data = json.load(f)
                    return data.get("font_path", "fonts/centurygothic.ttf")
            except:
                pass
        return "fonts/centurygothic.ttf"

    def save_config(self):
        """บันทึกค่าฟอนต์ลงไฟล์ JSON"""
        try:
            with open(self.config_file, "w") as f:
                json.dump({"font_path": self.selected_font_path}, f)
        except Exception as e:
            self.add_log(f"Error saving config: {e}")

    def add_log(self, message):
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.logs.append(f"[{timestamp}] {message}")
        if len(self.logs) > 100:
            self.logs.pop(0)

state = AppState()

def get_resource_path(relative_path):
    """ฟังก์ชันสำหรับหา Path ของไฟล์ทั้งตอนรันปกติ และตอนรันแบบ .exe ไฟล์เดียว"""
    try:
        # PyInstaller สร้างโฟลเดอร์ชั่วคราวและเก็บ path ไว้ใน _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def open_file_dialog():
    root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)
    path = filedialog.askopenfilename(filetypes=[("Video", "*.mp4 *.mkv *.ts *.avi"), ("All", "*.*")])
    root.destroy()
    return path

def open_folder_dialog():
    root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)
    path = filedialog.askdirectory()
    root.destroy()
    return path

# ตั้งค่า Assets Folder
current_dir = os.path.dirname(__file__)
hello_imgui.set_assets_folder(current_dir)

def load_fonts():
    """ฟังก์ชันนี้จะถูกเรียกโดย HelloImGui เมื่อเริ่มโปรแกรม"""
    io = imgui.get_io()
    
    # ตรวจสอบ Path ให้แน่ใจ (รองรับทั้งตอนรันสดและตอนเป็น .exe)
    if os.path.exists(state.selected_font_path):
        MyFont.main_font = hello_imgui.load_font(state.selected_font_path, 18.0)
        io.font_default = MyFont.main_font
        print(f"Successfully loaded: {state.selected_font_path}")
    else:
        print(f"Error: Cannot find font at {state.selected_font_path}")

def start_thread(target_func, *args):
    def wrapper():
        state.is_running = True
        state.add_log("Task started...")
        result = target_func(*args)
        state.add_log(result)
        state.log_msg = f"Status: {result}"
        state.is_running = False
    threading.Thread(target=wrapper, daemon=True).start()

def gui():
    io = imgui.get_io()
    imgui.set_next_window_pos((0, 0))
    imgui.set_next_window_size(io.display_size)
    
    imgui.begin("MainContainer", None, imgui.WindowFlags_.no_decoration)

    # หัวข้อใหญ่
    imgui.text_colored((1.0, 0.8, 0.2, 1.0), "VIDEO TOOLKIT PRO")
    imgui.spacing()

    if imgui.begin_tab_bar("Tabs"):
        # --- TAB 1: M3U8 ---
        opened, _ = imgui.begin_tab_item("M3U8")
        if opened:
            # 1. รับค่า URL ของ M3U8
            _, state.m3u8_url = imgui.input_text("M3U8 URL", state.m3u8_url)
            
            # 2. เพิ่มส่วนเลือกโฟลเดอร์สำหรับ Save (Save Directory)
            _, state.m3u8_save_dir = imgui.input_text("Save Directory", state.m3u8_save_dir)
            imgui.same_line()
            if imgui.button("Browse##m3u8_dir"):
                # เรียกใช้ฟังก์ชันเปิดหน้าต่างเลือกโฟลเดอร์ (ที่เราสร้างไว้ก่อนหน้า)
                selected_folder = open_folder_dialog() 
                if selected_folder:
                    state.m3u8_save_dir = selected_folder
                    
            # 3. รับค่าชื่อไฟล์ปลายทาง
            _, state.m3u8_output = imgui.input_text("Output (.mp4)", state.m3u8_output)
            full_path = os.path.join(state.m3u8_save_dir, state.m3u8_output)
            imgui.text_disabled(f"Full Path: {full_path}")
            imgui.spacing()
            imgui.begin_disabled(state.is_running)
            
            # 4. เมื่อกดปุ่ม ส่งพารามิเตอร์ให้ครบตามที่ downloader.py ต้องการ
            if imgui.button("Start M3U8 Download"):
                # ลำดับพารามิเตอร์: ffmpeg_path, url, save_dir, filename, max_workers
                start_thread(
                    downloader.run_m3u8_download, 
                    state.ffmpeg_path, 
                    state.m3u8_url, 
                    state.m3u8_save_dir, 
                    state.m3u8_output, 
                    state.max_workers
                )
                
            imgui.end_disabled()
            imgui.end_tab_item()

        # --- TAB 2: NORMAL ---
        opened, _ = imgui.begin_tab_item("Normal Video")
        if opened:
            # 1. รับค่า URL ไฟล์ปกติ
            _, state.normal_url = imgui.input_text("Video URL", state.normal_url)
            
            # 2. ส่วนเลือกโฟลเดอร์สำหรับ Save พร้อมปุ่ม Browse
            _, state.normal_save_dir = imgui.input_text("Save Directory", state.normal_save_dir)
            imgui.same_line()
            if imgui.button("Browse##normal_dir"):
                selected_folder = open_folder_dialog()
                if selected_folder:
                    state.normal_save_dir = selected_folder
                    
            # 3. รับชื่อไฟล์
            _, state.normal_filename = imgui.input_text("Output (.mp4)", state.normal_filename)
            
            # คำนวณ Path เต็มสำหรับตรวจสอบ (แสดงให้ผู้ใช้เห็นหรือใช้ภายใน)
            full_path = os.path.join(state.normal_save_dir, state.normal_filename)
            imgui.text_disabled(f"Full Path: {full_path}")

            imgui.spacing()
            imgui.begin_disabled(state.is_running)
            
            # 4. เมื่อกดปุ่ม ส่งพารามิเตอร์ไปยัง downloader.run_normal_download
            if imgui.button("Start VIDEO Download"):
                # ใช้ full_path ที่รวม Save Dir และ Filename เข้าด้วยกันแล้ว
                start_thread(downloader.run_normal_download, state.normal_url, full_path)
                
            imgui.end_disabled()
            imgui.end_tab_item()

        # --- TAB 3: CONVERTER ---
        opened, _ = imgui.begin_tab_item("Converter")
        if opened:
            _, state.conv_input = imgui.input_text("Source File", state.conv_input)
            imgui.same_line()
            if imgui.button("Browse##merger_files"):
                # ใช้หน้าต่างเลือกไฟล์แบบหลายไฟล์พร้อมกัน (Multiple Selection)
                root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)
                files = filedialog.askopenfilenames(
                    title="Select Video Clips",
                    filetypes=[("Video", "*.mp4 *.mkv *.ts *.avi"), ("All", "*.*")]
                )
                root.destroy()
                
                # ถ้ามีการเลือกไฟล์ ให้เพิ่มเข้าไปในลิสต์ทันที
                if files:
                    state.conv_input = files[0]

            _, state.conv_output = imgui.input_text("Output Name", state.conv_output)
            _, state.selected_codec_idx = imgui.combo("Codec", state.selected_codec_idx, ["H.264", "H.265"])
            imgui.begin_disabled(state.is_running)
            if imgui.button("Convert to MP4"):
                codec_name = state.codecs[state.selected_codec_idx]
                start_thread(converter.run_conversion, state.ffmpeg_path, state.conv_input, state.conv_output, codec_name)
            imgui.end_disabled()
            imgui.end_tab_item()

        # --- TAB: VIDEO MERGER ---
        opened, _ = imgui.begin_tab_item("Video Merger")
        if opened:
            imgui.text("Add video clips to merge (Order matters):")
            
            # 1. ส่วนเลือกไฟล์ (Browse & Manual)
            _, state.merge_input_path = imgui.input_text("Clip Path", state.merge_input_path)
            
            imgui.same_line()
            if imgui.button("Browse##merger_files"):
                # ใช้หน้าต่างเลือกไฟล์แบบหลายไฟล์พร้อมกัน (Multiple Selection)
                root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)
                files = filedialog.askopenfilenames(
                    title="Select Video Clips",
                    filetypes=[("Video", "*.mp4 *.mkv *.ts *.avi"), ("All", "*.*")]
                )
                root.destroy()
                
                # ถ้ามีการเลือกไฟล์ ให้เพิ่มเข้าไปในลิสต์ทันที
                if files:
                    for f in files:
                        state.merge_list.append(f)

            imgui.same_line()
            if imgui.button("Add Manual"):
                if state.merge_input_path.strip():
                    state.merge_list.append(state.merge_input_path)
                    state.merge_input_path = ""
            
            # 2. แสดงรายการไฟล์ที่เตรียมจะรวม
            imgui.text_disabled(f"Total Clips: {len(state.merge_list)}")
            imgui.begin_child("MergeList", (0, 150), imgui.ChildFlags_.borders)
            
            # วนลูปแสดงรายการพร้อมปุ่มลบทีละไฟล์ (แถมเพิ่มให้เพื่อความสะดวกครับ)
            temp_list = state.merge_list.copy()
            for i, p in enumerate(temp_list):
                imgui.push_id(str(i))
                if imgui.button("X"): # ปุ่มลบเฉพาะไฟล์นั้นๆ
                    state.merge_list.pop(i)
                imgui.same_line()
                imgui.text(f"{i+1}. {os.path.basename(p)}")
                imgui.pop_id()
                
            imgui.end_child()

            if imgui.button("Clear All"):
                state.merge_list.clear()
            
            imgui.separator()
            
            # 3. ส่วนตั้งค่า Output
            _, state.merge_output_name = imgui.input_text("Output Name (.mp4)", state.merge_output_name)
            
            # ปุ่มเริ่มทำงาน
            imgui.begin_disabled(state.is_running or len(state.merge_list) < 2)
            if imgui.button("Start Merge Clips (FFmpeg)"):
                start_thread(merger.video_merge, state.ffmpeg_path, state.merge_list.copy(), state.merge_output_name)
            imgui.end_disabled()
            
            imgui.end_tab_item()
            
        # --- TAB 4: SETTINGS ---
        opened, _ = imgui.begin_tab_item("Settings")
        if opened:
            imgui.text("Application Settings")
            _, state.max_workers = imgui.input_int("Threads", state.max_workers)
            _, state.ffmpeg_path = imgui.input_text("FFmpeg Path", state.ffmpeg_path)
            imgui.same_line()
            if imgui.button("Browse##merger_files"):
                # ใช้หน้าต่างเลือกไฟล์แบบหลายไฟล์พร้อมกัน (Multiple Selection)
                root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)
                files = filedialog.askopenfilenames(
                    title="Select ffmpeg.exe",
                    filetypes=[(".EXE", "*.exe"), ("All", "*.*")]
                )
                root.destroy()
                
                # ถ้ามีการเลือกไฟล์ ให้เพิ่มเข้าไปในลิสต์ทันที
                if files:
                    state.ffmpeg_path = files[0]

            imgui.text_disabled("EXAMPLE: C:/ffmpeg/bin/ffmpeg.exe")
            imgui.separator()
            imgui.text("UI Customization (Font)")
            imgui.text_colored((1.0, 0.4, 0.4, 1.0), "* Restart required to apply new font")
            
            # ปุ่มเปลี่ยนเป็น Century Gothic
            if imgui.button("Select Century Gothic"):
                state.selected_font_path = "fonts/centurygothic.ttf"
                state.save_config()
                state.add_log("Font set to Century Gothic. Please restart.")
            
            imgui.same_line()
            
            # ปุ่มเปลี่ยนเป็น Roboto Mono
            if imgui.button("Select Roboto Mono"):
                state.selected_font_path = "fonts/RobotoMono-VariableFont_wght.ttf"
                state.save_config()
                state.add_log("Font set to Roboto Mono. Please restart.")
            
            imgui.spacing()
            if imgui.button("Close App Now"):
                os._exit(0) # ปิดโปรแกรมทันทีเพื่อให้ผู้ใช้เปิดใหม่

            imgui.text(f"Next boot font: {os.path.basename(state.selected_font_path)}")
            imgui.end_tab_item()

        # --- TAB 5: ABOUT ---
        opened, _ = imgui.begin_tab_item("About")
        if opened:
            imgui.spacing()
            imgui.text_colored((1.0, 0.8, 0.2, 1.0), "VIDEO TOOLKIT PRO")
            imgui.text("Version 1.0.0 (2026 Stable Release)")
            imgui.separator()

            # System Description
            imgui.text_wrapped(
                "A high-performance video management utility designed for seamless "
                "M3U8 downloading, video conversion, and fast merging operations "
                "powered by the industrial-grade FFmpeg engine."
            )
            imgui.text_colored((1.0, 0.0, 0.0, 1.0), "*This is free software and open-source for learn and use.")
            
            imgui.spacing()
            imgui.text_colored((0.4, 0.8, 1.0, 1.0), "Technical Stack:")
            imgui.bullet_text("Programming Language: Python 3.13")
            imgui.bullet_text("GUI Framework: Dear ImGui (via ImGui Bundle), tkinter")
            imgui.bullet_text("Processing Engine: FFmpeg (Multithreaded)")
            imgui.bullet_text("Architecture: Asynchronous Threading")

            imgui.spacing()
            imgui.separator()
            
            # Author Section
            imgui.text("Developed by:")
            imgui.same_line()
            imgui.text_colored((1.0, 1.0, 1.0, 1.0), "M4RTKL")
            imgui.spacing()
                
            imgui.end_tab_item()

        imgui.end_tab_bar()

    imgui.separator()
    imgui.text("Console Log:")
    imgui.begin_child("LogRegion", (0, 150), imgui.ChildFlags_.borders)
    for log in state.logs:
        if "Success" in log: imgui.text_colored((0.3, 1.0, 0.3, 1.0), log)
        elif "Error" in log: imgui.text_colored((1.0, 0.3, 0.3, 1.0), log)
        elif "Working" in log or "Started" in log: imgui.text_colored((1.0, 0.8, 0.0, 1.0), log)
        else: imgui.text(log)
    if imgui.get_scroll_y() >= imgui.get_scroll_max_y():
        imgui.set_scroll_here_y(1.0)
    imgui.end_child()

    imgui.text_colored((0.4, 0.8, 1.0, 1.0), state.log_msg)
    imgui.end()

if __name__ == "__main__":
    # 1. ตั้งค่าพื้นฐานก่อนรัน
    runner_params = hello_imgui.RunnerParams()
    runner_params.app_window_params.window_title = "Video Tool PRO"
    runner_params.app_window_params.window_geometry.size = (800, 600)

    # 2. เชื่อมต่อ Callbacks
    # สำคัญ: ตรวจสอบให้แน่ใจว่าได้ระบุชื่อฟังก์ชันที่สร้างไว้ด้านบน
    runner_params.callbacks.load_additional_fonts = load_fonts
    runner_params.callbacks.show_gui = gui

    # 3. สั่งรันโปรแกรม
    try:
        immapp.run(runner_params)
    except Exception as e:
        print(f"Application Error: {e}")