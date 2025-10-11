"""
Audio FFT (Fast Fourier Transform) Visualizer Module

This module provides real-time audio visualization using FFT analysis of microphone input.
It displays both time-domain waveform and frequency-domain spectrum with interactive
controls for analysis and instrument tuning assistance.

Key Features:
- Real-time audio input visualization from microphone
- Dual-panel display: time-domain waveform and frequency-domain FFT spectrum
- Interactive frequency markers for instrument tuning
- Adjustable gain and vertical offset controls
- Log/linear frequency scale options
- Multiple audio input device support
- Instrument-specific frequency reference lines

Dependencies:
- numpy: Numerical computations and FFT processing
- pyaudio: Audio input stream handling
- scipy.fft: Fast Fourier Transform computations
- matplotlib: Real-time plotting and visualization
- PyQt5: Graphical user interface components

Author: Matteo Tsikalakis-Reeder
Date: 25/9/2025
Version: 1.0
"""

import numpy as np
import pyaudio
from scipy.fft import fft
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import (QMessageBox, QPushButton, QCheckBox, QWidget, QSlider, QVBoxLayout, QComboBox, QLabel, 
                            QHBoxLayout, QSizePolicy)
from PyQt5.QtCore import QTimer, Qt
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

class AudioFFTVisualizer(QWidget):
    """
    Real-time audio FFT visualizer with instrument tuning assistance.
    
    This class provides functionality for:
    - Capturing real-time audio input from microphone devices
    - Performing FFT analysis to display frequency spectrum
    - Showing both time-domain waveform and frequency-domain analysis
    - Providing instrument-specific frequency markers for tuning
    - Interactive controls for signal processing parameters
    
    The visualizer uses a dual-panel display with the top panel showing
    the time-domain waveform and the bottom panel showing the frequency
    spectrum with customizable frequency scale.

    Attributes:
        controller: Reference to main application controller
        CHUNK: Samples per buffer for audio processing
        FORMAT: Audio format (16-bit integer)
        CHANNELS: Number of audio channels (mono)
        RATE: Sample rate in Hz (44.1 kHz)
        frequency_range: Display frequency range (20Hz-20kHz human hearing)
        p: PyAudio instance
        input_devices: List of available audio input devices
        has_audio_input: Boolean indicating if audio input is available
        current_device_index: Currently selected audio input device
        zoom_level: Current gain/zoom level for FFT display
        min_zoom/max_zoom: Zoom level limits
        instrument_frequencies: Dictionary of instrument tuning frequencies
        instrument_labels: Dictionary of instrument note labels
        freq_markers: List of frequency reference line objects
        freq_labels: List of frequency label text objects
        audio_data: Current audio buffer data
        fft_data: Current FFT spectrum data
        running: Boolean controlling the visualization loop
        timer: QTimer for periodic plot updates
        figure: Matplotlib figure instance
        canvas: Matplotlib canvas for Qt integration
        toolbar: Plot navigation toolbar
        ax_wave: Waveform plot axes
        ax_fft: FFT spectrum plot axes
    """

    def __init__(self, master, controller):
        """
        Initialize the Audio FFT Visualizer widget.
        
        Args:
            master: Parent widget
            controller: Main application controller for coordination
        """
        super().__init__(master)
        
        # Audio parameters for PyAudio configuration
        self.CHUNK = 2048 * 4  # Samples per buffer (affects frequency resolution)
        self.FORMAT = pyaudio.paInt16  # 16-bit audio format
        self.CHANNELS = 1  # Mono audio input
        self.RATE = 44100  # Sample rate (Hz) - CD quality
        self.frequency_range = (20, 20000)  # Human hearing range (20Hz-20kHz)
        
        # Initialize PyAudio and get available input devices
        try:
            self.p = pyaudio.PyAudio()
            self.input_devices = self.get_input_devices()
            self.has_audio_input = len(self.input_devices) > 0
        except Exception as e:
            print(f"Error initializing audio: {e}")
            self.has_audio_input = False
            self.show_no_microphone_warning()
        
        # Only proceed if we have audio input devices available
        if not self.has_audio_input:
            self.setup_ui_disabled()
            return
            
        self.current_device_index = None  # Will be set when starting stream

        # Data for when freezing the plots.
        self.freeze_audio_data = None  # Stores frozen audio waveform data
        self.freeze_fft_data = None  # Stores frozen FFT magnitude data
        self.freeze_freqs = None     # Stores frozen frequency array

        # Visualization parameters
        self.zoom_level = 60  # Initial zoom level (dB range)
        self.min_zoom = 20    # Minimum zoom level (more zoomed in)
        self.max_zoom = 120   # Maximum zoom level (more zoomed out)
        
        # Instrument frequencies for tuning assistance (in Hz)
        self.instrument_frequencies = {
            'Guitar (Standard)': [82.41, 110.00, 146.83, 196.00, 246.94, 329.63],  # E2, A2, D3, G3, B3, E4
            'Violin': [196.00, 293.66, 440.00, 659.26],  # G3, D4, A4, E5
            'Cretan Lute': [110.00, 146.83, 196.00, 359],  # E A D G
            'Piano': [27.50, 55.00, 110.00, 220.00, 440.00, 880.00]  # A0-A5
        }
        
        # Corresponding note labels for each instrument
        self.instrument_labels = {
            'Guitar (Standard)': ['E2', 'A2', 'D3', 'G3', 'B3', 'E4'],
            'Violin': ['G3', 'D4', 'A4', 'E5'],
            'Cretan Lute': ['E', 'A', 'D', 'G'],
            'Piano': ['A0', 'A1', 'A2', 'A3', 'A4', 'A5']
        }
        
        self.freq_markers = []  # Store reference line objects for instrument frequencies
        self.freq_labels = []   # Store text label objects for frequency annotations

        # Setup matplotlib figure and canvas
        self.setup_ui()

        # Start audio stream with default device
        self.start_audio_stream()
        
        # Data buffers for audio processing
        self.audio_data = np.zeros(self.CHUNK)
        self.fft_data = np.zeros(self.CHUNK//2)
        self.running = True  # Control flag for the visualization loop
        
        # Timer for periodic plot updates (50 FPS)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(20)  # Update every 20ms

    def show_no_microphone_warning(self):
        """
        Show a warning message when no microphone is available.
        
        Displays a user-friendly message when the application cannot
        detect any audio input devices, explaining the limitation.
        """
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setText("No audio input devices found")
        msg.setInformativeText("The application will run in disabled mode. Please connect a microphone to use audio features.")
        msg.setWindowTitle("Audio Device Not Found")
        msg.exec_()

    def setup_ui_disabled(self):
        """
        Setup a disabled UI when no microphone is available.
        
        Creates a minimal interface with a message indicating that
        audio features are unavailable due to missing input devices.
        """
        main_layout = QVBoxLayout(self)
        
        # Create disabled message
        disabled_label = QLabel("Audio features disabled - no input devices available")
        disabled_label.setAlignment(Qt.AlignCenter)
        disabled_label.setStyleSheet("font-size: 16px; color: #888;")
        
        main_layout.addWidget(disabled_label)
        self.setLayout(main_layout)

    def get_input_devices(self):
        """
        Get list of available audio input devices with their indices.
        
        Scans through all available audio devices and returns those
        that support audio input (have input channels).
        
        Returns:
            list: List of dictionaries containing device information
                  with keys: 'index', 'name', 'channels'
        """
        devices = []
        try:
            for i in range(self.p.get_device_count()):
                dev = self.p.get_device_info_by_index(i)
                if dev['maxInputChannels'] > 0:
                    devices.append({
                        'index': i,
                        'name': dev['name'],
                        'channels': dev['maxInputChannels']
                    })
        except Exception as e:
            print(f"Error getting input devices: {e}")
        return devices

    def setup_ui(self):
        """
        Configure the main UI layout with proper Qt widgets.
        
        Creates the complete user interface including:
        - Matplotlib figure with dual-panel plot
        - Navigation toolbar for plot interaction
        - Control panel with device selection, gain, offset, and instrument controls
        """
        main_layout = QVBoxLayout(self)
        
        # Create matplotlib figure and canvas
        self.figure = Figure(figsize=(12, 8))
        self.canvas = FigureCanvas(self.figure)
        
        # Add navigation toolbar for plot interaction
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        # Create control panel with Qt widgets
        control_panel = QWidget()
        control_layout = QHBoxLayout(control_panel)

        # Instrument dropdown for tuning assistance
        self.instrument_label = QLabel("Instrument:")
        self.instrument_dropdown = QComboBox()
        self.instrument_dropdown.addItem("-- Select Instrument --", None)  # Default empty option
        self.instrument_dropdown.addItems(self.instrument_frequencies.keys())
        self.instrument_dropdown.currentTextChanged.connect(self.update_instrument_markers)

        # Add reset button to restore default settings
        self.reset_button = QPushButton("Reset Values")
        self.reset_button.clicked.connect(self.reset_values)

        # Add freeze button
        self.freeze_button = QPushButton("Freeze Plots")
        self.freeze_button.setCheckable(True)  # Make it toggleable
        self.freeze_button.clicked.connect(self.toggle_freeze)
        self.freeze_button.setStyleSheet("""
            QPushButton {
                background-color: #d3d3d3;  /* Light gray when unfrozen */
                border: 1px solid #999;
                padding: 5px 10px;
                border-radius: 3px;
            }
            QPushButton:checked {
                background-color: #2196F3;  /* Blue when frozen */
                color: white;
                border: 1px solid #1976D2;
            }
        """)
        
        # Device selection dropdown
        self.device_label = QLabel("Input Device:")
        self.device_dropdown = QComboBox()
        self.populate_device_dropdown()
        self.device_dropdown.currentIndexChanged.connect(self.change_device)
        
        # Gain slider (labeled as zoom but functions as gain control)
        self.zoom_label = QLabel("Gain:")
        self.zoom_slider = QSlider()
        self.zoom_slider.setOrientation(Qt.Horizontal)
        self.zoom_slider.setRange(10, 120)  # 10=very amplified, 120=very attenuated
        self.zoom_slider.setValue(60)       # Default neutral position
        self.zoom_slider.valueChanged.connect(self.update_zoom_level)

        # Vertical offset slider for FFT display
        self.offset_label = QLabel("Vertical Offset:")
        self.offset_slider = QSlider()
        self.offset_slider.setOrientation(Qt.Horizontal)
        self.offset_slider.setRange(-40, 40)  # -40dB to +40dB offset range
        self.offset_slider.setValue(0)        # Default no offset
        self.offset_slider.valueChanged.connect(self.update_plot)

        # Log/linear frequency scale checkbox
        self.log_freq_checkbox = QCheckBox("Linear Frequency")
        self.log_freq_checkbox.setChecked(False)  # Default to log scale
        self.log_freq_checkbox.stateChanged.connect(self.update_plot)
        
        # Add widgets to control panel
        control_layout.addWidget(self.device_label)
        control_layout.addWidget(self.device_dropdown)
        control_layout.addWidget(self.zoom_label)
        control_layout.addWidget(self.zoom_slider)
        control_layout.addWidget(self.offset_label)
        control_layout.addWidget(self.offset_slider)
        control_layout.addWidget(self.log_freq_checkbox)
        control_layout.addWidget(self.freeze_button)


        control_layout.addWidget(self.instrument_label)
        control_layout.addWidget(self.instrument_dropdown)
        control_layout.addWidget(self.reset_button)
        
        # Add stretch to push controls left and maintain spacing
        control_layout.addStretch()
        
        # Add widgets to main layout
        main_layout.addWidget(self.toolbar)
        main_layout.addWidget(self.canvas)
        main_layout.addWidget(control_panel)
        
        # Setup the dual-panel plots
        self.setup_plots()

    def start_audio_stream(self, device_index=None):
        """
        Start the audio input stream with specified device.
        
        Opens a PyAudio input stream with the specified device index.
        If no device is specified, uses the system default input device.
        
        Args:
            device_index: Index of the audio input device to use, or None for default
        """
        if not self.has_audio_input:
            return
            
        if hasattr(self, 'stream'):
            self.stream.stop_stream()
            self.stream.close()

        try:
            self.stream = self.p.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                output=False,
                frames_per_buffer=self.CHUNK,
                input_device_index=device_index,
                stream_callback=self.audio_callback
            )
            self.current_device_index = device_index
            print(f"Stream started with device index: {device_index if device_index else 'default'}")
        except Exception as e:
            print(f"Error opening stream: {e}")
            self.show_stream_error_message(str(e))

    def show_stream_error_message(self, error_details):
        """
        Show an error message when audio stream fails to open.
        
        Args:
            error_details: Detailed error message from PyAudio exception
        """
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText("Failed to open audio stream")
        msg.setInformativeText(f"Error details: {error_details}")
        msg.setWindowTitle("Audio Stream Error")
        msg.exec_()

    def reset_values(self):
        """
        Reset all controls to default values.
        
        Restores the default settings for:
        - Gain/zoom level (60)
        - Vertical offset (0)
        - Frequency scale (logarithmic)
        Then triggers a plot update to reflect the changes.
        """
        self.zoom_slider.setValue(60)
        self.offset_slider.setValue(0)
        self.log_freq_checkbox.setChecked(False)
        self.update_plot()

    def update_instrument_markers(self, instrument_name):
        """
        Update the frequency reference lines based on selected instrument.
        
        Clears existing frequency markers and creates new vertical lines
        and labels at the fundamental frequencies of the selected instrument.
        This helps users identify and tune to specific instrument notes.
        
        Args:
            instrument_name: Name of the selected instrument, or None to clear markers
        """
        # Clear existing markers and labels
        for marker in self.freq_markers:
            marker.remove()
        for label in self.freq_labels:
            label.remove()
        self.freq_markers.clear()
        self.freq_labels.clear()

        # Skip if no instrument selected or it's the placeholder
        if not instrument_name or instrument_name == "-- Select Instrument --":
            self.canvas.draw()
            return

        # Get frequencies and labels for selected instrument
        frequencies = self.instrument_frequencies.get(instrument_name, [])
        labels = self.instrument_labels.get(instrument_name, [])

        # Create vertical lines and labels for each frequency
        colors = [
                '#FF5733',  # Red-orange
                '#33FF57',  # Green
                '#3357FF',  # Blue
                '#F033FF',  # Purple 
                '#FFC733',  # Yellow-orange (new)
                '#33FFF0'   # Cyan (new)
        ]
        
        # Calculate dynamic vertical positions (higher on the plot)
        num_notes = len(frequencies)
        base_y = 25  # Starting y position (higher up)
        y_step = 20   # Vertical spacing between labels
        y_positions = [base_y - (i % 3) * y_step for i in range(num_notes)]
        angle = 30  # Rotation angle for labels
        
        for freq, label, color, y_pos in zip(frequencies, labels, colors, y_positions):
            # Add vertical line at instrument frequency
            marker = self.ax_fft.axvline(x=freq, color=color, linestyle='--', alpha=0.7, linewidth=1.5)
            self.freq_markers.append(marker)
            
            # Add text label without box for better visibility
            text = self.ax_fft.text(
                freq, y_pos, f"{label} ({freq:.1f}Hz)", 
                color=color, 
                ha='center', 
                va='top',
                fontsize=10,
                alpha=0.9,
                weight='bold',
                rotation=angle,
                rotation_mode='anchor'
            )
            self.freq_labels.append(text)

        # Adjust ylim to ensure labels are visible
        current_ylim = self.ax_fft.get_ylim()
        self.ax_fft.set_ylim(current_ylim[0], current_ylim[1])  # Keep existing upper limit
        
        self.canvas.draw()

    def populate_device_dropdown(self):
        """
        Populate the dropdown with available audio input devices.
        
        Scans available input devices and adds them to the device
        selection dropdown with descriptive names including channel count.
        Selects the system default input device if available.
        """
        self.device_dropdown.clear()
        for dev in self.input_devices:
            self.device_dropdown.addItem(
                f"{dev['name']} (Ch: {dev['channels']})", 
                userData=dev['index']
            )
        
        # Select default device if available
        default_device = self.p.get_default_input_device_info()
        if default_device:
            for i, dev in enumerate(self.input_devices):
                if dev['index'] == default_device['index']:
                    self.device_dropdown.setCurrentIndex(i)
                    break

    def setup_plots(self):
        """
        Configure matplotlib plots for waveform and FFT display.
        
        Creates a dual-panel plot configuration:
        - Top panel: Time-domain waveform of audio input
        - Bottom panel: Frequency-domain FFT spectrum with log frequency scale
        
        Initializes plot lines, labels, grids, and custom frequency ticks.
        """
        # Create subplots (2 rows, 1 column)
        self.ax_wave = self.figure.add_subplot(211)  # Top: waveform
        self.ax_fft = self.figure.add_subplot(212)   # Bottom: FFT spectrum
        
        # Waveform plot initialization
        self.x_wave = np.arange(0, self.CHUNK)
        self.line_wave, = self.ax_wave.plot(self.x_wave, np.zeros(self.CHUNK), 'b')
        self.ax_wave.set_title('Time Domain - Microphone Input')
        self.ax_wave.set_xlim(0, self.CHUNK)
        self.ax_wave.set_ylim(-1, 1)  # Normalized amplitude range
        self.ax_wave.set_ylabel('Amplitude')
        self.ax_wave.grid(True)
        
        # FFT plot initialization with log frequency scale
        freqs = np.fft.rfftfreq(self.CHUNK, 1 / self.RATE)
        self.line_fft, = self.ax_fft.semilogx(freqs, np.zeros_like(freqs), 'r')
        
        # Changing the coordinate format
        def format_time_amp(x, y):
            # Convert sample index to time in seconds
            time_sec = x / self.RATE
            return f"time = {time_sec:.2f} s, amplitude = {y:.3f}"

        def format_freq_db(x, y):
            return f"freq = {x:.1f} Hz, magnitude = {y:.1f} dB"

        # Apply custom coordinate formatting
        self.ax_wave.format_coord = format_time_amp
        self.ax_fft.format_coord = format_freq_db

        # Setup custom log-scale frequency ticks
        self.setup_log_ticks()

        self.ax_fft.set_title('Frequency Domain - FFT Analysis')
        self.ax_fft.set_xlim(*self.frequency_range)  # Human hearing range
        self.ax_fft.set_ylim(-self.zoom_level, 0)   # dB scale
        self.ax_fft.set_xlabel('Frequency (Hz)')
        self.ax_fft.set_ylabel('Magnitude (dB)')
        self.ax_fft.grid(True, which='both')  # Major and minor grid lines

    def update_zoom_level(self, value):
        """
        Update the zoom/gain level for the FFT plot.
        
        The zoom level controls the dynamic range displayed in the FFT plot.
        Lower values show a more zoomed-in view (smaller dB range), while
        higher values show a more zoomed-out view (larger dB range).
        
        Args:
            value: New zoom level (10-120, where 60 is neutral)
        """
        self.zoom_level = value
        self.ax_fft.set_ylim(-self.zoom_level, 0)
        self.canvas.draw()

    def change_device(self, index):
        """
        Handle device selection change from dropdown.
        
        Args:
            index: Index of the selected device in the dropdown
        """
        device_index = self.device_dropdown.itemData(index)
        print(f"Selected device index: {device_index}")
        self.start_audio_stream(device_index)

    def audio_callback(self, in_data, frame_count, time_info, status):
        """
        Callback function for audio stream input.
        
        This function is called by PyAudio whenever new audio data is available.
        It converts the raw audio bytes to normalized floating-point values
        and stores them for processing by the update_plot method.
        
        Args:
            in_data: Raw audio input bytes
            frame_count: Number of frames in the buffer
            time_info: Timing information dictionary
            status: Stream status flags
            
        Returns:
            tuple: (in_data, pyaudio.paContinue) to continue stream
        """
        if self.running:
            # Convert 16-bit integer data to normalized float (-1 to 1)
            self.audio_data = np.frombuffer(in_data, dtype=np.int16) / 32768.0
        return (in_data, pyaudio.paContinue)

    def setup_log_ticks(self):
        """
        Configure custom log-scale frequency ticks for better readability.
        
        Creates manually positioned frequency ticks with human-readable
        labels (Hz for <1000, kHz for >=1000). This provides a more
        intuitive frequency scale than the default log scale ticks.
        """
        # Set manual tick positions at specific frequencies
        tick_positions = []
        tick_labels = []
        
        # Define our frequency steps for optimal readability
        steps_under_100 = [20, 30, 40, 50, 60, 70, 80, 90, 100]
        steps_100_to_1000 = [
            100, 125, 150, 175, 200, 250, 300, 350, 
            400, 500, 600, 700, 800, 900, 1000
        ]
        steps_above_1000 = [1000, 1500, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000]
        
        # Combine all steps
        all_steps = steps_under_100 + steps_100_to_1000 + steps_above_1000
        
        # Create ticks and labels
        for freq in all_steps:
            if 20 <= freq <= 20000:  # Within our display range
                tick_positions.append(freq)
                if freq < 1000:
                    tick_labels.append(f"{freq:.0f}")
                else:
                    if freq % 1000 == 0:
                        tick_labels.append(f"{freq//1000}k")
                    else:
                        tick_labels.append(f"{freq/1000:.1f}k")
        
        # Set the custom ticks
        self.ax_fft.set_xticks(tick_positions)
        self.ax_fft.set_xticklabels(tick_labels, rotation=45, ha='right', rotation_mode='anchor')        
        
        # Configure minor ticks (more dense between major ticks)
        self.ax_fft.xaxis.set_minor_locator(plt.LogLocator(
            base=10, 
            subs=np.linspace(0.1, 1.0, 10)[1:-1]  # More minor ticks between majors
        ))
        self.ax_fft.minorticks_on()

        # Adjust layout to prevent label cutoff
        self.figure.tight_layout()
        self.figure.subplots_adjust(bottom=0.15)  # Add more space at bottom
    
        # Style adjustments for better visual appearance
        self.ax_fft.tick_params(axis='x', which='major', length=6, width=1)
        self.ax_fft.tick_params(axis='x', which='minor', length=3, width=0.5)

    def cleanup(self):
        """
        Clean up resources when closing the application.
        
        Stops the audio stream, terminates PyAudio, and ensures
        all resources are properly released.
        """
        self.running = False
        if self.has_audio_input:
            if hasattr(self, 'stream'):
                self.stream.stop_stream()
                self.stream.close()
            self.p.terminate()

    def toggle_freeze(self):
        """
        Toggle between frozen and live display for both waveform and FFT.
        
        When frozen:
        - Button turns blue and says "Unfreeze Display"
        - Both waveform and FFT plots show snapshots
        - Audio processing continues in background but display is frozen
        
        When unfrozen:
        - Button returns to gray and says "Freeze Display" 
        - Both plots update in real-time
        """
        if self.freeze_button.isChecked():
            # Freeze the current audio and FFT data
            self.freeze_audio_data = self.audio_data.copy()
            self.freeze_fft_data = self.fft_data.copy()
            self.freeze_freqs = np.fft.rfftfreq(self.CHUNK, 1 / self.RATE)
            self.freeze_button.setText("Unfreeze Display")
            print("Display frozen - holding current waveform and spectrum")
        else:
            # Release the frozen data
            self.freeze_audio_data = None
            self.freeze_fft_data = None
            self.freeze_freqs = None
            self.freeze_button.setText("Freeze Display")
            print("Display unfrozen - showing live data")
        
        # Update the plot to reflect freeze state
        self.update_plot()

    def update_plot(self):
        """
        Update the plots with new audio data.
        
        Modified to handle frozen state for both waveform and FFT.
        """
        if not self.running or not hasattr(self, 'audio_data'):
            return

        # Check if display is frozen
        if self.freeze_button.isChecked() and hasattr(self, 'freeze_audio_data'):
            # Use frozen data for both plots
            processed_audio = self.freeze_audio_data * (self.zoom_level / 60.0)
            mag_db = self.freeze_fft_data
            freqs = self.freeze_freqs
        else:
            # Use live data with current processing
            zoom_factor = self.zoom_level / 60.0
            processed_audio = self.audio_data * zoom_factor
            
            # Compute live FFT
            window = np.hanning(len(processed_audio))
            yf = fft(processed_audio * window)
            mag_lin = 2 / self.CHUNK * np.abs(yf[:len(yf)//2 + 1])
            mag_db = 20 * np.log10(mag_lin + 1e-8) + self.offset_slider.value()
            freqs = np.fft.rfftfreq(self.CHUNK, 1 / self.RATE)
            
            # Store current data for potential freezing
            self.fft_data = mag_db.copy()

        # Update waveform plot
        self.line_wave.set_ydata(processed_audio)
        self.ax_wave.set_ylim(-1, 1)

        # Update FFT line data
        min_length = min(len(freqs), len(mag_db))
        self.line_fft.set_data(freqs[:min_length], mag_db[:min_length])

        # Handle frequency scale type (logarithmic or linear)
        if self.log_freq_checkbox.isChecked():
            self.ax_fft.set_xscale("linear")
            self.ax_fft.set_xlim(0, self.RATE / 2)
            self.ax_fft.xaxis.set_major_formatter(plt.ScalarFormatter())
            self.ax_fft.xaxis.set_major_locator(plt.MaxNLocator(10))
        else:
            self.ax_fft.set_xscale("log")
            self.ax_fft.set_xlim(*self.frequency_range)
            self.setup_log_ticks()
                        
        # Remove any zero lines (including red line artifacts)
        for line in self.ax_fft.lines:
            if len(line.get_ydata()) > 0 and np.all(line.get_ydata() == 0):
                line.remove()

        # Adjust y-limits based on current offset settings
        max_offset = self.offset_slider.maximum()
        self.ax_fft.set_ylim(-60 - max_offset, 0 + max_offset)

        # Update plot titles to indicate frozen state
        if self.freeze_button.isChecked():
            self.ax_wave.set_title('Time Domain - Microphone Input [FROZEN]')
            self.ax_fft.set_title('Frequency Domain - FFT Analysis [FROZEN]')
        else:
            self.ax_wave.set_title('Time Domain - Microphone Input')
            self.ax_fft.set_title('Frequency Domain - FFT Analysis')

        self.canvas.draw()
    

    def closeEvent(self, event):
        """
        Handle window close event for proper cleanup.
        
        Ensures audio resources are properly released when the
        application window is closed.
        
        Args:
            event: QCloseEvent object
        """
        self.running = False
        if hasattr(self, 'stream'):
            self.stream.stop_stream()
            self.stream.close()
        self.p.terminate()
        event.accept()