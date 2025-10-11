"""
Square Wave Generator Module

This module provides a dialog interface for generating square wave signals with
fully adjustable parameters. It features real-time waveform visualization and
interactive audio playback capabilities.

Key Features:
- Generate square waves with customizable parameters
- Adjustable duty cycle for pulse width modulation
- Real-time waveform visualization with interactive selection
- Audio playback of generated tones and selected segments
- Integration with control windows for further processing

Dependencies:
- numpy: Numerical computations and signal generation
- scipy.signal: Square wave generation function
- sounddevice: Audio playback functionality
- matplotlib: Plotting and visualization
- PyQt5: Graphical user interface components

Author: Matteo Tsikalakis-Reeder
Date: 25/9/2025
Version: 1.0
"""

import matplotlib.pyplot as plt
import numpy as np
import sounddevice as sd
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QLineEdit, QPushButton, 
                            QSlider, QMessageBox, QVBoxLayout, QHBoxLayout, QGridLayout)
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.widgets import SpanSelector
from scipy import signal

class SquareWave(QWidget):
    """
    Square wave generator with interactive visualization and playback.
    
    This class provides functionality for:
    - Generating square waves with fully adjustable parameters
    - Real-time visualization of generated waveforms
    - Interactive audio playback and segment selection
    - Loading generated signals into control windows for processing
    
    Attributes:
        controller: Reference to main application controller
        master: Parent widget reference
        selectedAudio: Currently selected audio segment for playback
        default_values: Dictionary containing default parameter values
        sliders: Dictionary of slider widgets for parameter control
        fig: Matplotlib figure for waveform display
        ax: Matplotlib axes for waveform plotting
        canvas: Figure canvas for embedding in Qt
        toolbar: Navigation toolbar for plot interaction
        span: Span selector for interactive audio segment selection
    """

    def __init__(self, master, controller):
        """
        Initialize the SquareWave generator widget.
        
        Args:
            master: Parent widget
            controller: Main application controller for coordination
        """
        super().__init__(master)
        self.controller = controller
        self.master = master
        self.selectedAudio = np.empty(1)  # Initialize empty audio array
        
        # Default parameter values for square wave generation
        self.default_values = {
            'duration': 0.2,      # Signal duration in seconds
            'amplitude': 0.8,     # Signal amplitude (0-1 scale)
            'fs': 44100,          # Sample rate (Hz)
            'offset': 0.0,        # DC offset
            'frequency': 440,     # Fundamental frequency (Hz)
            'phase': 0.0,         # Phase offset in π radians
            'duty': 0.5           # Duty cycle (0-1, proportion of high state)
        }
        self.sliders = {}  # Store slider widgets for parameter control

        self.setupUI()  # Initialize user interface
        self.plotSquareWave()  # Generate and display initial waveform
        self.setupAudioInteractions()  # Set up audio playback functionality

    def showHelp(self):
        """Show help information for the square wave generator."""
        if hasattr(self, 'help') and self.help:
            self.help.openHelpPage('square_help.html')
        else:
            QMessageBox.information(self, "Help", 
                                   "Square Wave Generator Help\n\n"
                                   "This tool generates a square wave with adjustable parameters:\n"
                                   "- Duration: Length in seconds\n"
                                   "- Amplitude: Volume (0-1)\n"
                                   "- Frequency: Pitch in Hz\n"
                                   "- Phase: Starting point in cycle\n"
                                   "- Duty Cycle: Percentage of active cycle (0-1)\n"
                                   "- Offset: DC offset")

    def setupUI(self):
        """Initialize the user interface with controls and visualization."""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Matplotlib figure setup for waveform visualization
        self.fig = plt.figure(figsize=(8, 4))
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvas(self.fig)
        self.toolbar = NavigationToolbar(self.canvas, self)  # Plot navigation toolbar
        
        main_layout.addWidget(self.toolbar)
        main_layout.addWidget(self.canvas)
        main_layout.addLayout(self.create_controls())  # Add parameter controls
        
        self.setLayout(main_layout)

    def setupAudioInteractions(self):
        """
        Set up interactive audio selection using span selector.
        
        Creates a span selector that allows users to select portions of the
        waveform for audio playback by clicking and dragging on the plot.
        """
        self.span = SpanSelector(
            self.ax,
            self.on_select_region,  # Callback for region selection
            'horizontal',           # Selection direction
            useblit=True,           # Use blitting for performance
            interactive=True,       # Allow interactive adjustment
            drag_from_anywhere=True # Drag from anywhere in span
        )
        self.span.set_active(True)  # Activate the span selector

    def on_select_region(self, xmin, xmax):
        """
        Handle audio segment selection and playback.
        
        When a region is selected on the plot, this method extracts the
        corresponding audio segment and plays it back immediately.
        
        Args:
            xmin: Start time of selected region (seconds)
            xmax: End time of selected region (seconds)
        """
        if len(self.selectedAudio) <= 1:  # Check if audio data is available
            return
            
        fs = self.default_values['fs']  # Get sample rate
        duration = self.sliders['Duration (s)'].value() / 100  # Current duration
        # Create time array for index calculation
        time = np.linspace(0, duration, len(self.selectedAudio), endpoint=False)
        
        # Find array indices corresponding to selected time range
        idx_min = np.argmax(time >= xmin)
        idx_max = np.argmax(time >= xmax)
        
        # Stop any current playback and play the selected segment
        sd.stop()
        sd.play(self.selectedAudio[idx_min:idx_max], fs)

    def create_controls(self):
        """
        Create and arrange the control widgets for parameter adjustment.
        
        Returns:
            QGridLayout: Layout containing all control widgets
        """
        layout = QGridLayout()
        layout.setVerticalSpacing(8)
        layout.setHorizontalSpacing(10)
        
        # Create sliders for all adjustable parameters
        self.sliders['Duration (s)'] = self.create_slider(0.01, 30.0, self.default_values['duration'])
        self.sliders['Offset'] = self.create_slider(-1.0, 1.0, self.default_values['offset'])
        self.sliders['Amplitude'] = self.create_slider(0.0, 1.0, self.default_values['amplitude'])
        self.sliders['Frequency (Hz)'] = self.create_slider(0, 20000, self.default_values['frequency'], is_float=False)
        self.sliders['Phase (π rad)'] = self.create_slider(-1.0, 1.0, self.default_values['phase'])
        self.sliders['Duty Cycle'] = self.create_slider(0.0, 1.0, self.default_values['duty'])
        
        # Add labels and value displays for each slider
        for i, (label, slider) in enumerate(self.sliders.items()):
            layout.addWidget(QLabel(label), i, 0, alignment=Qt.AlignRight)
            layout.addWidget(slider, i, 1, 1, 2)
            layout.addWidget(self.create_value_display(slider, label.endswith('Hz)')), i, 3)
        
        # Create action buttons
        btn_layout = QHBoxLayout()
        
        self.help_button = QPushButton('🛈')
        self.controller_button = QPushButton('Load to Controller')
        self.plot_button = QPushButton('Plot')
        
        self.help_button.setFixedWidth(30)  # Compact help button
        
        btn_layout.addStretch(1)  # Push buttons to the right
        btn_layout.addWidget(self.controller_button)
        btn_layout.addWidget(self.help_button)
        btn_layout.addWidget(self.plot_button)

        # Connect button signals
        self.help_button.clicked.connect(lambda: self.controller.help.createHelpMenu(3))
        self.plot_button.clicked.connect(self.plotSquareWave)
        self.controller_button.clicked.connect(self.load_to_controller)
        
        layout.addLayout(btn_layout, len(self.sliders), 1, 1, 3)
        
        return layout

    def load_to_controller(self):
        """
        Load the generated square wave into a new control window.
        
        This method creates a new ControlMenu instance with the current
        square wave signal, allowing for further processing and analysis.
        Handles both full waveforms and selected segments.
        """
        from core.controlMenu import ControlMenu

        try:
            # Ensure the waveform is freshly generated with current parameters
            self.plotSquareWave()
            
            # Use selected span if valid, otherwise full audio
            audio_to_load = (
                self.selectedAudio if self.selectedAudio.size > 1 else self.selectedAudio
            )
            duration = self.sliders['Duration (s)'].value() / 100
            fs = self.default_values['fs']
            
            # Compose descriptive title from key parameters
            frequency = self.sliders['Frequency (Hz)'].value()
            duty = self.sliders['Duty Cycle'].value() / 100
            title = f"Square Wave {frequency}Hz (Duty: {duty:.2f})"
            
            # Check if controller is properly set up
            if not hasattr(self.controller, 'adse'):
                from PyQt5.QtWidgets import QWidget
                self.controller = QWidget()
                self.controller.adse = type('', (), {})()  # Create dummy object
                self.controller.adse.advancedSettings = lambda: print("Advanced settings not available")
            
            # Create and configure control window
            control_window = ControlMenu(title, fs, audio_to_load, duration, self.controller)
            
            # Track window for proper cleanup
            if not hasattr(self, 'control_windows'):
                self.control_windows = []
            self.control_windows.append(control_window)
            
            # Set up cleanup when window is closed
            control_window.destroyed.connect(
                lambda: self.control_windows.remove(control_window)
                if control_window in self.control_windows else None
            )
            
            # Show and activate the new window
            control_window.show()
            control_window.activateWindow()
            
        except Exception as e:
            print(f"Error loading square wave to controller: {e}")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Could not load to controller: {str(e)}")

    def plotSquareWave(self):
        """
        Generate and plot the square wave with current parameters.
        
        This method:
        - Clears any existing span selector to prevent conflicts
        - Generates the square wave signal using scipy.signal.square
        - Updates the visualization with the new waveform
        - Sets up audio interactions for the new signal
        """
        # Clear any existing span selector first to prevent conflicts
        if hasattr(self, 'span'):
            self.span.clear()
            del self.span
            
        self.ax.clear()  # Clear previous plot
        
        # Get current parameter values from sliders
        duration = self.sliders['Duration (s)'].value() / 100
        amplitude = self.sliders['Amplitude'].value() / 100
        frequency = self.sliders['Frequency (Hz)'].value()
        phase = self.sliders['Phase (π rad)'].value() / 100
        offset = self.sliders['Offset'].value() / 100
        duty = self.sliders['Duty Cycle'].value() / 100
        fs = self.default_values['fs']
        
        # Generate square wave signal
        samples = int(duration * fs)  # Calculate number of samples
        time = np.linspace(0, duration, samples, endpoint=False)
        # Generate square wave using scipy.signal.square
        self.selectedAudio = amplitude * signal.square(2*np.pi*frequency*time + phase*np.pi, duty=duty) + offset
        
        # Plot the generated waveform
        self.ax.plot(time, self.selectedAudio, linewidth=1.5, color='blue')
        self.ax.set(xlim=[0, duration], 
                   ylim=[-1.1, 1.1],  # Fixed y-limits for square waves
                   xlabel='Time (s)', 
                   ylabel='Amplitude')
        self.ax.grid(True, linestyle=':', alpha=0.5)  # Add grid for readability
        
        self.canvas.draw()  # Refresh the display
        self.setupAudioInteractions()  # Re-enable audio interactions

    def reset_to_defaults(self):
        """Reset all parameters to their default values and regenerate waveform."""
        for name, value in self.default_values.items():
            if name == 'frequency':
                self.sliders['Frequency (Hz)'].setValue(value)
            elif name == 'fs':
                continue  # Sample rate not adjustable via slider
            else:
                # Map parameter names to slider names
                slider_name = {
                    'duration': 'Duration (s)',
                    'amplitude': 'Amplitude',
                    'offset': 'Offset',
                    'phase': 'Phase (π rad)',
                    'duty': 'Duty Cycle'
                }.get(name)
                if slider_name:
                    self.sliders[slider_name].setValue(int(value * 100))
        
        self.plotSquareWave()  # Regenerate with default values

    def create_slider(self, min_val, max_val, init_val, is_float=True):
        """
        Create a parameter slider widget.
        
        Args:
            min_val: Minimum value for the parameter
            max_val: Maximum value for the parameter  
            init_val: Initial value for the parameter
            is_float: Whether the parameter is float (scaled by 100) or integer
            
        Returns:
            QSlider: Configured slider widget
        """
        slider = QSlider(Qt.Horizontal)
        # Set range with appropriate scaling for float parameters
        if is_float:
            slider.setRange(int(min_val*100), int(max_val*100))
            slider.setValue(int(init_val*100))
        else:
            slider.setRange(min_val, max_val)
            slider.setValue(init_val)
        slider.valueChanged.connect(self.update_plot)  # Update plot on value change
        return slider

    def create_value_display(self, slider, is_int=False):
        """
        Create a value display and input field for a slider.
        
        Args:
            slider: The slider widget to connect to
            is_int: Whether the value should be displayed as integer
            
        Returns:
            QLineEdit: Configured input field showing current value
        """
        # Calculate initial value with appropriate formatting
        value = slider.value() / 100 if not is_int else slider.value()
        input_field = QLineEdit(f"{value:.2f}" if not is_int else f"{value}")
        input_field.setFixedWidth(50)
        input_field.setAlignment(Qt.AlignCenter)
        # Connect input field to slider update
        input_field.returnPressed.connect(lambda: self.update_slider_from_input(slider, input_field, is_int))
        # Connect slider to input field update
        slider.valueChanged.connect(lambda v: input_field.setText(f"{v/100:.2f}" if not is_int else f"{v}"))
        return input_field

    def update_plot(self):
        """Update the waveform plot when parameters change."""
        self.plotSquareWave()

    def createControlMenu(self):
        """
        Create a control menu for the generated signal.
        
        Note: This method appears to be a legacy version of load_to_controller
        and may not be fully implemented in the current version.
        """
        duration = self.sliders['Duration (s)'].value() / 100
        fs = self.default_values['fs']
        signal = self.selectedAudio
        name = "Square Wave"
        
        self.cm = ControlMenu(name, fs, signal, duration, self.controller)
        self.cm.show()

    def update_slider_from_input(self, slider, input_field, is_int):
        """
        Update slider value from text input field.
        
        Args:
            slider: Slider widget to update
            input_field: Input field containing new value
            is_int: Whether the value should be treated as integer
        """
        try:
            # Parse input value with appropriate type
            value = float(input_field.text()) if not is_int else int(input_field.text())
            # Update slider with appropriate scaling
            slider.setValue(int(value * 100) if not is_int else value)
        except ValueError:
            # Reset to current value if input is invalid
            input_field.setText(f"{slider.value()/100:.2f}" if not is_int else f"{slider.value()}")