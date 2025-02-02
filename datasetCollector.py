import cv2
import mediapipe as mp
import os
import time

class DatasetCollector:
    def __init__(self, images_per_sign=200, videos_per_sign=100, fps=30):
        # Words that can be captured with static images, dool bas hatethom 3ashan agarab
        self.static_words = ["Hello", "Yes", "No", "I", "You", "He", "She", "We", "They"]
        # Words that require video sequences, nafs elkalam hatethom 3ashan agarab
        self.dynamic_words = ["Thank you"]
        
        # Configuration parameters
        self.images_per_sign = images_per_sign
        self.videos_per_sign = videos_per_sign
        self.fps = fps
        
        # Initialize MediaPipe solutions
        self.mp_pose = mp.solutions.pose
        self.mp_hands = mp.solutions.hands
        
        # Set up pose and hand tracking models
        self.pose = self.mp_pose.Pose(static_image_mode=False, min_detection_confidence=0.5)
        self.hands = self.mp_hands.Hands(static_image_mode=False, max_num_hands=2, min_detection_confidence=0.5)
        
        # Directory setup
        self.data_dir = "ArSL_Dataset"
        self.image_dir = os.path.join(self.data_dir, "Images")
        self.video_dir = os.path.join(self.data_dir, "Videos")
        self.username = "Nour" # Da hanghayaro b esm kol had fena
        
        # Create necessary folders
        self._create_directories()

        # Add recording state variables
        self.recording_in_progress = False
        self.current_frame = None
        self.current_recording = None

    def _create_directories(self):
        """Create all required folders if they don't exist"""
        # Create base directories
        os.makedirs(self.image_dir, exist_ok=True)
        os.makedirs(self.video_dir, exist_ok=True)
        
        # Create subdirectories for each static word
        for word in self.static_words:
            path = os.path.join(self.image_dir, word, self.username)
            os.makedirs(path, exist_ok=True)
        
        # Create subdirectories for each dynamic word
        for word in self.dynamic_words:
            path = os.path.join(self.video_dir, word, self.username)
            os.makedirs(path, exist_ok=True)

    def processFrame(self, frame):
        """
        Process frame to detect pose and hands, draw landmarks, 
        and return enhanced frame with visualizations
        """
        # Mirror the frame for natural interaction
        frame = cv2.flip(frame, 1)
        
        # Convert to RGB for MediaPipe processing
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Detect and draw pose landmarks
        pose_results = self.pose.process(frame_rgb)
        if pose_results.pose_landmarks:
            mp.solutions.drawing_utils.draw_landmarks(
                frame, pose_results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS)
        
        # Detect and draw hand landmarks
        hand_results = self.hands.process(frame_rgb)
        if hand_results.multi_hand_landmarks:
            for landmarks in hand_results.multi_hand_landmarks:
                mp.solutions.drawing_utils.draw_landmarks(
                    frame, landmarks, self.mp_hands.HAND_CONNECTIONS)
        
        return frame

    def collect_images(self):
        """Capture static images for sign language gestures"""
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Error: Could not open camera.")
            return
        
        # Collect images for each static word
        for word in self.static_words:
            word_dir = os.path.join(self.image_dir, word, self.username)
            print(f"Press 's' to save images for {word}. Press 'q' to quit.")
            image_count = 0
            
            while image_count < self.images_per_sign:
                ret, frame = cap.read()
                if not ret:
                    continue

                # Use processFrame for landmark detection and drawing
                enhanced_frame = self.processFrame(frame)

                # Display count and instructions
                cv2.putText(enhanced_frame, f"{word}: {image_count}/{self.images_per_sign}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.imshow("Image Collection", enhanced_frame)
                
                # Handle key presses, press 's' to save image and press 'q' to quit
                key = cv2.waitKey(1)
                if key == ord('s'):
                    img_path = os.path.join(word_dir, f"Image_{image_count}.jpg")
                    cv2.imwrite(img_path, enhanced_frame)  # Modified: Save enhanced frame
                    print(f"Saved: {img_path}")
                    image_count += 1
                elif key == ord('q'):
                    cap.release()
                    cv2.destroyAllWindows()
                    return

        cap.release()
        cv2.destroyAllWindows()

    def collect_videos(self):
        """Record video sequences for dynamic gestures"""
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Error: Could not open camera.")
            return
        
        # Record videos for each dynamic word
        for word in self.dynamic_words:
            word_dir = os.path.join(self.video_dir, word, self.username)
            video_count = 0
            
            while video_count < self.videos_per_sign:
                print(f"Press 'r' to start recording {word} video {video_count+1}. Press 's' to stop.")
                recording = False
                out = None  # Video writer initialized only when recording starts
                
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break

                    # Use processFrame for landmark detection and drawing
                    enhanced_frame = self.processFrame(frame)

                    # Display recording status
                    status_text = f"Recording {word}: {video_count}/{self.videos_per_sign}" if recording else "Press 'r' to start recording"
                    cv2.putText(enhanced_frame, status_text, (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    cv2.imshow("Video Recording", enhanced_frame)
                    
                    # Handle key presses, press 'r' to start recording, press 's' to save recorded video and press 'q' to quit
                    key = cv2.waitKey(1)
                    if key == ord('r') and not recording:
                        # Start recording
                        recording = True
                        # Initialize video writer only when recording starts
                        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                        video_path = os.path.join(word_dir, f"Video_{video_count}.mp4")
                        out = cv2.VideoWriter(video_path, fourcc, self.fps, 
                                            (int(cap.get(3)), int(cap.get(4))))
                        print("Recording started...")
                    elif key == ord('s') and recording:
                        # Stop recording
                        recording = False
                        out.release()
                        print(f"Saved: {video_path}")
                        video_count += 1
                        break
                    elif key == ord('q'):
                        if out is not None:
                            out.release()
                        cap.release()
                        cv2.destroyAllWindows()
                        return

                    # Write enhanced frame if recording
                    if recording:
                        out.write(enhanced_frame)  # Write enhanced frame

        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    collector = DatasetCollector()
    collector.collect_images()  # Collect static gestures
    collector.collect_videos()  # Collect dynamic gestures
