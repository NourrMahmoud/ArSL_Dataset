
###################################
####          OLD GUI         #####
###################################




# import tkinter as tk
# from tkinter import ttk, messagebox
# import cv2
# from PIL import Image, ImageTk
# import os
# import time
# import numpy as np
# from tkvideo import tkvideo
# from datasetCollector import DatasetCollector

# class DatasetCollectorGUI(DatasetCollector):
#     """
#     GUI application for collecting ArSL (Arabic Sign Language) dataset.
#     Inherits from DatasetCollector for base functionality.
#     """
    
#     def __init__(self):
#         # Initialize base collector
#         super().__init__()
        
#         #######################
#         # Initialize GUI vars #
#         #######################
#         self.root = tk.Tk()
#         self.root.title("ArSL Dataset Collector")
#         self.preview_size = (400, 400)  # Increase size for previews

#         # Set window size and center it
#         window_width, window_height = 1100, 800  # Adjust window size
#         screen_width = self.root.winfo_screenwidth()
#         screen_height = self.root.winfo_screenheight()
#         x = (screen_width - window_width) // 2
#         y = (screen_height - window_height) // 2
#         self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")

#         # For testing: allow adjustment of images per sign
#         self.images_count = tk.StringVar(value=str(self.images_per_sign))
        
#         #########################
#         # Directory Management  #
#         #########################
#         self.preview_signs_dir = "signs_directory"
#         if not self._check_preview_directories():
#             messagebox.showerror("Error", f"Required preview directory '{self.preview_signs_dir}' not found!")
#             self.root.destroy()
#             return
            
#         # Load sign data
#         try:
#             self.static_words = self._load_preview_static_words()
#             self.dynamic_words = self._load_preview_dynamic_words()
#         except Exception as e:
#             messagebox.showerror("Error", f"Failed to load preview signs: {str(e)}")
#             self.root.destroy()
#             return

#         ############################
#         # State tracking variables #
#         ############################
#         # Recording states
#         self.is_recording = False
#         self.is_test_recording = False
#         self.recording_in_progress = False
        
#         # Counters and timing
#         self.current_sign_index = 0
#         self.recorded_count = 0
#         self.total_count = 0
#         self.last_capture_time = 0
#         self.capture_interval = 100  # ms between captures
        
#         # Camera and recording objects
#         self.cap = cv2.VideoCapture(0)
#         self.current_frame = None
#         self.current_recording = None
#         self.recording_timer = None
        
#         # User input variables
#         self.video_delay = tk.StringVar(value="3")
#         self.username = tk.StringVar(value="Nour")
        
#         # Test recording variables
#         self.is_test_playback = False
#         self.test_video_path = None
        
#         # Initialize video-related variables
#         self.video_player = None
#         self.is_video_playing = False
#         self.video_after_id = None  # For canceling video playback
#         self.current_video_frame = None
#         self.video_cap = None
#         self.test_video_cap = None  # Add this for test video playback
        
#         # Initialize GUI
#         self._setup_gui()
#         self._setup_preview()

#     ################################
#     # Directory Management Methods #
#     ################################
    
#     def _check_preview_directories(self):
#         """Verify preview folders exist under 'signs_directory'"""
#         required_dirs = [
#             self.preview_signs_dir,
#             os.path.join(self.preview_signs_dir, "images"),
#             os.path.join(self.preview_signs_dir, "videos")
#         ]
#         return all(os.path.exists(d) for d in required_dirs)

#     def _load_preview_static_words(self):
#         """Load static preview words from signs_directory/images"""
#         image_dir = os.path.join(self.preview_signs_dir, "images")
#         return [os.path.splitext(f)[0] for f in os.listdir(image_dir)
#                 if f.lower().endswith(('.jpg', '.jpeg', '.png'))]

#     def _load_preview_dynamic_words(self):
#         """Load dynamic preview words from signs_directory/videos"""
#         video_dir = os.path.join(self.preview_signs_dir, "videos")
#         return [os.path.splitext(f)[0] for f in os.listdir(video_dir)
#                 if f.lower().endswith('.mp4')]

