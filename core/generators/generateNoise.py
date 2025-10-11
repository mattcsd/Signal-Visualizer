"""
Noise Generator Module

This module provides a dialog interface for generating noise with
mathematical visualization and interactive controls. It allows users to create
custom-random noise with adjustable parameters and load them into the main application.

Dependencies:
- matplotlib: Plotting and visualization
- numpy: Numerical computations and signal generation
- sounddevice: Audio playback functionality
- PyQt5: Graphical user interface components
- colorednoise: Libradry for colored noise.


Author: Matteo Tsikalakis-Reeder
Date: 25/09/2025
Version: 1.0
"""


import numpy as np
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QSlider, QLineEdit, QPushButton,
    QMessageBox
)
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.widgets import SpanSelector
import sounddevice as sd
import colorednoise as cn  # Ensure this is installed

class Noise(QWidget):
    """
    Noise Generation Widget for creating and visualizing different types of noise signals.
    Supports white, pink, and brown noise generation with real-time playback and plotting.
    """
    
    def __init__(self, master, controller):
        """
        Initialize the noise generation widget.
        
        Args:
            master: The parent widget
            controller: The main application controller for navigation and help system
        """
        super().__init__(master)
        self.controller = controller
        self.master = master
        self.selectedAudio = np.empty(1)  # Store selected audio fragment
        self.setup_ui()  # Initialize the user interface

    def setup_ui(self):
        """Set up the user interface components and layout."""
        self.setWindowTitle('Generate noise')
        self.layout = QVBoxLayout(self)
        
        # Default parameter values for noise generation
        default_values = [
            ['NOISE', '\t duration', 1.0, '\t amplitude', 0.5, '\t fs', 44100, '\t noise type', 'white'],
            ['PURE TONE', '\t duration', 1.0, '\t amplitude', 0.5, '\t fs', 44100, 
             '\t offset', 0.0, '\t frequency', 440, '\t phase', 0.0],
        ]
        
        # Initialize noise parameters from defaults
        self.duration = float(default_values[0][2])    # Duration in seconds
        self.amplitude = float(default_values[0][4])   # Amplitude (0.0 to 1.0)
        self.fs = int(default_values[0][6])           # Sample rate in Hz
        self.noise_type = default_values[0][8]        # Type of noise

        # === Noise Type Selection ===
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel('Noise type:'))
        self.type_combo = QComboBox()
        self.type_combo.addItems(['White noise', 'Pink noise', 'Brown noise'])
        self.type_combo.setCurrentText(self.noise_type)
        type_layout.addWidget(self.type_combo)
        self.layout.addLayout(type_layout)

        # === Amplitude Control ===
        ampl_layout = QHBoxLayout()
        ampl_layout.addWidget(QLabel('Max. amplitude:'))
        self.ampl_slider = QSlider(Qt.Horizontal)
        self.ampl_slider.setRange(0, 100)  # 0% to 100% range
        self.ampl_slider.setValue(int(self.amplitude * 100))  # Convert to percentage
        self.ampl_entry = QLineEdit(f"{self.amplitude:.2f}")
        self.ampl_entry.setFixedWidth(80)  # Fixed width for consistent layout
        ampl_layout.addWidget(self.ampl_slider)
        ampl_layout.addWidget(self.ampl_entry)
        self.layout.addLayout(ampl_layout)

        # === Duration Control ===
        dura_layout = QHBoxLayout()
        dura_layout.addWidget(QLabel('Total duration (s):'))
        self.dura_slider = QSlider(Qt.Horizontal)
        self.dura_slider.setRange(1, 3000)  # 0.01s to 30s (divided by 100)
        self.dura_slider.setValue(int(self.duration * 100))
        self.dura_entry = QLineEdit(f"{self.duration:.2f}")
        self.dura_entry.setFixedWidth(80)
        dura_layout.addWidget(self.dura_slider)
        dura_layout.addWidget(self.dura_entry)
        self.layout.addLayout(dura_layout)

        # === Sample Rate Input ===
        fs_layout = QHBoxLayout()
        fs_layout.addWidget(QLabel('Fs (Hz):'))
        self.fs_entry = QLineEdit(str(self.fs))
        self.fs_entry.setFixedWidth(80)
        fs_layout.addWidget(self.fs_entry)
        self.layout.addLayout(fs_layout)

        # === Control Buttons ===
        button_layout = QHBoxLayout()
        self.plot_button = QPushButton('Plot')
        self.controller_button = QPushButton('Load to Controller')
        #self.save_button = QPushButton('Save')  # Commented out for future implementation
        self.help_button = QPushButton('🛈')  # Information button
        self.help_button.setFixedWidth(30)
        button_layout.addStretch()  # Push buttons to the right
        button_layout.addWidget(self.controller_button)
        button_layout.addWidget(self.help_button)
        button_layout.addWidget(self.plot_button)
        self.layout.addLayout(button_layout)

        # === Plotting Area ===
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)  # Matplotlib navigation toolbar
        self.ax = self.figure.add_subplot(111)  # Main plot axis
        self.layout.addWidget(self.toolbar)
        self.layout.addWidget(self.canvas)

        # === Connect Signals and Slots ===
        # Amplitude controls
        self.ampl_slider.valueChanged.connect(self.update_amplitude)
        self.ampl_entry.editingFinished.connect(self.update_amplitude_from_entry)
        
        # Duration controls  
        self.dura_slider.valueChanged.connect(self.update_duration)
        self.dura_entry.editingFinished.connect(self.update_duration_from_entry)
        
        # Action buttons
        self.plot_button.clicked.connect(self.plot_noise)
        self.controller_button.clicked.connect(self.load_to_controller)
        self.help_button.clicked.connect(lambda: self.controller.help.createHelpMenu(5))

        # Generate and plot initial noise
        self.plot_noise()

    def load_to_controller(self):
        """
        Load the generated noise signal to a new controller window for further analysis.
        Creates a ControlMenu window with the current noise parameters and audio data.
        """
        from core.controlMenu import ControlMenu

        try:
            # Re-plot to ensure audio data is up to date
            self.plot_noise()
            
            # Use selected fragment if available, otherwise use full audio
            audio_to_load = (
                self.selectedAudio if self.selectedAudio.size > 1 else self.audio
            )
            duration = self.duration
            fs = self.fs
            
            # Create descriptive window title
            noise_type = self.type_combo.currentText()
            title = f"{noise_type} ({duration:.2f}s)"
            
            # Ensure controller has required interface methods
            if not hasattr(self.controller, 'adse'):
                from PyQt5.QtWidgets import QWidget
                self.controller = QWidget()
                self.controller.adse = type('', (), {})()
                self.controller.adse.advancedSettings = lambda: print("Advanced settings not available")
            
            # Create controller window with the generated noise
            control_window = ControlMenu(title, fs, audio_to_load, duration, self.controller)
            
            # Track open control windows for management
            if not hasattr(self, 'control_windows'):
                self.control_windows = []
            self.control_windows.append(control_window)
            
            # Cleanup when window is closed
            control_window.destroyed.connect(
                lambda: self.control_windows.remove(control_window) 
                if control_window in self.control_windows else None
            )
            
            # Show and focus the new window
            control_window.show()
            control_window.activateWindow()
            
        except Exception as e:
            print(f"Error loading noise to controller: {e}")
            QMessageBox.critical(self, "Error", f"Could not load noise to controller: {str(e)}")

    def update_amplitude(self, value):
        """
        Update amplitude value from slider change.
        
        Args:
            value (int): Slider value (0-100 representing 0.0-1.0)
        """
        self.amplitude = value / 100  # Convert percentage to decimal
        self.ampl_entry.setText(f"{self.amplitude:.2f}")

    def update_duration(self, value):
        """
        Update duration value from slider change.
        
        Args:
            value (int): Slider value (1-3000 representing 0.01-30.0 seconds)
        """
        self.duration = value / 100  # Convert slider units to seconds
        self.dura_entry.setText(f"{self.duration:.2f}")

    def update_amplitude_from_entry(self):
        """Update amplitude value from text entry field with validation."""
        try:
            value = float(self.ampl_entry.text())
            if 0 <= value <= 1:
                self.amplitude = value
                self.ampl_slider.setValue(int(value * 100))  # Update slider position
            else:
                # Reset to previous value if out of range
                self.ampl_entry.setText(f"{self.amplitude:.2f}")
        except ValueError:
            # Reset to previous value if invalid input
            self.ampl_entry.setText(f"{self.amplitude:.2f}")

    def update_duration_from_entry(self):
        """Update duration value from text entry field with validation."""
        try:
            value = float(self.dura_entry.text())
            if 0.01 <= value <= 30:  # Validate reasonable duration range
                self.duration = value
                self.dura_slider.setValue(int(value * 100))  # Update slider position
            else:
                # Reset to previous value if out of range
                self.dura_entry.setText(f"{self.duration:.2f}")
        except ValueError:
            # Reset to previous value if invalid input
            self.dura_entry.setText(f"{self.duration:.2f}")

    def plot_noise(self):
        """
        Generate and plot the selected type of noise based on current parameters.
        Also enables audio fragment selection using SpanSelector.
        """
        try:
            # Validate and update sample rate
            self.fs = int(self.fs_entry.text())
            if self.fs > 48000:
                self.fs = 48000  # Enforce maximum sample rate
                self.fs_entry.setText("48000")
                QMessageBox.warning(self, 'Wrong sample frequency value',
                                    'The sample frequency cannot be greater than 48000 Hz.')
                return
        except ValueError:
            QMessageBox.warning(self, 'Invalid Input', 'Please enter a valid integer for sample frequency.')
            return

        # Get noise type selection and calculate number of samples
        choice = self.type_combo.currentText()
        samples = int(self.duration * self.fs)

        # Map noise type to colored noise beta parameter:
        # White noise: beta=0, Pink noise: beta=1, Brown noise: beta=2
        beta = {"White noise": 0, "Pink noise": 1, "Brown noise": 2}.get(choice, 1)

        # Generate time array and colored noise
        self.time = np.linspace(0, self.duration, samples, endpoint=False)
        noise_raw = cn.powerlaw_psd_gaussian(beta, samples)  # Generate colored noise
        
        # Normalize and scale noise to desired amplitude
        self.audio = self.amplitude * noise_raw / max(abs(noise_raw))

        # Clear previous plot and create new one
        self.ax.clear()
        self.ax.plot(self.time, self.audio)
        self.ax.set(xlabel='Time (s)', ylabel='Amplitude', xlim=[0, self.duration])
        self.ax.axhline(y=0, color='black', linewidth='0.5', linestyle='--')  # Zero reference line

        # Add interactive span selector for audio fragment selection
        self.span = SpanSelector(
            self.ax, self.listen_fragment, 'horizontal',
            useblit=True, interactive=True, drag_from_anywhere=True
        )

        # Refresh the plot
        self.canvas.draw()

    def listen_fragment(self, xmin, xmax):
        """
        Play the selected audio fragment using sounddevice.
        Called when a time range is selected on the plot.
        
        Args:
            xmin (float): Start time of selected fragment in seconds
            xmax (float): End time of selected fragment in seconds
        """
        # Find indices corresponding to the selected time range
        ini, end = np.searchsorted(self.time, (xmin, xmax))
        self.selectedAudio = self.audio[ini:end + 1]  # Extract selected audio fragment
        
        # Play the selected fragment using sounddevice
        sd.play(self.selectedAudio, self.fs)