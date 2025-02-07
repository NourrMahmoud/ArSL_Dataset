# Main application for collecting Arabic Sign Language dataset
# This tool allows recording of both static images and dynamic videos of signs

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
        # Basic configuration
        self.username = username
        self.signs_dir = signs_dir
        self.sign_config = {}
        self.load_sign_configuration()
        
        # Initialize MediaPipe for pose and hand tracking
        self.mp_pose = mp.solutions.pose
        self.mp_hands = mp.solutions.hands
        self.pose = self.mp_pose.Pose(min_detection_confidence=0.5)
        self.hands = self.mp_hands.Hands(min_detection_confidence=0.5)
        
        # Set up data storage
        self.data_dir = "ArSL_Dataset"
        self._create_directories()
        
        # Camera and frame handling setup
        self.cap = cv2.VideoCapture(0)
        self.frame_queue = queue.Queue(maxsize=2)  # Small queue to reduce latency
        self.preview_queue = queue.Queue(maxsize=1)  # Preview queue for UI updates
        self.last_frame_time = 0
        self.frame_interval = 1.0 / 30  # Target 30 frames per second
        
        # Recording state
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
        current_time = time.time()
        # Control frame rate to maintain consistent recording speed
        if current_time - self.last_frame_time < self.frame_interval:
            return None
            
        # Flip frame horizontally for more intuitive preview
        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        
        # Track body pose
        pose_results = self.pose.process(rgb)
        if pose_results.pose_landmarks:
            mp.solutions.drawing_utils.draw_landmarks(
                frame, pose_results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS)
        
        # Track hand movements
        hand_results = self.hands.process(rgb)
        if hand_results.multi_hand_landmarks:
            for landmarks in hand_results.multi_hand_landmarks:
                mp.solutions.drawing_utils.draw_landmarks(
                    frame, landmarks, self.mp_hands.HAND_CONNECTIONS)
        
        self.last_frame_time = current_time
        return frame

    def camera_loop(self):
        """Main camera capture loop that runs in a separate thread"""
        while self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                continue
                
            processed = self.process_frame(frame)
            if processed is not None:
                # Smart frame dropping: only keep most recent frames
                try:
                    self.frame_queue.put_nowait(processed)
                except queue.Full:
                    # If queue is full, remove oldest frame
                    try:
                        self.frame_queue.get_nowait()
                        self.frame_queue.put_nowait(processed)
                    except (queue.Empty, queue.Full):
                        pass
                
                # Create smaller preview for UI
                preview_frame = cv2.resize(processed, (320, 240))
                try:
                    self.preview_queue.put_nowait(preview_frame)
                except queue.Full:
                    try:
                        self.preview_queue.get_nowait()
                        self.preview_queue.put_nowait(preview_frame)
                    except (queue.Empty, queue.Full):
                        pass

class CollectorGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ArSL Dataset Collector Pro v4")
        self.geometry("1200x800")
        self.minsize(800, 600)
        
        # Initialize timing variables first
        self.last_preview_update = time.time()
        self.preview_interval = 1.0 / 15  # 15 FPS for preview
        
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
        
        self.current_video_count = 0
        self.total_videos = 0
        
        # Control panel at bottom (fixed height)
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=1, column=0, sticky="sew", padx=10, pady=10)
        
        # Add sign selector to control frame (new location)
        selector_frame = ttk.Frame(control_frame)
        selector_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        ttk.Label(selector_frame, text="Select Sign:").pack(side=tk.LEFT, padx=5)
        self.sign_selector = ttk.Combobox(selector_frame, state="readonly", width=30)
        self.sign_selector.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.sign_selector.bind('<<ComboboxSelected>>', self.on_sign_selected)
        
        # Add delay configuration and buttons
        self.initial_delay = 3
        self.video_delay = 1
        self.collection_running = False
        
        # Control buttons frame
        buttons_frame = ttk.Frame(control_frame)
        buttons_frame.pack(side=tk.LEFT, padx=5)
        
        self.delay_btn = ttk.Button(buttons_frame, text="Set Delays", 
                                  command=self.set_delays)
        self.delay_btn.pack(side=tk.LEFT, padx=2)
        
        self.play_btn = ttk.Button(buttons_frame, text="▶", width=5, 
                                 command=self.toggle_media_playback)
        self.play_btn.pack(side=tk.LEFT, padx=2)
        
        self.start_btn = ttk.Button(buttons_frame, text="Start Collection", 
                                  command=self.start_collection)
        self.start_btn.pack(side=tk.LEFT, padx=2)
        
        self.test_btn = ttk.Button(buttons_frame, text="Test Recording", 
                                 command=self.toggle_test_recording)
        self.test_btn.pack(side=tk.LEFT, padx=2)
        
        self.duration_btn = ttk.Button(buttons_frame, text="Set Duration", 
                                     command=self.set_duration)
        self.duration_btn.pack(side=tk.LEFT, padx=2)
        
        # Progress bar
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
        
        # Add keyboard shortcuts
        self.bind('<space>', lambda e: self.toggle_media_playback())
        self.bind('<Control-s>', lambda e: self.start_collection())
        self.bind('<Control-t>', lambda e: self.toggle_test_recording())
        self.bind('<Escape>', lambda e: self.emergency_stop())
        
        # Add tooltips to buttons
        self.create_tooltips()
        
        # Add session tracking
        self.session_stats = {
            'recorded_items': 0,
            'start_time': time.time(),
            'completed_signs': set()
        }
        
        # Add a menu bar
        self.create_menu()
        
    def set_delays(self):
        popup = tk.Toplevel()
        popup.title("Set Recording Delays")
        
        ttk.Label(popup, text="Initial delay (seconds):").grid(row=0, column=0, padx=5, pady=5)
        initial_entry = ttk.Entry(popup)
        initial_entry.insert(0, str(self.initial_delay))
        initial_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(popup, text="Delay between videos:").grid(row=1, column=0, padx=5, pady=5)
        video_entry = ttk.Entry(popup)
        video_entry.insert(0, str(self.video_delay))
        video_entry.grid(row=1, column=1, padx=5, pady=5)
        
        def save_delays():
            self.initial_delay = int(initial_entry.get())
            self.video_delay = int(video_entry.get())
            popup.destroy()
        
        ttk.Button(popup, text="Save", command=save_delays).grid(row=2, columnspan=2, pady=10)

        
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
            
        # Populate sign selector
        all_signs = [(f"Static: {s}", 'static', i) for i, s in enumerate(self.signs['static'])]
        all_signs.extend([(f"Dynamic: {s}", 'dynamic', i) for i, s in enumerate(self.signs['dynamic'])])
        
        self.sign_selector['values'] = [s[0] for s in all_signs]
        self.sign_mappings = {s[0]: (s[1], s[2]) for s in all_signs}
        
        if self.sign_selector['values']:
            self.sign_selector.set(self.sign_selector['values'][0])
            self.show_current_sign()

    def on_sign_selected(self, event):
        selected = self.sign_selector.get()
        if selected in self.sign_mappings:
            sign_type, idx = self.sign_mappings[selected]
            if sign_type == 'static':
                self.current_sign_index = idx
            else:
                self.current_sign_index = len(self.signs['static']) + idx
            self.show_current_sign()

    def update_camera_preview(self):
        current_time = time.time()
        if current_time - self.last_preview_update >= self.preview_interval:
            try:
                frame = self.collector.preview_queue.get_nowait()
                img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                
                # Cache container size
                if not hasattr(self, '_container_size'):
                    self._container_size = (
                        self.camera_frame.winfo_width(),
                        self.camera_frame.winfo_height()
                    )
                
                # Only resize if container size has changed
                if (self._container_size[0] != self.camera_frame.winfo_width() or
                    self._container_size[1] != self.camera_frame.winfo_height()):
                    self._container_size = (
                        self.camera_frame.winfo_width(),
                        self.camera_frame.winfo_height()
                    )
                    
                if self._container_size[0] > 0 and self._container_size[1] > 0:
                    img = self._resize_with_aspect_ratio(img, 
                                                       self._container_size[0], 
                                                       self._container_size[1])
                    
                imgtk = ImageTk.PhotoImage(image=img)
                self.camera_label.imgtk = imgtk
                self.camera_label.configure(image=imgtk)
                self.last_preview_update = current_time
                
            except queue.Empty:
                pass
                
        self.after(max(1, int(self.preview_interval * 1000)), self.update_camera_preview)

    def show_current_sign(self):
        # Update the combobox selection to match current_sign_index
        if self.current_sign_index < len(self.signs['static']):
            sign_type = 'static'
            sign_name = self.signs['static'][self.current_sign_index]
            display_name = f"Static: {sign_name}"
        else:
            sign_type = 'dynamic'
            idx = self.current_sign_index - len(self.signs['static'])
            sign_name = self.signs['dynamic'][idx]
            display_name = f"Dynamic: {sign_name}"
        
        self.sign_selector.set(display_name)
        media_path = os.path.join(self.signs_dir, sign_type, sign_name)
        self.play_media(media_path)
        self.status.config(text=f"Current sign: {os.path.splitext(sign_name)[0]} ({sign_type})")

    def play_media(self, path):
        if self.media_player:
            self.media_player.stop()
        
        ext = os.path.splitext(path)[1].lower()
        if ext in ['.jpg', '.png', '.jpeg']:
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
        if self.collection_running:
            return
        
        if self.current_sign_index >= len(self.signs['static']) + len(self.signs['dynamic']):
            self.show_completion_message()
            return

        if self.current_sign_index < len(self.signs['static']):
            # Static sign handling
            sign_file = self.signs['static'][self.current_sign_index]
            sign_name = os.path.splitext(sign_file)[0]
            
            count = simpledialog.askinteger("Images", 
                                        f"Number of images for {sign_name}:", 
                                        initialvalue=200)
            if count is None:  # User canceled
                return
                
            def start_with_countdown():
                self.collection_running = True
                self._start_countdown(self.initial_delay, 
                                    lambda: self.collect_static_sign(count))
                
            start_with_countdown()
        else:
            # Dynamic sign handling
            idx = self.current_sign_index - len(self.signs['static'])
            sign_file = self.signs['dynamic'][idx]
            sign_name = os.path.splitext(sign_file)[0]
            
            def ask_video_duration(video_count):
                duration = simpledialog.askinteger("Duration", 
                                                f"Duration per video (seconds):",
                                                initialvalue=self.collector.sign_config.get(sign_name, 5),
                                                parent=self)
                if duration is not None:
                    def start_with_countdown():
                        self.collection_running = True
                        self._start_countdown(self.initial_delay, 
                                           lambda: self.collect_dynamic_sign(sign_name, duration, video_count))
                    start_with_countdown()
            
            # Ask for number of videos first
            video_count = simpledialog.askinteger("Videos", 
                                               f"Number of videos for {sign_name}:",
                                               initialvalue=3,
                                               parent=self)
            if video_count is not None:
                self.after(100, lambda: ask_video_duration(video_count))  # Small delay to ensure proper window ordering

    def _start_countdown(self, seconds, callback=None):
        self.status.config(text=f"Starting in {seconds}...")
        if seconds > 0:
            self.after(1000, lambda: self._start_countdown(seconds-1, callback))
        else:
            self.status.config(text="Recording started!")
            if callback:
                callback()
            else:
                # Start the actual collection process
                if self.current_sign_index < len(self.signs['static']):
                    self.collect_static_sign()
                else:
                    self.collect_dynamic_sign()

    def collect_static_sign(self, count):
        sign_file = self.signs['static'][self.current_sign_index]
        sign_name = os.path.splitext(sign_file)[0]
        
        # Create recording popup
        popup = tk.Toplevel()
        popup.title(f"Recording {sign_name}")
        popup.geometry("640x480")
        
        preview_label = ttk.Label(popup)
        preview_label.pack(fill=tk.BOTH, expand=True)
        
        progress = ttk.Progressbar(popup, orient=tk.HORIZONTAL)
        progress.pack(fill=tk.X, padx=10, pady=5)
        
        def actual_collection_thread():
            sign_dir = os.path.join(self.collector.data_dir, "Images", sign_name, self.collector.username)
            os.makedirs(sign_dir, exist_ok=True)
            
            for i in range(count):
                try:
                    frame = self.collector.frame_queue.get(timeout=1)
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(frame)
                    img.save(os.path.join(sign_dir, f"{sign_name}_{i}.jpg"))
                    
                    # Update progress and preview using proper thread-safe calls
                    self.after(0, lambda i=i: progress.config(value=(i+1)/count * 100))
                    self.after(0, lambda f=frame: self.update_popup_preview(preview_label, f))
                    
                except queue.Empty:
                    continue
            
            self.after(0, popup.destroy)
            self.current_sign_index += 1
            self.show_current_sign()
            self.check_completion()
            self.collection_running = False
            self.session_stats['recorded_items'] += count
            self.session_stats['completed_signs'].add(self.current_sign_index)
        
        threading.Thread(target=actual_collection_thread, daemon=True).start()
        
    def check_completion(self):
        if self.current_sign_index >= len(self.signs['static']) + len(self.signs['dynamic']):
            self.show_completion_message()
            
    def show_completion_message(self):
        messagebox.showinfo("Collection Complete", 
                        "All signs have been recorded!\n"
                        "Thank you for your participation.")
        
    def update_popup_preview(self, label, frame):
        img = Image.fromarray(frame)
        img = self._resize_with_aspect_ratio(img, 640, 480)
        imgtk = ImageTk.PhotoImage(image=img)
        label.imgtk = imgtk
        label.config(image=imgtk)

    def collect_dynamic_sign(self, sign_name, duration, video_count):
       def recording_thread():
           sign_dir = os.path.join(self.collector.data_dir, "Videos", sign_name, self.collector.username)
           os.makedirs(sign_dir, exist_ok=True)
        
           # Try different codecs in order of preference
           codecs = [
            ('XVID', 'avi'),
            ('mp4v', 'mp4'),
            ('MJPG', 'avi'),
           ]
        
           # Determine frame size from the camera
           frame_size = (int(self.collector.cap.get(3)), int(self.collector.cap.get(4)))
           
           # Record videos with working codec
           for video_num in range(video_count):
            # Test which codec works
            working_codec = None
            working_ext = None
            for codec, ext in codecs:
                fourcc = cv2.VideoWriter_fourcc(*codec)
                test_path = os.path.join(sign_dir, f"test.{ext}")
                test_writer = cv2.VideoWriter(test_path, fourcc, 30, frame_size)
                if test_writer.isOpened():
                    test_writer.release()
                    os.remove(test_path)   # Clean up test file
                    working_codec = codec
                    working_ext = ext
                    break
            
            if not working_codec:
                # If no codec worked
                self.after(0, lambda: messagebox.showerror("Error", "No suitable codec found!"))
                return
            
            video_path = os.path.join(sign_dir, f"{sign_name}_{video_num}.{working_ext}")
            
            # Collect all frames during the duration
            start_time = time.time()
            frames = []
            
            while (time.time() - start_time) < duration and self.collection_running:
                try:
                    frame = self.collector.frame_queue.get(timeout=0.1)
                    frames.append(frame)
                except queue.Empty:
                    continue
            
            # Calculate actual FPS based on desired duration
            if duration <= 0:
                actual_fps = 30  # Prevent division by zero, use default
            else:
                actual_fps = max(1, len(frames) / duration)  # Ensure minimum 1 FPS
            
            # Initialize VideoWriter with calculated FPS
            fourcc = cv2.VideoWriter_fourcc(*working_codec)
            out = cv2.VideoWriter(video_path, fourcc, actual_fps, frame_size)
            
            if not out.isOpened():
                self.after(0, lambda: messagebox.showerror("Error", f"Failed to create video {video_num + 1}"))
                continue
            
            # Write all collected frames
            for frame in frames:
                out.write(frame)
            
            out.release()
            
            # Only show the delay popup if this is not the last video
            if video_num < video_count - 1:
                # Create and show the delay popup
                self.after(0, lambda: self.show_delay_popup(video_num + 1, video_count))
                # Wait for the configured delay
                time.sleep(self.video_delay)
                # Remove the popup
                self.after(0, lambda: self.remove_delay_popup())
        
           self.after(0, lambda: self.update_ui_after_recording())

       threading.Thread(target=recording_thread, daemon=True).start()

    def show_delay_popup(self, current_video, total_videos):
        """Show a popup during the delay between videos"""
        self.delay_popup = tk.Toplevel(self)
        self.delay_popup.title("Get Ready")
        self.delay_popup.geometry("300x150")
        
        # Center the popup on screen
        self.delay_popup.transient(self)
        self.delay_popup.grab_set()
        
        # Add message
        message = f"Video {current_video} completed!\nGet ready for video {current_video + 1} of {total_videos}\n\nWaiting {self.video_delay} seconds..."
        label = ttk.Label(self.delay_popup, text=message, wraplength=250, justify='center')
        label.pack(expand=True)
        
        # Center the popup on the main window
        x = self.winfo_x() + (self.winfo_width() // 2) - (300 // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (150 // 2)
        self.delay_popup.geometry(f"+{x}+{y}")

    def remove_delay_popup(self):
        """Remove the delay popup if it exists"""
        if hasattr(self, 'delay_popup') and self.delay_popup is not None:
            self.delay_popup.destroy()
            self.delay_popup = None

    def update_ui_after_recording(self):
        """Update UI elements after recording completion"""
        self.current_sign_index += 1
        self.show_current_sign()
        self.collection_running = False
        self.session_stats['recorded_items'] += 1
        self.session_stats['completed_signs'].add(self.current_sign_index)
        self.status.config(text="Recording completed")

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
        
        # Try different codecs
        codecs = [
            ('XVID', 'avi'),
            ('mp4v', 'mp4'),
            ('MJPG', 'avi'),
        ]
        
        # Find working codec
        for codec, ext in codecs:
            try:
                fourcc = cv2.VideoWriter_fourcc(*codec)
                frame_size = (int(self.collector.cap.get(3)), int(self.collector.cap.get(4)))
                self.test_video_path = os.path.join("test_recordings", f"test_{time.time()}.{ext}")
                os.makedirs("test_recordings", exist_ok=True)
                
                self.test_writer = cv2.VideoWriter(self.test_video_path, fourcc, 30, frame_size)
                if self.test_writer.isOpened():
                    break
            except Exception:
                continue
        else:
            messagebox.showerror("Error", "Could not initialize video recording")
            self.recording_popup.destroy()
            return
        
        # Rest of the test recording code
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

    def create_tooltips(self):
        self.tooltips = {}
        tips = {
            self.play_btn: "Play/Pause (Space)",
            self.start_btn: "Start Collection (Ctrl+S)",
            self.test_btn: "Test Recording (Ctrl+T)",
            self.duration_btn: "Set Video Duration",
            self.delay_btn: "Configure Recording Delays",
            self.sign_selector: "Select Sign to Record"
        }
        
        for widget, text in tips.items():
            self.create_tooltip(widget, text)
    
    def create_tooltip(self, widget, text):
        def enter(event):
            tooltip = tk.Toplevel()
            tooltip.withdraw()
            tooltip.overrideredirect(True)
            label = ttk.Label(tooltip, text=text, padding=(5, 3))
            label.pack()
            
            x = widget.winfo_rootx() + widget.winfo_width()//2
            y = widget.winfo_rooty() + widget.winfo_height() + 5
            tooltip.geometry(f"+{x}+{y}")
            tooltip.deiconify()
            self.tooltips[widget] = tooltip
            
        def leave(event):
            if widget in self.tooltips:
                self.tooltips[widget].destroy()
                del self.tooltips[widget]
                
        widget.bind('<Enter>', enter)
        widget.bind('<Leave>', leave)
    
    def create_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Change Signs Directory", command=self.change_signs_directory)
        file_menu.add_command(label="Export Session Stats", command=self.export_session_stats)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)
        
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="View Progress", command=self.show_progress_window)
        tools_menu.add_command(label="Settings", command=self.show_settings)
    
    def emergency_stop(self):
        """Stop all recording activities immediately"""
        self.test_recording_active = False
        self.collection_running = False
        if hasattr(self, 'recording_popup') and self.recording_popup:
            self.recording_popup.destroy()
        self.status.config(text="Recording stopped (Emergency)")
        
    def show_progress_window(self):
        """Show detailed progress information"""
        progress = tk.Toplevel()
        progress.title("Recording Progress")
        progress.geometry("400x300")
        
        # Calculate statistics
        total_signs = len(self.signs['static']) + len(self.signs['dynamic'])
        completed = len(self.session_stats['completed_signs'])
        elapsed_time = time.time() - self.session_stats['start_time']
        
        # Create progress display
        ttk.Label(progress, text=f"Completed: {completed}/{total_signs} signs").pack(pady=5)
        ttk.Label(progress, text=f"Session time: {int(elapsed_time/60)} minutes").pack(pady=5)
        ttk.Label(progress, text=f"Items recorded: {self.session_stats['recorded_items']}").pack(pady=5)
        
        # Add progress bars
        progress_frame = ttk.LabelFrame(progress, text="Progress by type")
        progress_frame.pack(fill=tk.X, padx=5, pady=5)
        
        static_progress = ttk.Progressbar(progress_frame)
        static_progress.pack(fill=tk.X, padx=5, pady=5)
        static_progress['value'] = (len([s for s in self.session_stats['completed_signs'] 
                                       if s < len(self.signs['static'])]) / len(self.signs['static'])) * 100
        
        dynamic_progress = ttk.Progressbar(progress_frame)
        dynamic_progress.pack(fill=tk.X, padx=5, pady=5)
        dynamic_progress['value'] = (len([s for s in self.session_stats['completed_signs'] 
                                        if s >= len(self.signs['static'])]) / len(self.signs['dynamic'])) * 100
    
    def show_settings(self):
        """Show comprehensive settings dialog"""
        settings = tk.Toplevel()
        settings.title("Settings")
        settings.geometry("500x400")
        
        notebook = ttk.Notebook(settings)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # User settings
        user_frame = ttk.Frame(notebook)
        notebook.add(user_frame, text="User")
        
        ttk.Label(user_frame, text="Username:").grid(row=0, column=0, padx=5, pady=5)
        username_entry = ttk.Entry(user_frame)
        username_entry.insert(0, self.collector.username)
        username_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # Recording settings
        recording_frame = ttk.Frame(notebook)
        notebook.add(recording_frame, text="Recording")
        
        ttk.Label(recording_frame, text="Initial delay (seconds):").grid(row=0, column=0, padx=5, pady=5)
        initial_delay = ttk.Entry(recording_frame)
        initial_delay.insert(0, str(self.initial_delay))
        initial_delay.grid(row=0, column=1, padx=5, pady=5)
        
        # Camera settings
        camera_frame = ttk.Frame(notebook)
        notebook.add(camera_frame, text="Camera")
        
        # Add camera resolution selection
        ttk.Label(camera_frame, text="Resolution:").grid(row=0, column=0, padx=5, pady=5)
        resolutions = ["640x480", "1280x720", "1920x1080"]
        resolution_cb = ttk.Combobox(camera_frame, values=resolutions)
        resolution_cb.grid(row=0, column=1, padx=5, pady=5)
        
        def save_settings():
            # Handle username change
            new_username = username_entry.get().strip()
            if new_username and new_username != self.collector.username:
                if messagebox.askyesno("Confirm Change", 
                                     "Changing username will create a new folder for recordings.\n"
                                     "Are you sure you want to continue?"):
                    self.collector.username = new_username
                    self.status.config(text=f"Username changed to: {new_username}")
            
            self.initial_delay = int(initial_delay.get())
            settings.destroy()
            
        ttk.Button(settings, text="Save", command=save_settings).pack(pady=10)

    def export_session_stats(self):
        """Export session statistics to a file"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile=f"session_stats_{time.strftime('%Y%m%d_%H%M%S')}.json"
        )
        if filename:
            stats = {
                'duration': time.time() - self.session_stats['start_time'],
                'completed_signs': len(self.session_stats['completed_signs']),
                'recorded_items': self.session_stats['recorded_items'],
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            with open(filename, 'w') as f:
                json.dump(stats, f, indent=2)

    def change_signs_directory(self):
        """Allow changing the signs directory during runtime"""
        new_dir = filedialog.askdirectory(title="Select New Signs Directory")
        if not new_dir:
            return
            
        if not os.path.exists(os.path.join(new_dir, "static")):
            messagebox.showerror("Error", "Invalid signs directory structure!")
            return
            
        # Update directory and reload signs
        self.signs_dir = new_dir
        self.collector.signs_dir = new_dir
        
        # Reset session stats for new directory
        self.session_stats = {
            'recorded_items': 0,
            'start_time': time.time(),
            'completed_signs': set()
        }
        
        # Reload signs and update UI
        self.current_sign_index = 0
        self.load_signs()
        self.status.config(text="Signs directory changed successfully")

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