#     ########################
#     # GUI Setup Methods    #
#     ########################
    
#     def _setup_gui(self):
#         """Initialize all GUI components"""
#         # Create main layout frames
#         self._create_main_frames()
#         # Create preview areas
#         self._create_preview_areas()
#         # Create control panel
#         self._create_control_panel()
#         # Create video playback elements
#         self._create_playback_elements()

#     def _create_main_frames(self):
#         """Create and configure main layout frames"""
#         self.left_frame = ttk.Frame(self.root)
#         self.right_frame = ttk.Frame(self.root)
#         self.control_frame = ttk.Frame(self.root)
        
#         self.left_frame.grid(row=0, column=0, padx=10, pady=10)
#         self.right_frame.grid(row=0, column=1, padx=10, pady=10)
#         self.control_frame.grid(row=1, column=0, columnspan=2, pady=10)

#     def _create_preview_areas(self):
#         """Create camera and sign preview areas"""
#         # Camera preview
#         self.camera_label = ttk.Label(self.left_frame)
#         self.camera_label.pack()

#         # Sign preview
#         self.sign_preview = ttk.Label(self.right_frame)
#         self.sign_preview.pack()
#         self.sign_name_label = ttk.Label(self.right_frame, text="")
#         self.sign_name_label.pack()

#         # Add play/stop button for video preview
#         self.play_stop_btn = ttk.Button(self.right_frame, text="Play Video", command=self._toggle_video_playback)
#         self.play_stop_btn.pack()

#     def _toggle_video_playback(self):
#         """Toggle video playback for the current sign"""
#         if self.is_video_playing:
#             self._stop_video()
#         else:
#             self._play_video()

#     def _play_video(self):
#         """Play video preview using OpenCV"""
#         if self.current_sign_index >= len(self.static_words):
#             word = self.dynamic_words[self.current_sign_index - len(self.static_words)]
#             video_path = os.path.join(self.preview_signs_dir, "videos", f"{word}.mp4")
            
#             if os.path.exists(video_path):
#                 self.video_cap = cv2.VideoCapture(video_path)
#                 self.is_video_playing = True
#                 self.play_stop_btn.configure(text="Stop Video")
#                 self._play_video_frame()

#     def _play_video_frame(self):
#         """Display next video frame"""
#         if self.is_video_playing and self.video_cap and self.video_cap.isOpened():
#             ret, frame = self.video_cap.read()
#             if ret:
#                 frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
#                 resized_frame = self._resize_with_aspect_ratio(frame_rgb, self.preview_size)
#                 img = Image.fromarray(resized_frame)
#                 imgtk = ImageTk.PhotoImage(image=img)
#                 self.sign_preview.imgtk = imgtk
#                 self.sign_preview.configure(image=imgtk)
#                 self.video_after_id = self.root.after(30, self._play_video_frame)  # ~30fps
#             else:
#                 # Video ended, restart
#                 self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
#                 self._play_video_frame()

#     def _stop_video(self):
#         """Stop video preview"""
#         self.is_video_playing = False
#         if self.video_after_id:
#             self.root.after_cancel(self.video_after_id)
#             self.video_after_id = None
#         if self.video_cap:
#             self.video_cap.release()
#             self.video_cap = None
#         self.play_stop_btn.configure(text="Play Video")

#     def _create_control_panel(self):
#         """Create all control panel elements"""
#         # User input fields
#         self._create_input_fields()
#         # Control buttons
#         self._create_control_buttons()
#         # Progress tracking
#         self._create_progress_tracking()

#     def _create_input_fields(self):
#         """Create user input fields"""
#         # Username dropdown
#         ttk.Label(self.control_frame, text="Username:").pack(side=tk.LEFT, padx=5)
#         self.username_combobox = ttk.Combobox(
#             self.control_frame, 
#             textvariable=self.username,
#             values=["Nour", "Mostafa"]
#         )
#         self.username_combobox.pack(side=tk.LEFT, padx=5)
#         # Ensure user selects a username by setting a default:
#         self.username_combobox.bind("<<ComboboxSelected>>", lambda e: print(f"Username selected: {self.username.get()}"))
        
