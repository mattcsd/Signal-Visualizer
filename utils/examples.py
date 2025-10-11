"""
Beat Frequency Visualizer and Audio Analysis Module

This module provides a comprehensive audio analysis tool with real-time visualization
of beat frequencies, harmonics, and acoustic phenomena. It features multi-panel
visualization including waveform, amplitude envelope, spectrogram, and real-time FFT.

Key Features:
- Multi-panel audio visualization (waveform, envelope, spectrogram, FFT)
- Real-time playback cursor synchronization across all plots
- Interactive parameter controls for analysis customization
- Built-in help system with context-aware documentation
- Support for various acoustic phenomena analysis (beats, harmonics, resonance)
- High-resolution FFT with peak detection
- Smooth real-time updates using blitting for performance

Dependencies:
- numpy: Numerical computations and signal processing
- librosa: Audio analysis and feature extraction
- matplotlib: Multi-panel visualization and plotting
- PyQt5: Graphical user interface components
- scipy: Signal processing and peak detection
- PyQt5.QtMultimedia: Audio playback functionality

Author: Matteo Tsikalakis-Reeder
Date: 25/9/2025
Version: 1.0
"""

import numpy as np
import librosa
import librosa.display
import os
import time
import matplotlib.pyplot as plt
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtCore import QUrl, Qt
from PyQt5.QtWidgets import ( QTextBrowser, QComboBox, QCheckBox, QWidget, QVBoxLayout, QLabel, QScrollArea, 
                            QGroupBox, QPushButton, QMessageBox, 
                            QFormLayout, QSpinBox, QHBoxLayout,
                            QSizePolicy, QApplication)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT
from matplotlib.figure import Figure
from scipy.signal import find_peaks
from scipy.signal.windows import blackmanharris 

from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl
import os
import sys
from pathlib import Path

