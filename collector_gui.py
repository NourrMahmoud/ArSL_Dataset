# arsl_collector_pro_v4.py
import cv2
import mediapipe as mp
import os
import time
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from PIL import Image, ImageTk, ImageOps
import json
import threading
import queue
import math

class SignDatasetCollector:
    def __init__(self, username, signs_dir):
        self.username = username
        self.signs_dir = signs_dir
        self.sign_config = {}
        self.load_sign_configuration()
        
        self.mp_pose = mp.solutions.pose
        self.mp_hands = mp.solutions.hands
        self.pose = self.mp_pose.Pose(min_detection_confidence=0.5)
        self.hands = self.mp_hands.Hands(min_detection_confidence=0.5)
        
        self.data_dir = "ArSL_Dataset"
        self._create_directories()
        
        self.cap = cv2.VideoCapture(0)
        self.frame_queue = queue.Queue(maxsize=1)
        self.recording = False
        self.test_recording = False
        self.current_sign = None
        self.current_media = None

    def _create_directories(self):
        os.makedirs(os.path.join(self.data_dir, "Images"), exist_ok=True)
        os.makedirs(os.path.join(self.data_dir, "Videos"), exist_ok=True)

    def load_sign_configuration(self):
        config_path = os.path.join(self.signs_dir, "sign_config.json")
        if os.path.exists(config_path):
            with open(config_path) as f:
                self.sign_config = json.load(f)

    def save_sign_configuration(self):
        config_path = os.path.join(self.signs_dir, "sign_config.json")
        with open(config_path, 'w') as f:
            json.dump(self.sign_config, f)

    def get_signs(self):
        signs = {"static": [], "dynamic": []}
        for f in os.listdir(os.path.join(self.signs_dir, "static")):
            if os.path.splitext(f)[1].lower() in ['.jpg', '.png', '.mp4']:
                signs["static"].append(f)
        for f in os.listdir(os.path.join(self.signs_dir, "dynamic")):
            if os.path.splitext(f)[1].lower() in ['.mp4', '.avi']:
                signs["dynamic"].append(f)
        return signs

    def process_frame(self, frame):
        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process pose
        pose_results = self.pose.process(rgb)
        if pose_results.pose_landmarks:
            mp.solutions.drawing_utils.draw_landmarks(
                frame, pose_results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS)
        
        # Process hands
        hand_results = self.hands.process(rgb)
        if hand_results.multi_hand_landmarks:
            for landmarks in hand_results.multi_hand_landmarks:
                mp.solutions.drawing_utils.draw_landmarks(
                    frame, landmarks, self.mp_hands.HAND_CONNECTIONS)
        
        return frame

    def camera_loop(self):
        while self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                processed = self.process_frame(frame)
                try:
                    self.frame_queue.put_nowait(processed)
                except queue.Full:
                    pass

class CollectorGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ArSL Dataset Collector Pro v4")
        self.geometry("1200x800")
        self.minsize(800, 600)
        
        # Configure grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Main container
        main_frame = ttk.Frame(self)
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)
        
        # Create paned window for resizable panels
        self.paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        self.paned_window.grid(row=0, column=0, sticky="nsew")
        
        # Camera preview
        self.camera_frame = ttk.LabelFrame(self.paned_window, text="Camera Preview")
        self.camera_label = ttk.Label(self.camera_frame)
        self.camera_label.pack(fill=tk.BOTH, expand=True)
        self.paned_window.add(self.camera_frame, weight=1)
        
        # Media preview
        self.media_frame = ttk.LabelFrame(self.paned_window, text="Sign Preview")
        self.media_label = ttk.Label(self.media_frame)
        self.media_label.pack(fill=tk.BOTH, expand=True)
        self.paned_window.add(self.media_frame, weight=1)
        
        # Control panel at bottom (fixed height)
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=1, column=0, sticky="sew", padx=10, pady=10)
        
        # Media controls in control panel
        self.play_btn = ttk.Button(control_frame, text="▶", width=5, 
                                 command=self.toggle_media_playback)
        self.play_btn.pack(side=tk.LEFT, padx=5)
        
        self.start_btn = ttk.Button(control_frame, text="Start Collection", 
                                  command=self.start_collection)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.test_btn = ttk.Button(control_frame, text="Test Recording", 
                                 command=self.toggle_test_recording)
        self.test_btn.pack(side=tk.LEFT, padx=5)
        
        self.duration_btn = ttk.Button(control_frame, text="Set Duration", 
                                     command=self.set_duration)
        self.duration_btn.pack(side=tk.LEFT, padx=5)
        
        self.progress = ttk.Progressbar(control_frame, orient=tk.HORIZONTAL)
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Status bar
        self.status = ttk.Label(self, text="Ready", anchor=tk.W)
        self.status.grid(row=1, column=0, sticky="sew")
        
        # Configure row weights
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=0)
        main_frame.grid_rowconfigure(2, weight=0)
        
        # Style configuration for bigger buttons
        self.style = ttk.Style()
        self.style.configure("TButton", font=('Helvetica', 10), padding=5)
        
        # Remaining initialization
        self.signs_dir = ""
        self.collector = None
        self.current_sign_index = 0
        self.signs = {"static": [], "dynamic": []}
        self.media_player = None
        self.test_video_path = ""
        self.recording_popup = None
        self.test_recording_active = False
        
        self._ask_signs_directory()
        self._ask_username()
        
    def _create_recording_popup(self, title):
        popup = tk.Toplevel()
        popup.title(title)
        popup.geometry("640x480")
        popup.grid_columnconfigure(0, weight=1)
        popup.grid_rowconfigure(0, weight=1)
        
        preview_label = ttk.Label(popup)
        preview_label.grid(row=0, column=0, sticky="nsew")
        
        control_frame = ttk.Frame(popup)
        control_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        
        stop_btn = ttk.Button(control_frame, text="Stop Recording", 
                            command=lambda: self.stop_recording(popup))
        stop_btn.pack(side=tk.RIGHT)
        
        return popup, preview_label

    def stop_recording(self, popup):
        self.test_recording_active = False
        if popup:
            popup.destroy()
        self.status.config(text="Test recording stopped")

    def _create_widgets(self):
        # Main container
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Camera preview
        self.camera_frame = ttk.LabelFrame(main_frame, text="Camera Preview")
        self.camera_frame.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.BOTH, expand=True)
        self.camera_label = ttk.Label(self.camera_frame)
        self.camera_label.pack(fill=tk.BOTH, expand=True)
        
        # Media preview
        self.media_frame = ttk.LabelFrame(main_frame, text="Sign Preview")
        self.media_frame.pack(side=tk.RIGHT, padx=10, pady=10, fill=tk.BOTH, expand=True)
        self.media_label = ttk.Label(self.media_frame)
        self.media_label.pack(fill=tk.BOTH, expand=True)
        
        # Media controls
        self.media_control_frame = ttk.Frame(self.media_frame)
        self.media_control_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.play_btn = ttk.Button(self.media_control_frame, text="▶", width=3, 
                                 command=self.toggle_media_playback)
        self.play_btn.pack(side=tk.LEFT)
        
        # Progress and controls
        control_frame = ttk.Frame(self)
        control_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
        
        self.start_btn = ttk.Button(control_frame, text="Start Collection", 
                                  command=self.start_collection)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.test_btn = ttk.Button(control_frame, text="Test Recording", 
                                 command=self.toggle_test_recording)
        self.test_btn.pack(side=tk.LEFT, padx=5)
        
        self.duration_btn = ttk.Button(control_frame, text="Set Duration", 
                                     command=self.set_duration)
        self.duration_btn.pack(side=tk.LEFT, padx=5)
        
        self.progress = ttk.Progressbar(control_frame, orient=tk.HORIZONTAL)
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.status = ttk.Label(self, text="Ready", anchor=tk.W)
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

    def _ask_signs_directory(self):
        self.signs_dir = filedialog.askdirectory(title="Select Signs Directory")
        if not self.signs_dir:
            self.destroy()
        elif not os.path.exists(os.path.join(self.signs_dir, "static")):
            messagebox.showerror("Error", "Invalid signs directory structure!")
            self.destroy()

    def _ask_username(self):
        username = simpledialog.askstring("Username", "Enter your username:")
        if not username:
            self.destroy()
            return
        self.collector = SignDatasetCollector(username, self.signs_dir)
        self.load_signs()
        threading.Thread(target=self.collector.camera_loop, daemon=True).start()
        self.update_camera_preview()

    def load_signs(self):
        self.signs = self.collector.get_signs()
        if not self.signs['static'] and not self.signs['dynamic']:
            messagebox.showwarning("No Signs", "No signs found in directory!")
            self.destroy()
        self.show_current_sign()

    def update_camera_preview(self):
        try:
            frame = self.collector.frame_queue.get_nowait()
            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            
            # Get current container size
            container_width = self.camera_frame.winfo_width()
            container_height = self.camera_frame.winfo_height()
            
            if container_width > 0 and container_height > 0:
                img = self._resize_with_aspect_ratio(img, container_width, container_height)
                imgtk = ImageTk.PhotoImage(image=img)
                self.camera_label.imgtk = imgtk
                self.camera_label.configure(image=imgtk)
        except (queue.Empty, AttributeError, RuntimeError):
            pass
        self.after(50, self.update_camera_preview)

    def show_current_sign(self):
        if self.current_sign_index < len(self.signs['static']):
            sign_type = 'static'
            sign_name = self.signs['static'][self.current_sign_index]
        else:
            sign_type = 'dynamic'
            idx = self.current_sign_index - len(self.signs['static'])
            sign_name = self.signs['dynamic'][idx]
        
        media_path = os.path.join(self.signs_dir, sign_type, sign_name)
        self.play_media(media_path)
        self.status.config(text=f"Current sign: {os.path.splitext(sign_name)[0]} ({sign_type})")

    def play_media(self, path):
        if self.media_player:
            self.media_player.stop()
        
        ext = os.path.splitext(path)[1].lower()
        if ext in ['.jpg', '.png']:
            self.media_player = ImagePlayer(self.media_label, path)
        elif ext in ['.mp4', '.avi']:
            self.media_player = VideoPlayer(self.media_label, path)
        
        # Set initial size based on container
        container_width = self.media_frame.winfo_width()
        container_height = self.media_frame.winfo_height()
        self.media_player.resize(container_width, container_height)
        self.media_player.play()
        self.play_btn.config(text="||")

    def toggle_media_playback(self):
        if self.media_player and isinstance(self.media_player, VideoPlayer):
            if self.media_player.playing:
                self.media_player.pause()
                self.play_btn.config(text="▶")
            else:
                self.media_player.resume()
                self.play_btn.config(text="||")

    def start_collection(self):
        if self.current_sign_index >= len(self.signs['static']) + len(self.signs['dynamic']):
            messagebox.showinfo("Complete", "All signs collected!")
            return
        
        if self.current_sign_index < len(self.signs['static']):
            self.collect_static_sign()
        else:
            self.collect_dynamic_sign()

    def collect_static_sign(self):
        sign_file = self.signs['static'][self.current_sign_index]
        sign_name = os.path.splitext(sign_file)[0]
        count = simpledialog.askinteger("Images", f"Number of images for {sign_name}:", initialvalue=200)
        
        def collection_thread():
            sign_dir = os.path.join(self.collector.data_dir, "Images", sign_name, self.collector.username)
            os.makedirs(sign_dir, exist_ok=True)
            
            for i in range(count):
                frame = self.collector.frame_queue.get()
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame)
                img.save(os.path.join(sign_dir, f"{sign_name}_{i}.jpg"))
                self.status.config(text=f"Saved image {i+1}/{count} for {sign_name}")
                self.progress['value'] = (i+1)/count * 100
            
            self.current_sign_index += 1
            self.show_current_sign()
            self.progress['value'] = 0
        
        threading.Thread(target=collection_thread, daemon=True).start()

    def collect_dynamic_sign(self):
        idx = self.current_sign_index - len(self.signs['static'])
        sign_file = self.signs['dynamic'][idx]
        sign_name = os.path.splitext(sign_file)[0]
        duration = self.collector.sign_config.get(sign_name, 5)
    
        def recording_thread():
            self.recording_popup = tk.Toplevel()
            self.recording_popup.title("Recording Preview")
            self.recording_popup.geometry("640x480")
        
            self.recording_popup.grid_columnconfigure(0, weight=1)
            self.recording_popup.grid_rowconfigure(0, weight=1)
        
            preview_label = ttk.Label(self.recording_popup)
            preview_label.grid(row=0, column=0, sticky="nsew")
        
            sign_dir = os.path.join(self.collector.data_dir, "Videos", sign_name, self.collector.username)
            os.makedirs(sign_dir, exist_ok=True)
        
            fps = 30  # Keda 7adedna en elvideo hytsagel b sor3et 30 frame fe elsanya
            frame_interval = 1.0 / fps  # keda bn7seb elmoda been kol frame (about 0.033 sec)
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            frame_size = (int(self.collector.cap.get(3)), int(self.collector.cap.get(4)))
            out = cv2.VideoWriter(os.path.join(sign_dir, f"{sign_name}.mp4"), fourcc, fps, frame_size)
        
            start_time = time.time()
            next_frame_time = start_time # Keda hn7seb elwa2t elly elmafrood n7ot feeh elframe elly gy fel video
            end_time = start_time + duration
        
            while time.time() < end_time:
              current_time = time.time()
              if current_time < next_frame_time:
                # Sleep until the next frame interval, hena ka2ini ba2olo estana shwaya
                time.sleep(max(0, next_frame_time - current_time - 0.001))
            
              try:
                frame = self.collector.frame_queue.get(timeout=0.1)
                out.write(frame)
                next_frame_time += frame_interval
                
                # Update recording preview
                img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                img = self._resize_with_aspect_ratio(img, 
                                                   preview_label.winfo_width(),
                                                   preview_label.winfo_height())
                imgtk = ImageTk.PhotoImage(image=img)
                preview_label.imgtk = imgtk
                preview_label.config(image=imgtk)
                
                remaining = end_time - time.time()
                self.status.config(text=f"Recording {sign_name} - {math.ceil(remaining)}s remaining")
                self.recording_popup.update()
              except queue.Empty:
                continue
        
            out.release()
            self.recording_popup.destroy()
            self.current_sign_index += 1
            self.show_current_sign()
            self.status.config(text="Ready")
    
        threading.Thread(target=recording_thread, daemon=True).start()

    def _resize_with_aspect_ratio(self, image, max_width, max_height):
        original_width, original_height = image.size
        ratio = min(max_width/original_width, max_height/original_height)
        new_size = (int(original_width * ratio), int(original_height * ratio))
        return image.resize(new_size, Image.LANCZOS)

    def toggle_test_recording(self):
        if not self.test_recording_active:
            self.start_test_recording()
        else:
            self.stop_recording(self.recording_popup)

    def start_test_recording(self):
        self.test_recording_active = True
        self.recording_popup, preview_label = self._create_recording_popup("Test Recording Preview")
        self.test_video_path = os.path.join("test_recordings", f"test_{time.time()}.mp4")
        os.makedirs("test_recordings", exist_ok=True)
        
        fps = 30  # Fixed target FPS
        frame_interval = 1.0 / fps
        frame_size = (int(self.collector.cap.get(3)), int(self.collector.cap.get(4)))
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.test_writer = cv2.VideoWriter(self.test_video_path, fourcc, fps, frame_size)
        
        def recording_thread():
            try:
                next_frame_time = time.time()
                while self.test_recording_active:
                    current_time = time.time()
                    if current_time < next_frame_time:
                        time.sleep(max(0, next_frame_time - current_time - 0.001))
                    
                    try:
                        frame = self.collector.frame_queue.get(timeout=0.1)
                        self.test_writer.write(frame)
                        next_frame_time += frame_interval
                        
                        if self.recording_popup.winfo_exists():
                            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                            img = self._resize_with_aspect_ratio(img, 640, 480)
                            imgtk = ImageTk.PhotoImage(image=img)
                            self.after(0, lambda: self.update_preview(preview_label, imgtk))
                    except queue.Empty:
                        continue
            finally:
                self.test_writer.release()
                self.after(0, self.playback_test)
        
        threading.Thread(target=recording_thread, daemon=True).start()
    
    def record_video(self, sign_name, duration, progress_callback):
        self.recording = True
        fps = 30  # Fixed target FPS
        frame_interval = 1.0 / fps
        sign_dir = os.path.join(self.data_dir, "Videos", sign_name, self.username)
        os.makedirs(sign_dir, exist_ok=True)
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        frame_size = (int(self.cap.get(3)), int(self.cap.get(4)))
        out = cv2.VideoWriter(os.path.join(sign_dir, f"{sign_name}.mp4"), fourcc, fps, frame_size)
        
        start_time = time.time()
        next_frame_time = start_time
        
        while (time.time() - start_time) < duration and self.recording:
            current_time = time.time()
            if current_time < next_frame_time:
                time.sleep(max(0, next_frame_time - current_time - 0.001))  # Precision sleep
            
            try:
                frame = self.frame_queue.get(timeout=0.1)
                out.write(frame)
                next_frame_time += frame_interval
                progress_callback(f"Recording {sign_name} - {int(time.time() - start_time)}s/{duration}s")
            except queue.Empty:
                continue
        
        out.release()
    
    
    def update_preview(self, label, image):
        """Thread-safe preview update"""
        if label.winfo_exists():
            label.imgtk = image
            label.config(image=image)

    def record_test(self):
        while self.collector.test_recording:
            frame = self.collector.frame_queue.get()
            self.test_writer.write(frame)

    def stop_test_recording(self):
        self.collector.test_recording = False
        self.test_writer.release()
        self.test_btn.config(text="Test Recording")
        self.playback_test()

    def playback_test(self):
        if not os.path.exists(self.test_video_path):
            messagebox.showerror("Error", "Test recording file not found!")
            return
        
        def play_thread():
            cap = cv2.VideoCapture(self.test_video_path)
            if not cap.isOpened():
                messagebox.showerror("Error", "Could not open test recording!")
                return
            
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                cv2.imshow("Test Recording Playback", frame)
                if cv2.waitKey(30) == 27:  # ESC key
                    break
            cap.release()
            cv2.destroyAllWindows()
        
        # Wait briefly to ensure file is fully released
        time.sleep(0.5)
        threading.Thread(target=play_thread, daemon=True).start()

    def set_duration(self):
        idx = self.current_sign_index - len(self.signs['static'])
        sign_name = self.signs['dynamic'][idx].split('.')[0]
        duration = simpledialog.askinteger("Duration", 
                                          f"Video duration for {sign_name} (seconds):",
                                          initialvalue=self.collector.sign_config.get(sign_name, 5))
        if duration:
            self.collector.sign_config[sign_name] = duration
            self.collector.save_sign_configuration()