#         # Delay settings
#         ttk.Label(self.control_frame, text="Video Delay (s):").pack(side=tk.LEFT, padx=5)
#         ttk.Entry(self.control_frame, textvariable=self.video_delay, width=5).pack(side=tk.LEFT, padx=5)

#         # Images per Sign settings
#         ttk.Label(self.control_frame, text="Images per Sign:").pack(side=tk.LEFT, padx=5)
#         ttk.Entry(self.control_frame, textvariable=self.images_count, width=5).pack(side=tk.LEFT, padx=5)

#     def _create_control_buttons(self):
#         """Create control buttons"""
#         # Main control buttons
#         self.record_btn = ttk.Button(self.control_frame, text="Start Recording", 
#                                    command=self._toggle_recording)
#         self.test_btn = ttk.Button(self.control_frame, text="Test Recording",
#                                   command=self._test_recording)
#         self.reset_btn = ttk.Button(self.control_frame, text="Reset",
#                                    command=self._reset_recording)
#         self.done_btn = ttk.Button(self.control_frame, text="Done",
#                                   command=self._handle_done, state='disabled')
        
#         # Pack buttons
#         for btn in [self.record_btn, self.test_btn, self.reset_btn, self.done_btn]:
#             btn.pack(side=tk.LEFT, padx=5)

#     def _create_progress_tracking(self):
#         """Create progress tracking elements"""
#         self.progress_frame = ttk.Frame(self.control_frame)
#         self.progress_frame.pack(side=tk.LEFT, padx=5)
        
#         self.progress_label = ttk.Label(self.progress_frame, text="Progress: 0/0")
#         self.progress_label.pack(side=tk.LEFT)

#     def _create_playback_elements(self):
#         """Create video playback control elements"""
#         self.playback_frame = ttk.Frame(self.root)
#         self.video_slider = ttk.Scale(self.playback_frame, from_=0, to=100, orient=tk.HORIZONTAL)
#         self.timestamp_label = ttk.Label(self.playback_frame, text="0:00 / 0:00")

#     #############################
#     # Preview Handling Methods  #
#     #############################
    
#     def _setup_preview(self):
#         """Initialize preview systems"""
#         self._update_sign_preview()
#         self._update_camera()
        
#     def _update_camera(self):
#         """Update camera preview and handle recording"""
#         try:
#             ret, frame = self.cap.read()
#             if ret:
#                 self.current_frame = self.processFrame(frame)
                
#                 # Display frame with consistent sizing
#                 frame_rgb = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2RGB)
#                 resized_frame = self._resize_with_aspect_ratio(frame_rgb, self.preview_size)
#                 img = Image.fromarray(resized_frame)
#                 imgtk = ImageTk.PhotoImage(image=img)
#                 self.camera_label.imgtk = imgtk
#                 self.camera_label.configure(image=imgtk)
                
#                 # Handle recording states
#                 if self.is_recording and self.current_sign_index < len(self.static_words):
#                     current_time = time.time() * 1000
#                     if current_time - self.last_capture_time >= self.capture_interval:
#                         self._capture_image()
#                         self.last_capture_time = current_time
#                 elif self.recording_in_progress and self.current_recording:
#                     self.current_recording.write(self.current_frame)
                
#             self.root.after(10, self._update_camera)
#         except Exception as e:
#             messagebox.showerror("Error", f"Camera error: {str(e)}")
#             self._cleanup()

#     ################################
#     # Recording Control Methods    #
#     ################################

#     def _toggle_recording(self):
#         """Handle recording start/stop"""
#         if not self.username.get():
#             messagebox.showerror("Error", "Please select a username")
#             return
            
#         try:
#             if not self.is_recording:
#                 self._start_recording()
#             else:
#                 self._pause_recording()
#         except Exception as e:
#             messagebox.showerror("Error", f"Recording error: {str(e)}")
#             self._cleanup()

