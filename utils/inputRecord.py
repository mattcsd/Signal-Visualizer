import time
import threading
import numpy as np
import soundfile as sf
import sounddevice as sd
from scipy.io.wavfile import write
from pathlib import Path
from PyQt5.QtWidgets import (QSpinBox, QApplication, QWidget, QDialog, QLabel, QPushButton, 
                            QVBoxLayout, QHBoxLayout, QMessageBox)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QFont
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.widgets import SpanSelector, Button

# Import ControlMenu at the top to avoid circular imports
try:
    from core.controlMenu import ControlMenu
    CONTROL_MENU_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import ControlMenu: {e}")
    CONTROL_MENU_AVAILABLE = False


class SoundDeviceRecordingThread(QThread):
    frames_ready = pyqtSignal(np.ndarray)
    recording_error = pyqtSignal(str)
    
    def __init__(self, fs, channels=1):
        super().__init__()
        self.fs = fs
        self.channels = channels
        self._is_recording = False
        self.stream = None
        
    def run(self):
        """Audio recording using sounddevice - much more reliable than PyAudio"""
        try:
            self._is_recording = True
            self.frames = []
            
            def callback(indata, frames, time, status):
                if status:
                    print(f"Audio input status: {status}")
                if self._is_recording:
                    # Make a copy of the data to avoid reference issues
                    data_copy = indata.copy()
                    self.frames_ready.emit(data_copy)
            
            # Use sounddevice which is more reliable
            with sd.InputStream(samplerate=self.fs, 
                              channels=self.channels,
                              callback=callback,
                              blocksize=1024,
                              dtype='float32'):
                print("Recording started with sounddevice")
                while self._is_recording:
                    # Small sleep to prevent busy waiting
                    self.msleep(10)
                    
        except Exception as e:
            error_msg = f"Recording error: {str(e)}"
            print(error_msg)
            self.recording_error.emit(error_msg)
            
    def stop(self):
        """Stop recording safely"""
        self._is_recording = False