class MediaPlayer:
    def __init__(self, parent, path):
        self.parent = parent
        self.path = path
        self.playing = False

class VideoPlayer:
    def __init__(self, parent, path):
        self.parent = parent
        self.path = path
        self.cap = cv2.VideoCapture(path)
        self.playing = False
        self.delay = int(1000/self.cap.get(cv2.CAP_PROP_FPS))
        self.current_frame = 0
        self.container_width = 0
        self.container_height = 0

    def resize(self, width, height):
        self.container_width = width
        self.container_height = height

    def play(self):
        self.playing = True
        self._update_frame()

    def _update_frame(self):
        if self.playing and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                if self.container_width > 0 and self.container_height > 0:
                    img = ImageOps.pad(img, (self.container_width, self.container_height), color='black')
                self.tkimg = ImageTk.PhotoImage(image=img)
                self.parent.config(image=self.tkimg)
                self.parent.after(self.delay, self._update_frame)
            else:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                self._update_frame()

    def pause(self):
        self.playing = False

    def resume(self):
        self.playing = True
        self._update_frame()

    def stop(self):
        self.playing = False
        self.cap.release()


class ImagePlayer:
    def __init__(self, parent, path):
        self.parent = parent
        self.path = path
        self.img = Image.open(path)
        self.container_width = 0
        self.container_height = 0

    def resize(self, width, height):
        self.container_width = width
        self.container_height = height

    def play(self):
        if self.container_width > 0 and self.container_height > 0:
            img = ImageOps.pad(self.img, (self.container_width, self.container_height), color='black')
        else:
            img = self.img
        self.tkimg = ImageTk.PhotoImage(image=img)
        self.parent.config(image=self.tkimg)

    def stop(self):
        pass

if __name__ == "__main__":
    app = CollectorGUI()
    app.mainloop()