#     def _start_recording(self):
#         """Initialize and start recording session"""
#         self.is_recording = True
#         self.recording_in_progress = True
#         self.record_btn.configure(text="Pause Recording")
#         self.test_btn.configure(state='disabled')
#         self.reset_btn.configure(state='disabled')
        
#         if self.current_sign_index < len(self.static_words):
#             self._start_image_session()
#         else:
#             self._start_video_session()

#     def _pause_recording(self):
#         """Pause current recording session"""
#         self.is_recording = False
#         self.recording_in_progress = False
#         self.record_btn.configure(text="Resume Recording")
        
#     def _stop_recording(self):
#         """Stop and cleanup current recording session"""
#         self.is_recording = False
#         self.recording_in_progress = False
#         self.record_btn.configure(text="Start Recording")
#         self.test_btn.configure(state='normal')
#         self.reset_btn.configure(state='normal')
        
#         if self.current_recording:
#             self.current_recording.release()
#             self.current_recording = None

#     #############################
#     # Session Control Methods  #
#     #############################

#     def _start_image_session(self):
#         """Initialize image recording session"""
#         self.total_count = int(self.images_count.get())
#         self.recorded_count = 0
#         self._ensure_directories()
#         self.last_capture_time = 0

#     def _start_video_session(self):
#         """Initialize video recording session"""
#         self.total_count = self.videos_per_sign
#         self.recorded_count = 0
#         self._ensure_directories()
#         self._start_video_recording_with_countdown()

#     def _capture_image(self):
#         """Capture and save a single image"""
#         if self.recorded_count >= self.total_count:
#             self._handle_recording_complete()
#             return
            
#         try:
#             word = self.static_words[self.current_sign_index]
#             path = os.path.join(self.image_dir, word, self.username.get(), 
#                               f"image_{self.recorded_count}.jpg")
#             cv2.imwrite(path, self.current_frame)
#             self.recorded_count += 1
#             self._update_progress()
            
#             if self.recorded_count >= self.total_count:
#                 self._handle_recording_complete()
#         except Exception as e:
#             messagebox.showerror("Error", f"Failed to capture image: {str(e)}")
#             self._cleanup()

#     ############################
#     # Test Recording Methods  #
#     ############################

#     def _test_recording(self):
#         """Initialize test recording session"""
#         if self.current_sign_index < len(self.static_words):
#             messagebox.showerror("Error", "Test recording is only available for dynamic signs.")
#             return

#         self.is_test_recording = True
#         self.test_btn.configure(text="Stop Test", command=self._stop_test_recording)
#         self.record_btn.configure(state='disabled')
#         self.reset_btn.configure(state='disabled')
        
#         if not os.path.exists('temp'):
#             os.makedirs('temp')
        
#         self.test_video_path = os.path.join('temp', 'test_recording.mp4')
#         self._start_countdown(int(self.video_delay.get()), self._start_test_recording)

#     def _start_test_recording(self):
#         """Start test video recording"""
#         # Use more compatible codec and format
#         fourcc = cv2.VideoWriter_fourcc(*'XVID')
#         self.test_video_path = os.path.join('temp', 'test_recording.avi')
        
#         self.current_recording = cv2.VideoWriter(
#             self.test_video_path,
#             fourcc,
#             self.fps,
#             (int(self.cap.get(3)), int(self.cap.get(4)))
#         )
#         if not self.current_recording.isOpened():
#             raise Exception("Failed to initialize video writer")
#         self.progress_label.configure(text="Recording test video...")

#     def _stop_test_recording(self):
#         """Stop test video recording and show playback"""
#         if self.current_recording:
#             self.current_recording.release()
#             self.current_recording = None
        
#         self.test_btn.configure(text="Test Recording", command=self._test_recording)
#         self.record_btn.configure(state='normal')
#         self.reset_btn.configure(state='normal')
#         self.progress_label.configure(text="Test recording complete.")
        
#         # Show test video playback
#         self._show_test_playback()

#     ################################
#     # Video Handling Methods       #
#     ################################

#     def _start_video_recording_with_countdown(self):
#         """Start video recording with countdown timer"""
#         self._start_countdown(int(self.video_delay.get()), self._start_video_recording)