class Record(QWidget):
    def __init__(self, master, controller):
        super().__init__(master)
        self.controller = controller
        self.master = master
        self.isrecording = False
        self.fs = 44100
        self.selectedAudio = np.empty(1)
        self.recording_start_time = 0
        self.frames = []
        self.control_windows = []
        
        self.setupUI()
        
    def setupUI(self):
        """Set up the user interface (same as before)"""
        self.setWindowTitle("Audio Recorder")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        control_row = QHBoxLayout()
        control_row.setContentsMargins(0, 0, 0, 0)
        control_row.setSpacing(10)
        
        self.record_button = QPushButton("⏺ Record")
        self.record_button.setFont(QFont("Arial", 12, QFont.Bold))
        self.record_button.setStyleSheet("""
            QPushButton {
                background-color: #ff4444;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #ff6666;
            }
            QPushButton:disabled {
                background-color: #aa3333;
            }
        """)
        self.record_button.clicked.connect(self.start_recording)
        
        self.stop_button = QPushButton("⏹ Stop")
        self.stop_button.setFont(QFont("Arial", 12, QFont.Bold))
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #666666;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #888888;
            }
            QPushButton:disabled {
                background-color: #444444;
            }
        """)
        self.stop_button.clicked.connect(self.stop_recording)
        self.stop_button.setEnabled(False)
        
        self.time_label = QLabel("00:00")
        self.time_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setStyleSheet("min-width: 80px;")
        
        time_limit_layout = QHBoxLayout()
        time_limit_layout.setSpacing(5)
        time_limit_label = QLabel("Max:")
        time_limit_label.setFont(QFont("Arial", 10))
        self.time_spinbox = QSpinBox()
        self.time_spinbox.setRange(1, 600)
        self.time_spinbox.setValue(30)
        self.time_spinbox.setSuffix("s")
        self.time_spinbox.setFixedWidth(80)
        
        self.help_button = QPushButton("🛈 Help")
        self.help_button.setFont(QFont("Arial", 18))
        self.help_button.setFixedWidth(120)
        self.help_button.setFixedHeight(35)
        self.help_button.clicked.connect(lambda: self.controller.help.createHelpMenu(7))
        self.help_button.setStyleSheet("""
            QPushButton {
                background-color: #555555;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #777777;
            }
        """)
        
        self.load_button = QPushButton("Load to Controller")
        self.load_button.setFont(QFont("Arial", 15))
        self.load_button.setFixedHeight(35)
        self.load_button.setVisible(False)
        self.load_button.clicked.connect(self.load_to_controller)
        self.load_button.setStyleSheet("""
            QPushButton {
                background-color: #4477ff;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
                min-width: 150px;
            }
            QPushButton:hover {
                background-color: #6699ff;
            }
        """)
        
        control_row.addWidget(self.record_button)
        control_row.addWidget(self.stop_button)
        control_row.addWidget(self.time_label)
        control_row.addWidget(time_limit_label)
        control_row.addWidget(self.time_spinbox)
        control_row.addWidget(self.help_button)
        control_row.addWidget(self.load_button)
        control_row.addStretch()
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time_display)
        
        self.auto_stop_timer = QTimer(self)
        self.auto_stop_timer.setSingleShot(True)
        self.auto_stop_timer.timeout.connect(self.stop_recording)
        
        self.fig = Figure(figsize=(8, 4))
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvas(self.fig)
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        self.canvas.setVisible(False)
        self.toolbar.setVisible(False)
        
        main_layout.addLayout(control_row)
        main_layout.addWidget(self.toolbar)
        main_layout.addWidget(self.canvas)
        
        self.setLayout(main_layout)
    

    def get_writable_recording_dir(self):
        """Get platform-appropriate writable directory for recordings"""
        app_name = "YourAppName"  # Replace with your actual app name
        user_data_dir = Path(appdirs.user_data_dir(app_name))
        
        recording_dir = user_data_dir / "recordings"
        try:
            recording_dir.mkdir(parents=True, exist_ok=True)
            return recording_dir
        except (OSError, PermissionError) as e:
            print(f"Failed to create directory {recording_dir}: {e}")
            # Fallback to temp directory
            fallback = Path(tempfile.gettempdir()) / f"{app_name}_recordings"
            fallback.mkdir(parents=True, exist_ok=True)
            return fallback


    def check_microphone_permission(self):
        """Check microphone permission and trigger permission dialog if needed"""
        try:
            # First, try a simple test that should trigger the permission dialog
            print("Testing microphone access...")
            
            # Create a short test recording - this should trigger the permission dialog
            duration = 0.1  # seconds
            test_recording = sd.rec(int(duration * self.fs), 
                                  samplerate=self.fs, 
                                  channels=1, 
                                  blocking=True)
            
            # If we get here, we have permission
            print("Microphone access successful!")
            return True
            
        except sd.PortAudioError as e:
            print(f"Microphone access error: {e}")
            
            # Show specific instructions for macOS
            QMessageBox.critical(
                self, 
                "Microphone Access Required", 
                "Microphone access is required for recording.\n\n"
                "Please grant microphone permission in:\n"
                "System Preferences > Security & Privacy > Microphone\n\n"
                "Then restart the application and try again."
            )
            return False
        except Exception as e:
            print(f"Unexpected error checking microphone: {e}")
            return False


    def start_recording(self):
        """Start recording with sounddevice"""
        if not self.check_microphone_permission():
            return

        try:
            self.record_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.isrecording = True
            self.frames = []  # Reset frames
            self.recording_start_time = time.time()
            
            # Start timers
            self.timer.start(200)
            self.max_record_time = self.time_spinbox.value()
            self.auto_stop_timer.start(self.max_record_time * 1000)
            
            # Start recording thread with sounddevice
            self.recording_thread = SoundDeviceRecordingThread(self.fs)
            self.recording_thread.frames_ready.connect(self.handle_frames)
            self.recording_thread.recording_error.connect(self.handle_recording_error)
            self.recording_thread.start()
            
        except Exception as e:
            print(f"Error starting recording: {e}")
            self.handle_recording_error(str(e))

    def handle_frames(self, data):
        """Handle incoming audio frames - runs in main thread"""
        if self.isrecording:
            # Convert to int16 for consistency with original code
            data_int16 = (data * 32767).astype(np.int16)
            
            # Store as bytes in frames list
            self.frames.append(data_int16.tobytes())
            
            # Alternative: Store as arrays for more efficient concatenation later
            # if not hasattr(self, 'frame_arrays'):
            #     self.frame_arrays = []
            # self.frame_arrays.append(data_int16)


    def handle_recording_error(self, error_msg):
        """Handle recording errors"""
        print(f"Recording error: {error_msg}")
        QMessageBox.critical(self, "Recording Error", f"Recording failed:\n{error_msg}")
        self.stop_recording()

    def stop_recording(self):
        """Stop recording safely"""
        print("stop_recording called")
        if not self.isrecording:
            print("Not recording, returning")
            return
            
        print("Stopping recording...")
        self.isrecording = False
        
        # Update UI first
        self.record_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.timer.stop()
        self.auto_stop_timer.stop()
        
        # Stop recording thread safely
        if hasattr(self, 'recording_thread') and self.recording_thread:
            print("Stopping recording thread...")
            self.recording_thread.stop()
            if not self.recording_thread.wait(2000):  # 2 second timeout
                print("Warning: Recording thread didn't finish in time")
                self.recording_thread.terminate()
                self.recording_thread.wait()
            self.recording_thread = None
        
        print("Processing recording...")
        # Process recording in main thread
        QTimer.singleShot(100, self.process_recording)
        
    def update_time_display(self):
        """Update time display"""
        if self.isrecording:
            duration = time.time() - self.recording_start_time
            mins, secs = divmod(int(duration), 60)
            self.time_label.setText(f"{mins:02d}:{secs:02d}")

    def process_recording(self):
        """Process the recorded audio entirely in memory"""
        try:
            if not self.frames:
                print("No frames recorded")
                return
                
            # Convert frames to numpy array directly
            audio_data = b"".join(self.frames)
            rec_int = np.frombuffer(audio_data, dtype=np.int16)
            
            if len(rec_int) == 0:
                print("Empty recording")
                return
                
            duration = len(rec_int) / self.fs
            time_axis = np.linspace(0, duration, len(rec_int))
            
            # Convert int16 to float32 for processing (normalize to [-1, 1])
            rec_float = rec_int.astype(np.float32) / 32768.0
            
            # Store the audio data in memory instead of saving to file
            self.current_recording_float = rec_float
            self.current_recording_int = rec_int
            
            # Update plot
            self.ax.clear()
            self.ax.plot(time_axis, rec_int)
            self.ax.set(xlim=[0, duration], xlabel='Time (s)', ylabel='Amplitude', title='Recording')
            self.ax.axhline(y=0, color='black', linewidth=0.5, linestyle='--')
            self.ax.grid(True, linestyle=':', alpha=0.5)
            
            # Setup span selector
            self.setup_span_selector(time_axis, rec_float)
            
            # Show plot
            self.canvas.setVisible(True)
            self.toolbar.setVisible(True)
            self.canvas.draw()
            self.load_button.setVisible(True)
            
            print(f"Recording processed: {duration:.2f} seconds (in memory)")
            
        except Exception as e:
            print(f"Error processing recording: {e}")
            QMessageBox.critical(self, "Processing Error", f"Could not process recording:\n{str(e)}")


    def setup_span_selector(self, time_axis, audio):
        """Setup span selector for audio selection"""
        if hasattr(self, 'span'):
            try:
                self.span.disconnect_events()
            except:
                pass

        def on_select(xmin, xmax):
            if len(audio) <= 1:
                return
            idx_min = np.argmax(time_axis >= xmin)
            idx_max = np.argmax(time_axis >= xmax)
            self.selectedAudio = audio[idx_min:idx_max]
            # Play selected segment
            try:
                sd.play(self.selectedAudio, self.fs)
            except Exception as e:
                print(f"Error playing audio: {e}")

        self.span = SpanSelector(
            self.ax,
            on_select,
            'horizontal',
            useblit=True,
            interactive=True,
            drag_from_anywhere=True
        )

    def load_to_controller(self):
        """Load audio to controller from memory"""
        try:
            if not CONTROL_MENU_AVAILABLE:
                raise ImportError("ControlMenu is not available")
            
            if hasattr(self, 'selectedAudio') and len(self.selectedAudio) > 1:
                audio_to_load = self.selectedAudio
            else:
                # Use the in-memory recording instead of reading from file
                if hasattr(self, 'current_recording_float'):
                    audio_to_load = self.current_recording_float
                else:
                    raise ValueError("No recording available in memory")
            
            duration = len(audio_to_load) / self.fs
            title = f"Recording {time.strftime('%Y-%m-%d %H:%M')}"

            # Use the imported ControlMenu class
            control_window = ControlMenu(title, self.fs, audio_to_load, duration, self.controller)
            self.control_windows.append(control_window)

            def handle_close():
                if control_window in self.control_windows:
                    self.control_windows.remove(control_window)
                if hasattr(self.controller, 'update_windows_menu'):
                    self.controller.update_windows_menu()
            
            control_window.destroyed.connect(handle_close)
            
            if hasattr(self.controller, 'update_windows_menu'):
                self.controller.update_windows_menu()

            control_window.show()
            control_window.activateWindow()

        except Exception as e:
            print(f"Error loading to controller: {e}")
            QMessageBox.critical(self, "Error", f"Could not load to controller:\n{str(e)}")