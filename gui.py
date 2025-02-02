import tkinter as tk
from tkinter import ttk, messagebox
import cv2
from PIL import Image, ImageTk
import os
import time
import numpy as np
from tkvideo import tkvideo
from datasetCollector import DatasetCollector

class DatasetCollectorGUI(DatasetCollector):
    """
    GUI application for collecting ArSL (Arabic Sign Language) dataset.
    Inherits from DatasetCollector for base functionality.
    """
    
    def __init__(self):
        # Initialize base collector
        super().__init__()
        
        #######################
        # Initialize GUI vars #
        #######################
        self.root = tk.Tk()
        self.root.title("ArSL Dataset Collector")
        self.preview_size = (300, 300)  # Standard size for previews
        
        #########################
        # Directory Management  #
        #########################
        self.preview_signs_dir = "signs_directory"
        if not self._check_preview_directories():
            messagebox.showerror("Error", f"Required preview directory '{self.preview_signs_dir}' not found!")
            self.root.destroy()
            return
            
        # Load sign data
        try:
            self.static_words = self._load_preview_static_words()
            self.dynamic_words = self._load_preview_dynamic_words()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load preview signs: {str(e)}")
            self.root.destroy()
            return

        ############################
        # State tracking variables #
        ############################
        # Recording states
        self.is_recording = False
        self.is_test_recording = False
        self.recording_in_progress = False
        
        # Counters and timing
        self.current_sign_index = 0
        self.recorded_count = 0
        self.total_count = 0
        self.last_capture_time = 0
        self.capture_interval = 100  # ms between captures
        
        # Camera and recording objects
        self.cap = cv2.VideoCapture(0)
        self.current_frame = None
        self.current_recording = None
        self.recording_timer = None
        
        # User input variables
        self.video_delay = tk.StringVar(value="3")
        self.username = tk.StringVar(value="Nour")
        
        # Test recording variables
        self.is_test_playback = False
        self.test_video_path = None
        
        # Initialize GUI
        self._setup_gui()
        self._setup_preview()

    ################################
    # Directory Management Methods #
    ################################
    
    def _check_preview_directories(self):
        """Verify preview folders exist under 'signs_directory'"""
        required_dirs = [
            self.preview_signs_dir,
            os.path.join(self.preview_signs_dir, "images"),
            os.path.join(self.preview_signs_dir, "videos")
        ]
        return all(os.path.exists(d) for d in required_dirs)

    def _load_preview_static_words(self):
        """Load static preview words from signs_directory/images"""
        image_dir = os.path.join(self.preview_signs_dir, "images")
        return [os.path.splitext(f)[0] for f in os.listdir(image_dir)
                if f.lower().endswith(('.jpg', '.jpeg', '.png'))]

    def _load_preview_dynamic_words(self):
        """Load dynamic preview words from signs_directory/videos"""
        video_dir = os.path.join(self.preview_signs_dir, "videos")
        return [os.path.splitext(f)[0] for f in os.listdir(video_dir)
                if f.lower().endswith('.mp4')]

    ########################
    # GUI Setup Methods    #
    ########################
    
    def _setup_gui(self):
        """Initialize all GUI components"""
        # Create main layout frames
        self._create_main_frames()
        # Create preview areas
        self._create_preview_areas()
        # Create control panel
        self._create_control_panel()
        # Create video playback elements
        self._create_playback_elements()

    def _create_main_frames(self):
        """Create and configure main layout frames"""
        self.left_frame = ttk.Frame(self.root)
        self.right_frame = ttk.Frame(self.root)
        self.control_frame = ttk.Frame(self.root)
        
        self.left_frame.grid(row=0, column=0, padx=10, pady=10)
        self.right_frame.grid(row=0, column=1, padx=10, pady=10)
        self.control_frame.grid(row=1, column=0, columnspan=2, pady=10)

    def _create_preview_areas(self):
        """Create camera and sign preview areas"""
        # Camera preview
        self.camera_label = ttk.Label(self.left_frame)
        self.camera_label.pack()

        # Sign preview
        self.sign_preview = ttk.Label(self.right_frame)
        self.sign_preview.pack()
        self.sign_name_label = ttk.Label(self.right_frame, text="")
        self.sign_name_label.pack()

    def _create_control_panel(self):
        """Create all control panel elements"""
        # User input fields
        self._create_input_fields()
        # Control buttons
        self._create_control_buttons()
        # Progress tracking
        self._create_progress_tracking()

    def _create_input_fields(self):
        """Create user input fields"""
        # Username dropdown
        ttk.Label(self.control_frame, text="Username:").pack(side=tk.LEFT, padx=5)
        self.username_combobox = ttk.Combobox(
            self.control_frame, 
            textvariable=self.username,
            values=["Nour", "Mostafa"]
        )
        self.username_combobox.pack(side=tk.LEFT, padx=5)
        # Ensure user selects a username by setting a default:
        self.username_combobox.bind("<<ComboboxSelected>>", lambda e: print(f"Username selected: {self.username.get()}"))
        
        # Delay settings
        ttk.Label(self.control_frame, text="Video Delay (s):").pack(side=tk.LEFT, padx=5)
        ttk.Entry(self.control_frame, textvariable=self.video_delay, width=5).pack(side=tk.LEFT, padx=5)

    def _create_control_buttons(self):
        """Create control buttons"""
        # Main control buttons
        self.record_btn = ttk.Button(self.control_frame, text="Start Recording", 
                                   command=self._toggle_recording)
        self.test_btn = ttk.Button(self.control_frame, text="Test Recording",
                                  command=self._test_recording)
        self.reset_btn = ttk.Button(self.control_frame, text="Reset",
                                   command=self._reset_recording)
        self.done_btn = ttk.Button(self.control_frame, text="Done",
                                  command=self._handle_done, state='disabled')
        
        # Pack buttons
        for btn in [self.record_btn, self.test_btn, self.reset_btn, self.done_btn]:
            btn.pack(side=tk.LEFT, padx=5)

    def _create_progress_tracking(self):
        """Create progress tracking elements"""
        self.progress_frame = ttk.Frame(self.control_frame)
        self.progress_frame.pack(side=tk.LEFT, padx=5)
        
        self.progress_label = ttk.Label(self.progress_frame, text="Progress: 0/0")
        self.progress_label.pack(side=tk.LEFT)

    def _create_playback_elements(self):
        """Create video playback control elements"""
        self.playback_frame = ttk.Frame(self.root)
        self.video_slider = ttk.Scale(self.playback_frame, from_=0, to=100, orient=tk.HORIZONTAL)
        self.timestamp_label = ttk.Label(self.playback_frame, text="0:00 / 0:00")

    #############################
    # Preview Handling Methods  #
    #############################
    
    def _setup_preview(self):
        """Initialize preview systems"""
        self._update_sign_preview()
        self._update_camera()
        
    def _update_camera(self):
        """Update camera preview and handle recording"""
        try:
            ret, frame = self.cap.read()
            if ret:
                self.current_frame = self.processFrame(frame)
                
                # Display frame with consistent sizing
                frame_rgb = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2RGB)
                resized_frame = self._resize_with_aspect_ratio(frame_rgb, self.preview_size)
                img = Image.fromarray(resized_frame)
                imgtk = ImageTk.PhotoImage(image=img)
                self.camera_label.imgtk = imgtk
                self.camera_label.configure(image=imgtk)
                
                # Handle recording states
                if self.is_recording and self.current_sign_index < len(self.static_words):
                    current_time = time.time() * 1000
                    if current_time - self.last_capture_time >= self.capture_interval:
                        self._capture_image()
                        self.last_capture_time = current_time
                elif self.recording_in_progress and self.current_recording:
                    self.current_recording.write(self.current_frame)
                
            self.root.after(10, self._update_camera)
        except Exception as e:
            messagebox.showerror("Error", f"Camera error: {str(e)}")
            self._cleanup()

    ################################
    # Recording Control Methods    #
    ################################

    def _toggle_recording(self):
        """Handle recording start/stop"""
        if not self.username.get():
            messagebox.showerror("Error", "Please select a username")
            return
            
        try:
            if not self.is_recording:
                self._start_recording()
            else:
                self._pause_recording()
        except Exception as e:
            messagebox.showerror("Error", f"Recording error: {str(e)}")
            self._cleanup()

    def _start_recording(self):
        """Initialize and start recording session"""
        self.is_recording = True
        self.recording_in_progress = True
        self.record_btn.configure(text="Pause Recording")
        self.test_btn.configure(state='disabled')
        self.reset_btn.configure(state='disabled')
        
        if self.current_sign_index < len(self.static_words):
            self._start_image_session()
        else:
            self._start_video_session()

    def _pause_recording(self):
        """Pause current recording session"""
        self.is_recording = False
        self.recording_in_progress = False
        self.record_btn.configure(text="Resume Recording")
        
    def _stop_recording(self):
        """Stop and cleanup current recording session"""
        self.is_recording = False
        self.recording_in_progress = False
        self.record_btn.configure(text="Start Recording")
        self.test_btn.configure(state='normal')
        self.reset_btn.configure(state='normal')
        
        if self.current_recording:
            self.current_recording.release()
            self.current_recording = None

    #############################
    # Session Control Methods  #
    #############################

    def _start_image_session(self):
        """Initialize image recording session"""
        self.total_count = self.images_per_sign
        self.recorded_count = 0
        self._ensure_directories()
        self.last_capture_time = 0

    def _start_video_session(self):
        """Initialize video recording session"""
        self.total_count = self.videos_per_sign
        self.recorded_count = 0
        self._ensure_directories()
        self._start_video_recording_with_countdown()

    def _capture_image(self):
        """Capture and save a single image"""
        if self.recorded_count >= self.total_count:
            self._handle_recording_complete()
            return
            
        try:
            word = self.static_words[self.current_sign_index]
            path = os.path.join(self.image_dir, word, self.username.get(), 
                              f"image_{self.recorded_count}.jpg")
            cv2.imwrite(path, self.current_frame)
            self.recorded_count += 1
            self._update_progress()
            
            if self.recorded_count >= self.total_count:
                self._handle_recording_complete()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to capture image: {str(e)}")
            self._cleanup()

    ############################
    # Test Recording Methods  #
    ############################

    def _test_recording(self):
        """Initialize test recording session"""
        self.is_test_recording = True
        self.test_btn.configure(state='disabled')
        self.record_btn.configure(state='disabled')
        
        if not os.path.exists('temp'):
            os.makedirs('temp')
        
        self.test_video_path = os.path.join('temp', 'test_recording.mp4')
        self._start_countdown(int(self.video_delay.get()), self._start_test_recording)

    def _start_test_recording(self):
        """Start test video recording"""
        self.current_recording = cv2.VideoWriter(
            self.test_video_path,
            cv2.VideoWriter_fourcc(*'mp4v'),
            self.fps,
            (int(self.cap.get(3)), int(self.cap.get(4)))
        )
        self.progress_label.configure(text="Recording test video...")
        self.recording_timer = self.root.after(3000, self._stop_test_recording)

    ################################
    # Video Handling Methods       #
    ################################

    def _start_video_recording_with_countdown(self):
        """Start video recording with countdown timer"""
        self._start_countdown(int(self.video_delay.get()), self._start_video_recording)

    def _start_countdown(self, seconds, callback):
        """Handle countdown before recording"""
        if seconds > 0:
            self.progress_label.configure(text=f"Starting in {seconds}...")
            self.root.after(1000, lambda: self._start_countdown(seconds - 1, callback))
        else:
            callback()

    def _start_video_recording(self):
        """Initialize and start video recording"""
        word = self.dynamic_words[self.current_sign_index - len(self.static_words)]
        path = os.path.join(self.video_dir, word, self.username.get(), 
                           f"video_{self.recorded_count}.mp4")
        
        self.current_recording = cv2.VideoWriter(
            path,
            cv2.VideoWriter_fourcc(*'mp4v'),
            self.fps,
            self.preview_size  # Use consistent size
        )
        self.recording_in_progress = True

    ################################
    # Playback Control Methods     #
    ################################

    def _show_test_playback(self):
        """Display test recording playback controls"""
        self.playback_frame.grid(row=2, column=0, columnspan=2, pady=10)
        self.video_slider.pack(fill=tk.X, padx=10)
        self.timestamp_label.pack()
        self.done_btn.configure(state='normal')
        
        try:
            # Play the test video with consistent size
            player = tkvideo(self.test_video_path, 
                           self.sign_preview,
                           loop=1, 
                           size=self.preview_size,
                           keepratio=True)
            player.play()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to play test video: {str(e)}")

    def _handle_done(self):
        """Clean up after test playback"""
        self.playback_frame.grid_remove()
        self.test_btn.configure(state='normal')
        self.record_btn.configure(state='normal')
        self.done_btn.configure(state='disabled')
        self.is_test_recording = False
        
        if os.path.exists(self.test_video_path):
            try:
                os.remove(self.test_video_path)
            except Exception as e:
                print(f"Warning: Failed to delete test video: {str(e)}")

    ################################
    # Utility Methods             #
    ################################

    def _resize_with_aspect_ratio(self, image, target_size):
        """Resize image maintaining aspect ratio and add padding"""
        height, width = image.shape[:2]
        target_width, target_height = target_size
        
        # Calculate aspect ratios
        aspect = width / height
        target_aspect = target_width / target_height
        
        if aspect > target_aspect:
            new_width = target_width
            new_height = int(target_width / aspect)
        else:
            new_height = target_height
            new_width = int(target_height * aspect)
            
        # Create black background
        result = np.zeros((target_height, target_width, 3), dtype=np.uint8)
        
        # Center the resized image
        y_offset = (target_height - new_height) // 2
        x_offset = (target_width - new_width) // 2
        
        # Resize and place image
        resized = cv2.resize(image, (new_width, new_height))
        result[y_offset:y_offset+new_height, 
               x_offset:x_offset+new_width] = resized
        
        return result

    def _update_progress(self):
        """Update progress display"""
        self.progress_label.configure(
            text=f"Progress: {self.recorded_count}/{self.total_count}"
        )

    def _handle_recording_complete(self):
        """Handle completion of recording session"""
        self.is_recording = False
        self.recording_in_progress = False
        self.record_btn.configure(text="Start Recording")
        self._show_confirmation_popup()

    def _show_confirmation_popup(self):
        """Show confirmation dialog for recording completion"""
        result = messagebox.askyesno(
            "Confirmation",
            "Was the recording successful?"
        )
        if result:
            self.current_sign_index += 1
            if self.current_sign_index >= len(self.static_words) + len(self.dynamic_words):
                self.current_sign_index = 0
            self._update_sign_preview()
            self._update_progress()
        else:
            self._reset_recording()

    def _reset_recording(self):
        """Reset current recording session and clean up files"""
        # Stop any ongoing recording
        if self.is_recording:
            self._stop_recording()
            
        try:
            # Reset counters
            self.recorded_count = 0
            self.last_capture_time = 0
            
            # Delete existing files for current sign
            word = (self.static_words[self.current_sign_index] 
                   if self.current_sign_index < len(self.static_words)
                   else self.dynamic_words[self.current_sign_index - len(self.static_words)])
            
            directory = os.path.join(
                self.image_dir if self.current_sign_index < len(self.static_words) 
                else self.video_dir,
                word,
                self.username.get()
            )
            
            # Delete all files in the directory
            if os.path.exists(directory):
                for filename in os.listdir(directory):
                    file_path = os.path.join(directory, filename)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
            
            # Update UI
            self._update_progress()
            self._update_sign_preview()
            self.progress_label.configure(text=f"Progress: 0/{self.total_count}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to reset recording: {str(e)}")
            self._cleanup()

    ################################
    # Cleanup Methods             #
    ################################

    def _cleanup(self):
        """Clean up resources and reset state"""
        if self.current_recording:
            self.current_recording.release()
            self.current_recording = None
            
        if self.recording_timer:
            self.root.after_cancel(self.recording_timer)
            self.recording_timer = None
            
        # Reset states
        self.is_recording = False
        self.recording_in_progress = False
        self.current_frame = None
        self.last_capture_time = 0
        
        # Reset UI
        self.record_btn.configure(text="Start Recording", state='normal')
        self.test_btn.configure(state='normal')
        self.reset_btn.configure(state='normal')
        self.done_btn.configure(state='disabled')

    def _ensure_directories(self):
        """Ensure required directories exist"""
        try:
            word = (self.static_words[self.current_sign_index] 
                   if self.current_sign_index < len(self.static_words)
                   else self.dynamic_words[self.current_sign_index - len(self.static_words)])
            
            directory = os.path.join(
                self.image_dir if self.current_sign_index < len(self.static_words) 
                else self.video_dir,
                word,
                self.username.get()
            )
            os.makedirs(directory, exist_ok=True)
            return directory
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create directories: {str(e)}")
            raise

    def run(self):
        """Start the GUI application"""
        try:
            self.root.mainloop()
        finally:
            self._cleanup()
            if self.cap:
                self.cap.release()

    def _update_sign_preview(self):
        """
        Update the sign name label and optionally display a preview
        of the current static or dynamic sign.
        """
        # Determine current sign
        if self.current_sign_index < len(self.static_words):
            word = self.static_words[self.current_sign_index]
            # Attempt to load the first image for this sign
            image_dir = os.path.join(self.preview_signs_dir, "images", word)
            if os.path.exists(image_dir):
                images = [f for f in os.listdir(image_dir) if f.lower().endswith(('.jpg','.jpeg','.png'))]
                print(f"Debug: Looking in {image_dir}, found images: {images}")
                if images:
                    img_path = os.path.join(image_dir, images[0])
                    preview_img = cv2.imread(img_path)
                    if preview_img is None:
                        print(f"Warning: Failed to read image: {img_path}")
                    else:
                        # ...existing code...
                        preview_img_rgb = cv2.cvtColor(preview_img, cv2.COLOR_BGR2RGB)
                        resized_frame = self._resize_with_aspect_ratio(preview_img_rgb, self.preview_size)
                        preview_pil = Image.fromarray(resized_frame)
                        preview_imgtk = ImageTk.PhotoImage(preview_pil)
                        self.sign_preview.configure(image=preview_imgtk)
                        self.sign_preview.image = preview_imgtk
                else:
                    print("Debug: No images in directory.")
            else:
                print(f"Debug: Directory not found: {image_dir}")
        else:
            # For dynamic signs, no image preview yet
            pass
        
        # Update sign name label
        self.sign_name_label.configure(text=f"Current Sign: {word}")
        
        # If desired, load an image or video preview here
        # ...existing code...

if __name__ == "__main__":
    app = DatasetCollectorGUI()
    app.run()