#     def _start_countdown(self, seconds, callback):
#         """Handle countdown before recording"""
#         if seconds > 0:
#             self.progress_label.configure(text=f"Starting in {seconds}...")
#             self.root.after(1000, lambda: self._start_countdown(seconds - 1, callback))
#         else:
#             self.progress_label.configure(text="Recording...")
#             callback()

#     def _start_video_recording(self):
#         """Initialize and start video recording"""
#         word = self.dynamic_words[self.current_sign_index - len(self.static_words)]
#         path = os.path.join(self.video_dir, word, self.username.get(), 
#                            f"video_{self.recorded_count}.avi")  # Change to .avi
        
#         # Use XVID codec for better compatibility
#         fourcc = cv2.VideoWriter_fourcc(*'XVID')
        
#         # Get actual frame size from camera
#         width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
#         height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
#         self.current_recording = cv2.VideoWriter(
#             path,
#             fourcc,
#             self.fps,
#             (width, height)  # Use actual camera resolution
#         )
        
#         if not self.current_recording.isOpened():
#             raise Exception("Failed to initialize video writer")
            
#         self.recording_in_progress = True
#         self.progress_label.configure(text="Recording...")

#     ################################
#     # Playback Control Methods     #
#     ################################

#     def _show_test_playback(self):
#         """Display test recording playback controls"""
#         try:
#             if not os.path.exists(self.test_video_path):
#                 raise Exception("Test video file not found")
                
#             self.playback_frame.grid(row=2, column=0, columnspan=2, pady=10)
#             self.video_slider.pack(fill=tk.X, padx=10)
#             self.timestamp_label.pack()
#             self.done_btn.configure(state='normal')
            
#             # Initialize video capture for test playback
#             self.test_video_cap = cv2.VideoCapture(self.test_video_path)
#             if not self.test_video_cap.isOpened():
#                 raise Exception("Could not open test video file")
                
#             # Get video info for the slider
#             total_frames = int(self.test_video_cap.get(cv2.CAP_PROP_FRAME_COUNT))
#             self.video_slider.configure(to=total_frames)
#             self.video_slider.set(0)
            
#             # Start test video playback
#             self.is_video_playing = True
#             # Use after() to start playback instead of direct call
#             self.video_after_id = self.root.after(30, self._play_test_video_frame)
            
#         except Exception as e:
#             messagebox.showerror("Error", f"Failed to play test video: {str(e)}")
#             self._cleanup_test_playback()

#     def _on_video_slider_change(self, value):
#         """Handle video slider position change"""
#         if self.test_video_cap:
#             frame_no = int(float(value))
#             self.test_video_cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)

#     def _play_test_video_frame(self):
#         """Display next frame of test video"""
#         if not (self.is_video_playing and self.test_video_cap and self.test_video_cap.isOpened()):
#             return
            
#         ret, frame = self.test_video_cap.read()
#         if ret:
#             # Process and display frame
#             frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
#             resized_frame = self._resize_with_aspect_ratio(frame_rgb, self.preview_size)
#             img = Image.fromarray(resized_frame)
#             imgtk = ImageTk.PhotoImage(image=img)
#             self.sign_preview.imgtk = imgtk
#             self.sign_preview.configure(image=imgtk)
            
#             # Update slider position
#             current_frame = int(self.test_video_cap.get(cv2.CAP_PROP_POS_FRAMES))
#             self.video_slider.set(current_frame)
            
#             # Schedule next frame
#             self.video_after_id = self.root.after(30, self._play_test_video_frame)
#         else:
#             # Video ended, restart without recursive call
#             self.test_video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
#             # Schedule next frame instead of direct call
#             self.video_after_id = self.root.after(30, self._play_test_video_frame)

#     def _cleanup_test_playback(self):
#         """Clean up test video playback resources"""
#         if self.video_after_id:
#             self.root.after_cancel(self.video_after_id)
#             self.video_after_id = None
        
#         if self.test_video_cap:
#             self.test_video_cap.release()
#             self.test_video_cap = None