class BeatFrequencyVisualizer(QWidget):
    """
    Advanced audio analysis tool for visualizing beat frequencies and acoustic phenomena.
    
    This class provides comprehensive audio analysis capabilities including:
    - Multi-panel visualization of time and frequency domain representations
    - Real-time synchronized playback across all visualization panels
    - High-resolution FFT analysis with automatic peak detection
    - Interactive parameter controls for customizing analysis parameters
    - Context-aware help system with detailed explanations of acoustic phenomena
    
    The visualizer uses four synchronized panels to provide different perspectives
    on the audio signal, making it ideal for educational and analytical purposes.

    Attributes:
        controller: Reference to main application controller
        audio_data: Loaded audio signal as numpy array
        sample_rate: Audio sample rate in Hz
        time: Time array corresponding to audio_data
        playback_lines: List of vertical cursor lines for playback indication
        axes: List of references to all matplotlib axes
        backgrounds: Cached background for blitting optimization
        last_update_time: Timestamp for frame rate control
        update_interval: Minimum time between plot updates (seconds)
        first_playback: Flag indicating first playback after file load
        fft_size: Size of FFT for frequency analysis (affects resolution)
        peak_markers: Plot object for FFT peak indicators
        recordings_dir: Directory path for audio file storage
        media_player: Qt media player for audio playback
        figure: Main matplotlib figure instance
        canvas: Matplotlib canvas for Qt integration
        toolbar: Plot navigation toolbar
        Various UI controls: Spin boxes, buttons, dropdowns for parameter control
    """

    def __init__(self, parent=None, controller=None):
        """
        Initialize the Beat Frequency Visualizer widget.
        
        Args:
            parent: Parent widget (optional)
            controller: Main application controller for coordination (optional)
        """
        super().__init__(parent)
        self.controller = controller
        self.audio_data = None  # Will store loaded audio signal
        self.sample_rate = None  # Will store audio sample rate
        self.time = None  # Will store time array for audio data
        self.playback_lines = []  # Store playback cursor lines for all plots
        self.axes = []  # Store references to all axes for coordinated updates
        self.backgrounds = None  # Will store the complete figure background for blitting
        self.last_update_time = time.time()  # For frame rate control
        self.update_interval = 0.02  # 20ms for ~50fps smooth updates

        self.first_playback = True  # Flag to handle initial playback setup

        # FFT parameters for high-resolution frequency analysis
        self.fft_size = 4096 * 4  # 32768-point FFT for high frequency resolution
        self.peak_markers = None  # Will be initialized in plot_spectrogram for peak indicators
                
        # Set up recordings directory path - inside library/recordings
        self.recordings_dir = self.get_recordings_directory()
        
        # Create recordings directory if it doesn't exist
        if not self.recordings_dir.exists():
            try:
                self.recordings_dir.mkdir(parents=True, exist_ok=True)
                print(f"Created recordings directory: {self.recordings_dir}")
            except Exception as e:
                print(f"Could not create recordings directory: {e}")

        # Media player setup for audio playback
        self.media_player = QMediaPlayer()
        self.media_player.setNotifyInterval(20)  # 20ms update interval for smooth cursor
        self.media_player.positionChanged.connect(self.update_playback_cursor)
        
        self.init_ui()  # Initialize user interface
        self.load_audio_files_list()  # Load available audio files into dropdown

    def get_recordings_directory(self):
        """
        Determine the recordings directory path based on the application context.
        
        Returns:
            Path: Path to the recordings directory inside library/recordings
        """
        # Determine the base directory
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            base_dir = Path(sys.executable).parent
            
            # Special handling for macOS .app bundle
            if sys.platform == 'darwin' and '.app' in str(base_dir):
                # For macOS .app, go up to the .app bundle directory
                base_dir = base_dir.parent.parent.parent
            # Special handling for Linux AppImage
            elif sys.platform == 'linux' and 'APPIMAGE' in os.environ:
                # For Linux AppImage, use the directory containing the AppImage
                base_dir = Path(os.environ['APPIMAGE']).parent
        else:
            # Running from source
            base_dir = Path(__file__).parent.parent
        
        # recordings directory is inside library/recordings
        recordings_dir = base_dir / "library" / "recordings"
        return recordings_dir

    def init_ui(self):
        """
        Initialize the user interface with controls and visualization area.
        
        Creates the main window layout including:
        - Control panel with analysis parameters and playback controls
        - Navigation toolbar for plot interaction
        - Multi-panel matplotlib figure for audio visualization
        - Context-aware help system
        """
        self.setWindowTitle("Beat Frequency Visualizer")
        self.setMinimumSize(1000, 800)  # Set minimum window size
        
        # Initialize parameter control widgets
        self.max_freq_spin = QSpinBox()
        self.max_freq_spin.setRange(100, 10000)  # Frequency range limit for spectrogram
        self.max_freq_spin.setValue(2000)  # Default maximum frequency
        
        self.window_size_spin = QSpinBox()
        self.window_size_spin.setRange(256, 4096)  # FFT window size range
        self.window_size_spin.setValue(1024)  # Default window size
        
        self.hop_size_spin = QSpinBox()
        self.hop_size_spin.setRange(64, 1024)  # Hop size between analysis frames
        self.hop_size_spin.setValue(256)  # Default hop size
        
        # Replot button to refresh visualization with new parameters
        self.replot_btn = QPushButton("Replot")
        self.replot_btn.clicked.connect(self.plot_spectrogram)
        
        # File selection dropdown for audio file loading
        self.file_combo = QComboBox()
        self.file_combo.setMinimumWidth(200)  # Ensure adequate width for file names
        self.file_combo.currentIndexChanged.connect(self.on_file_selected)
        
        # Playback control buttons
        self.play_btn = QPushButton("Play")
        self.play_btn.clicked.connect(self.toggle_playback)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_playback)
        
        # Main layout configuration
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)  # Minimal margins
        main_layout.setSpacing(0)  # No spacing between main components
        
        # Control panel for parameters and playback
        control_panel = QWidget()
        control_layout = QHBoxLayout(control_panel)
        control_layout.setContentsMargins(5, 5, 5, 5)  # Internal margins
        
        # Parameters layout for analysis controls
        param_layout = QHBoxLayout()
        param_layout.addWidget(QLabel("Max Freq (Hz):"))
        param_layout.addWidget(self.max_freq_spin)
        param_layout.addWidget(QLabel("Window Size:"))
        param_layout.addWidget(self.window_size_spin)
        param_layout.addWidget(QLabel("Hop Size:"))
        param_layout.addWidget(self.hop_size_spin)
        param_layout.addWidget(self.replot_btn)

        # Help button for context-aware documentation
        self.help_btn = QPushButton("Help")
        self.help_btn.clicked.connect(self.show_help)
        param_layout.addWidget(self.help_btn)

        
        # Playback layout for file selection and transport controls
        playback_layout = QHBoxLayout()
        playback_layout.addWidget(QLabel("Select File:"))
        playback_layout.addWidget(self.file_combo)
        playback_layout.addWidget(self.play_btn)
        playback_layout.addWidget(self.stop_btn)
        
        # Add sub-layouts to control panel
        control_layout.addLayout(param_layout)
        control_layout.addStretch()  # Push playback controls to the right
        control_layout.addLayout(playback_layout)
        
        # Visualization area with matplotlib figure
        self.figure = Figure(figsize=(12, 10))  # Main figure with generous size
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)  # Plot navigation
        
        # Add all widgets to main layout
        main_layout.addWidget(control_panel)
        main_layout.addWidget(self.toolbar)
        main_layout.addWidget(self.canvas, stretch=1)  # Canvas gets most space
        
        self.setLayout(main_layout)

    def show_help(self):
        """
        Show context-aware help documentation based on current audio file.
        
        Creates a help window with HTML content that explains the acoustic
        phenomena relevant to the currently selected audio file. Uses a
        QWebEngineView to display formatted help content.
        """
        current_file = self.file_combo.currentText().lower()
        
        # Generate HTML content based on the selected file type
        html_content = self.generate_help_content(current_file)
        
        # Create help window
        self.help_window = QWidget()
        self.help_window.setWindowTitle(f"Help: {current_file}")
        self.help_window.resize(800, 600)
        
        layout = QVBoxLayout()
        web_view = QWebEngineView()
        
        # Use a data URL to display our HTML content
        web_view.setHtml(html_content, QUrl.fromLocalFile(''))
        
        layout.addWidget(web_view)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.help_window.close)
        layout.addWidget(close_btn)
        
        self.help_window.setLayout(layout)
        self.help_window.show()

    def plot_spectrogram(self):
        """
        Create the multi-panel audio visualization.
        
        Generates four synchronized visualization panels:
        1. Waveform: Time-domain representation of audio signal
        2. Amplitude Envelope: Smoothed amplitude over time
        3. Spectrogram: Time-frequency representation with color intensity
        4. Real-time FFT: High-resolution frequency spectrum with peak detection
        
        Uses librosa for audio analysis and matplotlib for visualization.
        Implements blitting for smooth real-time updates during playback.
        """
        if self.audio_data is None:
            return  # No audio data to visualize
            
        self.figure.clear()  # Clear previous plots
        self.playback_lines = []  # Reset playback cursor lines
        
        # Create 4 subplots with specific height ratios
        gs = self.figure.add_gridspec(4, 1, height_ratios=[1, 1, 2, 2], hspace=0.6)
        
        # 1. Waveform plot - raw audio signal in time domain
        self.ax_wave = self.figure.add_subplot(gs[0])
        self.ax_wave.plot(self.time, self.audio_data, color='b', linewidth=0.5, alpha=0.7)
        self.playback_lines.append(self.ax_wave.axvline(x=0, color='r', linewidth=1, animated=True))
        
        # 2. Amplitude envelope plot - smoothed amplitude over time
        self.ax_env = self.figure.add_subplot(gs[1], sharex=self.ax_wave)
        amplitude = np.abs(self.audio_data)
        smooth_window = int(0.02 * self.sample_rate)  # 20ms smoothing window
        amplitude_smooth = np.convolve(amplitude, np.ones(smooth_window)/smooth_window, mode='same')
        self.ax_env.plot(self.time, amplitude_smooth, 'b-', linewidth=1)
        self.playback_lines.append(self.ax_env.axvline(x=0, color='r', linewidth=1, animated=True))
        
        # 3. Spectrogram plot - time-frequency representation
        self.ax_spec = self.figure.add_subplot(gs[2], sharex=self.ax_wave)
        # Compute Short-Time Fourier Transform
        D = librosa.stft(self.audio_data,
                        n_fft=self.window_size_spin.value(),
                        hop_length=self.hop_size_spin.value(),
                        win_length=self.window_size_spin.value())
        S_db = librosa.amplitude_to_db(np.abs(D), ref=np.max)  # Convert to dB scale
        # Display spectrogram with viridis colormap
        librosa.display.specshow(S_db,
                               sr=self.sample_rate,
                               hop_length=self.hop_size_spin.value(),
                               x_axis='time',
                               y_axis='linear',
                               ax=self.ax_spec,
                               cmap='viridis',
                               vmin=-60,  # Dynamic range limits
                               vmax=0)
        self.playback_lines.append(self.ax_spec.axvline(x=0, color='r', linewidth=1, animated=True))
        
        # 4. Real-time FFT plot - high-resolution frequency spectrum
        self.ax_fft = self.figure.add_subplot(gs[3])
        freqs = np.fft.rfftfreq(self.fft_size, 1/self.sample_rate)  # Frequency bins

        # Initialize FFT line and peak markers
        self.fft_line, = self.ax_fft.semilogx(freqs, np.zeros_like(freqs), 'b-', linewidth=0.8)
        self.peak_markers, = self.ax_fft.plot([], [], 'ro', markersize=4, alpha=0.7)

        # Enhanced FFT plot styling
        self.ax_fft.set_title("High-Resolution Frequency Spectrum", pad=8)
        self.ax_fft.set_xlim(20, 10000)  # Human hearing range focus
        self.ax_fft.set_ylim(-80, 0)  # Wider dynamic range for better visibility
        self.ax_fft.grid(True, which='both', alpha=0.3)  # Major and minor grid
        self.ax_fft.set_xlabel("Frequency (Hz)", fontsize=9)
        self.ax_fft.set_ylabel("Magnitude (dB)", fontsize=9)

        # Set titles and labels for all axes
        self.ax_wave.set_title("Waveform")
        self.ax_env.set_title("Amplitude Envelope")
        self.ax_spec.set_title("Spectrogram")
        
        # Set axis limits and labels for coordinated display
        self.ax_wave.set_xlim(0, self.time[-1])  # Full audio duration
        self.ax_spec.set_ylim(0, self.max_freq_spin.value())  # User-defined frequency limit
        self.figure.tight_layout(rect=[0, 0, 1, 0.95])  # Adjust layout to fit window
        
        # Draw everything and cache background for blitting
        self.canvas.draw()
        self.background = self.canvas.copy_from_bbox(self.figure.bbox)
        
        # Enable animation for all playback cursor lines
        for line in self.playback_lines:
            line.set_animated(True)

    def update_playback_cursor(self, position):
        """
        Update playback cursor position and real-time FFT analysis.
        
        This method is called continuously during audio playback to:
        - Update the vertical cursor lines across all plots
        - Perform real-time FFT analysis on the current audio frame
        - Detect and mark spectral peaks in the FFT display
        - Use blitting for smooth, efficient visual updates
        
        Args:
            position: Current playback position in milliseconds
        """
        current_time = position / 1000  # Convert ms to seconds
        
        # Update real-time FFT only when audio is playing
        if self.media_player.state() == QMediaPlayer.PlayingState:
            start_sample = int(current_time * self.sample_rate)
            end_sample = start_sample + self.window_size_spin.value()
            
            # Ensure we have enough samples for analysis
            if end_sample < len(self.audio_data):
                frame = self.audio_data[start_sample:end_sample]
                
                # Apply Blackman-Harris window to reduce spectral leakage
                window = blackmanharris(len(frame))
                frame_windowed = frame * window
                
                # Compute FFT with high resolution
                fft_result = np.fft.rfft(frame_windowed, n=self.fft_size)
                fft_magnitude = np.abs(fft_result)
                fft_magnitude_db = 20 * np.log10(fft_magnitude + 1e-8)  # Convert to dB
                fft_magnitude_db -= np.max(fft_magnitude_db)  # Normalize so 0 dB is peak
                fft_magnitude_db = np.clip(fft_magnitude_db, -60, 0)  # Clamp dynamic range

                # Update FFT plot data
                freqs = np.fft.rfftfreq(self.fft_size, 1/self.sample_rate)
                self.fft_line.set_data(freqs, fft_magnitude_db) 

                # Find and mark spectral peaks for easy frequency identification
                peaks, _ = find_peaks(fft_magnitude_db, height=-40, prominence=6, width=2)
                if len(peaks) > 0:
                    self.peak_markers.set_data(freqs[peaks], fft_magnitude_db[peaks])
                else:
                    self.peak_markers.set_data([], [])  # Clear markers if no peaks
                        
        # Update playback cursors for all plots
        for line in self.playback_lines:
            line.set_xdata([current_time, current_time])
        
        # Use blitting for efficient, smooth updates
        if hasattr(self, 'background'):
            try:
                # Restore cached background
                self.canvas.restore_region(self.background)
                
                # Redraw FFT plot if playing (most frequently changing element)
                if self.media_player.state() == QMediaPlayer.PlayingState:
                    self.ax_fft.draw_artist(self.fft_line)
                    self.ax_fft.draw_artist(self.peak_markers)
                
                # Redraw cursor lines on all plots
                for line in self.playback_lines:
                    line.axes.draw_artist(line)
                
                # Blit the updated regions to canvas
                self.canvas.blit(self.figure.bbox)
            except Exception as e:
                print(f"Blitting error: {e}")
                # Fallback to full redraw if blitting fails
                self.canvas.draw()

    def load_audio_files_list(self):
        """
        Load all WAV files from the recordings directory into the dropdown.
        
        Scans the recordings directory for WAV files and populates the
        file selection dropdown. Attempts to select 'beat.wav' by default
        if available, otherwise selects the first file.
        """
        try:
            self.file_combo.clear()

            # Check if recordings directory exists
            if not self.recordings_dir.exists():
                self.file_combo.addItem("No recordings directory found")
                QMessageBox.warning(
                    self, 
                    "Directory Not Found", 
                    f"The recordings directory was not found at:\n{self.recordings_dir}\n\n"
                    "Please create a 'library/recordings' directory and add some WAV files."
                )
                return

            # Find all WAV files in recordings directory
            files = [
                f for f in os.listdir(self.recordings_dir)
                if f.lower().endswith(".wav")
            ]
                                    
            if not files:
                self.file_combo.addItem("No WAV files found in recordings")
                QMessageBox.information(
                    self,
                    "No Audio Files",
                    f"No WAV files found in:\n{self.recordings_dir}\n\n"
                    "Please add some WAV files to the recordings directory."
                )
                return
            
            # Add sorted list of files to dropdown
            for file in sorted(files):
                self.file_combo.addItem(file)
            
            # Try to select beat.wav by default if it exists
            beat_index = self.file_combo.findText("beat.wav")
            if beat_index >= 0:
                self.file_combo.setCurrentIndex(beat_index)
            else:
                self.on_file_selected(0)  # Load first file by default
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not list audio files: {str(e)}")

    def on_file_selected(self, index):
        """
        Handle when a new audio file is selected from the dropdown.
        
        Loads the selected audio file, initializes the media player,
        and generates the initial visualization. Handles playback
        state reset and error conditions.
        
        Args:
            index: Index of the selected file in the dropdown
        """
        if self.file_combo.count() == 0 or self.file_combo.currentText() in ["No WAV files found", "No recordings directory found", "No WAV files found in recordings"]:
            return  # No valid files available
            
        selected_file = self.file_combo.currentText()
        file_path = os.path.join(self.recordings_dir, selected_file)
        
        try:
            # Stop any current playback and reset button state
            self.media_player.stop()
            self.play_btn.setText("Play")  # Reset button text
            
            # Load audio file using librosa with consistent sample rate
            self.audio_data, self.sample_rate = librosa.load(
                file_path, 
                sr=44100,  # Standardize to 44.1kHz
                mono=True   # Force mono for consistent analysis
            )
            self.time = np.arange(len(self.audio_data)) / self.sample_rate
            
            # Set up media player with the selected file
            url = QUrl.fromLocalFile(file_path)
            self.media_player.setMedia(QMediaContent(url))
            
            # Generate initial visualization
            self.plot_spectrogram()
            self.first_playback = True  # Reset flag for new file
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load audio: {str(e)}")

    def cleanup(self):
        """
        Clean up resources when closing the application.
        
        Stops audio playback and clears media resources to ensure
        clean application shutdown.
        """
        self.media_player.stop()
        self.media_player.setMedia(QMediaContent())  # Clear media
        # Clear any other resources if needed

    def toggle_playback(self):
        """
        Toggle audio playback between play and pause states.
        
        Handles the play/pause functionality with proper state management.
        On first playback after file load, ensures the visualization is
        properly initialized.
        """
        if self.media_player.state() == QMediaPlayer.PlayingState:
            self.media_player.pause()
            self.play_btn.setText("Play")
        else:
            # If near end of track, restart from beginning
            if self.media_player.position() >= self.media_player.duration() - 100:
                self.media_player.setPosition(0)

            # Check if it's the first playback after file load
            if self.first_playback:
                self.plot_spectrogram()  # Ensure visualization is ready
                self.first_playback = False

            self.media_player.play()
            self.play_btn.setText("Pause")

    def stop_playback(self):
        """
        Stop audio playback and reset to beginning.
        
        Stops playback, resets the play button text, and moves the
        playback cursor back to the start position.
        """
        self.media_player.stop()
        self.play_btn.setText("Play")
        self.update_playback_cursor(0)  # Reset cursor to start

    def generate_help_content(self, filename):
        """
        Generate context-aware HTML help content based on audio file type.
        
        Creates detailed, formatted help documentation explaining the
        acoustic phenomena demonstrated by the selected audio file.
        Includes scientific explanations, musical applications, and
        practical tips for musicians and audio engineers.
        
        Args:
            filename: Name of the audio file (used to determine content)
            
        Returns:
            str: HTML formatted help content
        """
        filename_lower = filename.lower()
        
        if "beat" in filename_lower:
            return """
            <html>
            <head>
                <style>
                    body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
                    h1 { color: #2c3e50; }
                    img { max-width: 100%; height: auto; display: block; margin: 20px auto; }
                    .note { background-color: #f8f9fa; padding: 15px; border-left: 4px solid #3498db; }
                </style>
            </head>
            <body>
                <h1>Beat Frequencies in Acoustics</h1>
                
                <p>Beat frequencies occur when two sound waves of slightly different frequencies interfere with each other.</p>
                
                <h2>What Musicians Should Know</h2>
                
                <p>When tuning instruments, beats are actually useful! Here's why:</p>
                
                <div class="note">
                    <strong>Practical Tip:</strong> When tuning two strings to unison, listen for beats. 
                    As the frequencies get closer, the beats slow down. When they completely disappear, 
                    your strings are in perfect tune!
                </div>
                
                <h3>The Science Behind Beats</h3>
                
                <p>Mathematically, when two waves with frequencies f₁ and f₂ combine, you hear:</p>
                
                <ul>
                    <li>A <strong>carrier frequency</strong> at the average: (f₁ + f₂)/2</li>
                    <li>A <strong>beat frequency</strong> at the difference: |f₁ - f₂|</li>
                </ul>
                
                <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/7/7d/Interference_of_two_waves.svg/1200px-Interference_of_two_waves.svg.png" 
                     alt="Wave interference diagram" style="max-width: 500px;">
                <p style="text-align: center;"><em>Constructive and destructive interference creates the beating effect</em></p>
                
                <h3>Musical Applications</h3>
                
                <ul>
                    <li>Tuning instruments (especially strings and pipe organs)</li>
                    <li>Creating special effects in electronic music</li>
                    <li>Understanding how vibrato works</li>
                </ul>
                
                <h3>Try This Experiment</h3>
                
                <p>In this visualization:</p>
                <ol>
                    <li>Look at the waveform - see the amplitude modulation?</li>
                    <li>Check the spectrogram - can you spot the two close frequencies?</li>
                    <li>Listen carefully - count how many beats occur per second</li>
                </ol>
            </body>
            </html>
            """
        
        elif "combo" in filename_lower:
            return """
            <html><body style="font-family: Arial; max-width: 800px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #2c3e50;">Resonating Frequencies</h1>
                <p>This demonstrates how open strings resonate when other strings are played.</p>
                
                <h2>What's Happening</h2>
                <ul>
                    <li>First pluck shows the fundamental frequency</li>
                    <li>Subsequent plucks show sympathetic vibrations in other strings</li>
                    <li>Particularly strong on strings that share harmonic relationships</li>
                </ul>
                
                <h2>Musical Uses</h2>
                <ul>
                    <li><strong>Resonance:</strong> Harp and piano use this effect deliberately</li>
                    <li><strong>Tuning:</strong> Helps verify proper string relationships</li>
                    <li><strong>Composition:</strong> Used in spectral music compositions</li>
                </ul>
            </body></html>
            """
        
        elif "harmonics" in filename_lower:
            return """
            <html><body style="font-family: Arial; max-width: 800px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #2c3e50;">String Harmonics</h1>
                <p>Harmonics are pure tones created by dividing the string at specific nodes.</p>
                
                <h2>Types Demonstrated</h2>
                <ul>
                    <li><strong>Natural harmonics:</strong> Created by lightly touching the string at fractional divisions</li>
                    <li><strong>Artificial harmonics:</strong> Created by stopping the string and touching a node</li>
                </ul>
                
                <div style="background: #f8f9fa; padding: 15px; border-left: 4px solid #3498db;">
                    <strong>Did You Know?</strong> The harmonic at the 12th fret is exactly one octave above the open string.
                </div>
                
                <h2>Practical Uses</h2>
                <ul>
                    <li>Tuning reference (harmonics are always perfectly in tune)</li>
                    <li>Special effects in compositions</li>
                    <li>Checking instrument intonation</li>
                </ul>
            </body></html>
            """
        
        elif "eigen" in filename_lower:
            return """
            <html><body style="font-family: Arial; max-width: 800px; margin: 0 auto; padding: 20px;">
            """