#     def _handle_done(self):
#         """Clean up after test playback"""
#         self._cleanup_test_playback()
#         self.playback_frame.grid_remove()
#         self.test_btn.configure(state='normal', text="Test Recording", command=self._test_recording)
#         self.record_btn.configure(state='normal')
#         self.done_btn.configure(state='disabled')
#         self.is_test_recording = False
        
#         if os.path.exists(self.test_video_path):
#             try:
#                 os.remove(self.test_video_path)
#             except Exception as e:
#                 print(f"Warning: Failed to delete test video: {str(e)}")

#     ################################
#     # Utility Methods             #
#     ################################

#     def _resize_with_aspect_ratio(self, image, target_size):
#         """Resize image maintaining aspect ratio and add padding"""
#         height, width = image.shape[:2]
#         target_width, target_height = target_size
        
#         # Calculate aspect ratios
#         aspect = width / height
#         target_aspect = target_width / target_height
        
#         if aspect > target_aspect:
#             new_width = target_width
#             new_height = int(target_width / aspect)
#         else:
#             new_height = target_height
#             new_width = int(target_height * aspect)
            
#         # Create black background
#         result = np.zeros((target_height, target_width, 3), dtype=np.uint8)
        
#         # Center the resized image
#         y_offset = (target_height - new_height) // 2
#         x_offset = (target_width - new_width) // 2
        
#         # Resize and place image
#         resized = cv2.resize(image, (new_width, new_height))
#         result[y_offset:y_offset+new_height, 
#                x_offset:x_offset+new_width] = resized
        
#         return result

#     def _update_progress(self):
#         """Update progress display"""
#         self.progress_label.configure(
#             text=f"Progress: {self.recorded_count}/{self.total_count}"
#         )

#     def _handle_recording_complete(self):
#         """Handle completion of recording session"""
#         self.is_recording = False
#         self.recording_in_progress = False
#         self.record_btn.configure(text="Start Recording")
#         self._show_confirmation_popup()

#     def _show_confirmation_popup(self):
#         """Show confirmation dialog for recording completion"""
#         result = messagebox.askyesno(
#             "Confirmation",
#             "Was the recording successful?"
#         )
#         if result:
#             self.current_sign_index += 1
#             if self.current_sign_index >= len(self.static_words) + len(self.dynamic_words):
#                 self.current_sign_index = 0
#             self._update_sign_preview()  # Ensure preview is updated
#             self._update_progress()
#         else:
#             self._reset_recording()

#     def _reset_recording(self):
#         """Reset current recording session and clean up files"""
#         # Stop any ongoing recording
#         if self.is_recording:
#             self._stop_recording()
            
#         try:
#             # Reset counters
#             self.recorded_count = 0
#             self.last_capture_time = 0
            
#             # Delete existing files for current sign
#             word = (self.static_words[self.current_sign_index] 
#                    if self.current_sign_index < len(self.static_words)
#                    else self.dynamic_words[self.current_sign_index - len(self.static_words)])
            
#             directory = os.path.join(
#                 self.image_dir if self.current_sign_index < len(self.static_words) 
#                 else self.video_dir,
#                 word,
#                 self.username.get()
#             )
            
#             # Delete all files in the directory
#             if os.path.exists(directory):
#                 for filename in os.listdir(directory):
#                     file_path = os.path.join(directory, filename)
#                     if os.path.isfile(file_path):
#                         os.remove(file_path)
            
#             # Update UI
#             self._update_progress()
#             self._update_sign_preview()  # Ensure preview is updated
#             self.progress_label.configure(text=f"Progress: 0/{self.total_count}")
            
#         except Exception as e:
#             messagebox.showerror("Error", f"Failed to reset recording: {str(e)}")
#             self._cleanup()

#     ################################
#     # Cleanup Methods             #
#     ################################

#     def _cleanup(self):
#         """Clean up resources and reset state"""
#         if self.current_recording:
#             self.current_recording.release()
#             self.current_recording = None
            
#         if self.recording_timer:
#             self.root.after_cancel(self.recording_timer)
#             self.recording_timer = None
            
#         # Reset states
#         self.is_recording = False
#         self.recording_in_progress = False
#         self.current_frame = None
#         self.last_capture_time = 0
        
#         # Reset UI
#         self.record_btn.configure(text="Start Recording", state='normal')
#         self.test_btn.configure(state='normal')
#         self.reset_btn.configure(state='normal')
#         self.done_btn.configure(state='disabled')
        
#         # Add video cleanup
#         self._stop_video()
        
#         # Add test video cleanup
#         self._cleanup_test_playback()

#     def _ensure_directories(self):
#         """Ensure required directories exist"""
#         try:
#             word = (self.static_words[self.current_sign_index] 
#                    if self.current_sign_index < len(self.static_words)
#                    else self.dynamic_words[self.current_sign_index - len(self.static_words)])
            
#             directory = os.path.join(
#                 self.image_dir if self.current_sign_index < len(self.static_words) 
#                 else self.video_dir,
#                 word,
#                 self.username.get()
#             )
#             os.makedirs(directory, exist_ok=True)
#             return directory
#         except Exception as e:
#             messagebox.showerror("Error", f"Failed to create directories: {str(e)}")
#             raise

#     def run(self):
#         """Start the GUI application"""
#         try:
#             self.root.mainloop()
#         finally:
#             self._cleanup()
#             if self.cap:
#                 self.cap.release()

#     def _update_sign_preview(self):
#         """
#         Update the sign name label and preview of the current static or dynamic sign.
#         """
#         # Clear previous preview
#         if self.video_cap:
#             self.video_cap.release()
#             self.video_cap = None
#         if self.video_after_id:
#             self.root.after_cancel(self.video_after_id)
#             self.video_after_id = None
#         self.is_video_playing = False
        
#         # Determine current sign
#         if self.current_sign_index < len(self.static_words):
#             word = self.static_words[self.current_sign_index]
#             # Load static image
#             image_path = os.path.join(self.preview_signs_dir, "images", f"{word}.jpg")
            
#             if os.path.exists(image_path):
#                 preview_img = cv2.imread(image_path)
#                 if preview_img is not None:
#                     preview_img_rgb = cv2.cvtColor(preview_img, cv2.COLOR_BGR2RGB)
#                     resized_frame = self._resize_with_aspect_ratio(preview_img_rgb, self.preview_size)
#                     preview_pil = Image.fromarray(resized_frame)
#                     preview_imgtk = ImageTk.PhotoImage(image=preview_pil)
#                     self.sign_preview.imgtk = preview_imgtk  # Keep a reference!
#                     self.sign_preview.configure(image=preview_imgtk)
#                 self.play_stop_btn.configure(state='disabled')
#                 self.test_btn.configure(state='disabled')
#         else:
#             # Handle dynamic sign (video)
#             word = self.dynamic_words[self.current_sign_index - len(self.static_words)]
#             video_path = os.path.join(self.preview_signs_dir, "videos", f"{word}.mp4")
            
#             if os.path.exists(video_path):
#                 # Show first frame of video
#                 cap = cv2.VideoCapture(video_path)
#                 ret, frame = cap.read()
#                 if ret:
#                     frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
#                     resized_frame = self._resize_with_aspect_ratio(frame_rgb, self.preview_size)
#                     preview_pil = Image.fromarray(resized_frame)
#                     preview_imgtk = ImageTk.PhotoImage(image=preview_pil)
#                     self.sign_preview.imgtk = preview_imgtk
#                     self.sign_preview.configure(image=preview_imgtk)
#                 cap.release()
                
#                 # Update controls for dynamic sign
#                 self.play_stop_btn.configure(state='normal', text="Play Video")
#                 self.test_btn.configure(state='normal')
#             else:
#                 self.play_stop_btn.configure(state='disabled')
#                 self.test_btn.configure(state='disabled')

#         # Update sign name label
#         self.sign_name_label.configure(text=f"Current Sign: {word}")

# if __name__ == "__main__":
#     app = DatasetCollectorGUI()
#     app.run()
