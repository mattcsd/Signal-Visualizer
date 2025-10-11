"""
Pure Tone Generator Module

This module provides a dialog interface for generating pure sine wave tones with
mathematical visualization and interactive controls. It allows users to create
custom audio tones with adjustable parameters and load them into the main application.

Key Features:
- Mathematical expression display of the generated tone
- Real-time waveform visualization
- Interactive parameter adjustment via sliders
- Audio playback of generated tones and selected segments
- Integration with control windows for further processing

Dependencies:
- matplotlib: Plotting and visualization
- numpy: Numerical computations and signal generation
- sounddevice: Audio playback functionality
- PyQt5: Graphical user interface components


Author: Matteo Tsikalakis-Reeder
Date: 25/09/2025
Version: 1.0
"""

import numpy as np
import sounddevice as sd
from PyQt5.QtWidgets import (
    QDialog, QLabel, QPushButton, QGridLayout, QSlider, 
    QMessageBox, QVBoxLayout, QHBoxLayout
)
import matplotlib.pyplot as plt
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.widgets import SpanSelector

from misc.help import Help  # Custom help system


class PureTone(QDialog):
    """
    Pure tone generator dialog with mathematical visualization.
    
    This class provides functionality for:
    - Generating pure sine waves with customizable parameters
    - Displaying mathematical expressions of the generated signals
    - Visualizing waveforms in real-time as parameters change
    - Playing back generated tones and selected segments
    - Loading tones into control windows for further processing
    
    Attributes:
        controller: Reference to main application controller
        selectedAudio: Generated audio data as numpy array
        default_values: Dictionary of default parameter values
        sliders: Dictionary mapping parameter names to slider widgets
    """
    
    def __init__(self, controller, parent=None):
        """
        Initialize the PureTone dialog.
        
        Args:
            controller: Main application controller for coordination
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        self.controller = controller
        self.selectedAudio = np.empty(1)  # Initialize empty audio array
        
        # Default parameter values for the pure tone
        self.default_values = {
            'duration': 0.2,    # Duration in seconds
            'amplitude': 0.5,   # Amplitude (0-1)
            'fs': 44100,        # Sample rate (Hz)
            'offset': 0.0,      # DC offset
            'frequency': 440,   # Frequency (Hz) - A4 note
            'phase': 0.0        # Phase in π radians
        }
        self.sliders = {}  # Dictionary to store slider widgets
        
        self.setupUI()  # Initialize the user interface
        self.plotPureTone()  # Generate and display initial tone
        self.setupAudioInteractions()  # Initialize audio playback functionality
        self.help = Help(self)  # Initialize help system

    def showHelp(self):
        """
        Display help information for the pure tone generator.
        
        Shows either the custom help system or a fallback message box.
        """
        print("Help button clicked")  # Debug output
        if hasattr(self, 'help') and self.help:
            print("Help system available")  # Debug output
            self.help.createHelpMenu(1)  # Show help page 1 (Pure Tone)
        else:
            print("Help system not available")  # Debug output
            # Fallback help message
            QMessageBox.information(self, "Help", 
                                   "Pure Tone Generator Help\n\n"
                                   "This tool generates a pure sine wave with adjustable parameters:\n"
                                   "- Duration: Length of the tone in seconds\n"
                                   "- Amplitude: Volume of the tone (0-1)\n"
                                   "- Frequency: Pitch of the tone in Hz\n"
                                   "- Phase: Starting point in the wave cycle\n"
                                   "- Offset: DC offset of the signal")

    def setupUI(self):
        """Set up the user interface with mathematical display, plot, and controls."""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)  # Add margins
        
        # Mathematical expression display with styling
        self.math_display = QLabel()
        self.math_display.setAlignment(Qt.AlignCenter)
        self.math_display.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-family: "Times New Roman", serif;  /* Fallback for Cambria */
                color: #0066cc;
                background-color: #f0f8ff;
                border: 1px solid #c0c0c0;
                border-radius: 5px;
                padding: 10px;
                margin-bottom: 15px;
            }
        """)
        main_layout.addWidget(self.math_display)
        
        # Figure setup for waveform visualization
        self.fig = plt.figure(figsize=(8, 4))
        self.ax = self.fig.add_subplot(111)  # Single subplot for waveform
        self.canvas = FigureCanvas(self.fig)  # Canvas for embedding matplotlib in Qt
        self.toolbar = NavigationToolbar(self.canvas, self)  # Plot navigation toolbar
        
        # Add widgets to main layout
        main_layout.addWidget(self.toolbar)
        main_layout.addWidget(self.canvas)
        main_layout.addLayout(self.create_controls())  # Add parameter controls
        
        self.setLayout(main_layout)
        self.update_expression()  # Initialize mathematical expression display

    def setupAudioInteractions(self):
        """
        Setup audio playback interactions including span selection.
        
        Initializes the span selector for interactive segment playback
        and ensures it remains active after plot updates.
        """
        # Region selection for interactive audio playback
        self.span = SpanSelector(
            self.ax,
            self.on_select_region,  # Callback function
            'horizontal',  # Selection direction
            useblit=True,  # Use blitting for performance
            interactive=True,  # Allow interactive adjustment
            drag_from_anywhere=True  # Drag from anywhere in span
        )
        
        # Ensure the span selector stays active
        self.span.set_active(True)

    def on_select_region(self, xmin, xmax):
        """
        Play the selected region of the generated tone.
        
        Args:
            xmin: Start time of selected region (seconds)
            xmax: End time of selected region (seconds)
        """
        if len(self.selectedAudio) <= 1:  # Check if audio has been generated
            return
            
        fs = self.default_values['fs']  # Get sample rate
        duration = self.sliders['Duration (s)'].value() / 100  # Get current duration
        # Create time array matching the audio data
        time = np.linspace(0, duration, len(self.selectedAudio), endpoint=False)
        
        # Find indices corresponding to selected time range
        idx_min = np.argmax(time >= xmin)
        idx_max = np.argmax(time >= xmax)
        
        # Stop any current playback and play the selected segment
        sd.stop()
        sd.play(self.selectedAudio[idx_min:idx_max], fs)

    def create_controls(self):
        """
        Create and arrange the control widgets (sliders and buttons).
        
        Returns:
            QGridLayout containing all control elements
        """
        layout = QGridLayout()
        layout.setVerticalSpacing(8)   # Vertical spacing between rows
        layout.setHorizontalSpacing(10)  # Horizontal spacing between columns
        
        # Create and store sliders for each parameter
        self.sliders['Duration (s)'] = self.create_slider(0.01, 30.0, self.default_values['duration'])
        self.sliders['Offset'] = self.create_slider(-1.0, 1.0, self.default_values['offset'])
        self.sliders['Amplitude'] = self.create_slider(0.0, 1.0, self.default_values['amplitude'])
        self.sliders['Frequency (Hz)'] = self.create_slider(0, 20000, self.default_values['frequency'], is_float=False)
        self.sliders['Phase (π rad)'] = self.create_slider(-1.0, 1.0, self.default_values['phase'])
        
        # Add sliders and their labels to the layout
        for i, (label, slider) in enumerate(self.sliders.items()):
            layout.addWidget(QLabel(label), i, 0, alignment=Qt.AlignRight)  # Parameter label
            layout.addWidget(slider, i, 1, 1, 2)  # Slider widget
            # Value display (integer for frequency, float for others)
            layout.addWidget(self.create_value_display(slider, label.endswith('Hz)')), i, 3)
        
        # Button layout at the bottom
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(QPushButton('Save', clicked=self.saveDefaults))
        btn_layout.addWidget(QPushButton('Load to Controller', clicked=self.load_to_controller))
        btn_layout.addStretch(1)  # Flexible space
        btn_layout.addWidget(QPushButton('Default Values', clicked=self.reset_to_defaults))
        btn_layout.addWidget(QPushButton('🛈 Help', clicked=self.showHelp))
        
        # Add button layout to the main grid
        layout.addLayout(btn_layout, len(self.sliders), 1, 1, 3)
        
        return layout

    def load_to_controller(self):
        """
        Load the generated pure tone into a new control window.
        
        This method:
        - Ensures the latest audio data is generated
        - Creates a control window with the tone
        - Handles integration with the main controller
        - Manages window lifecycle and cleanup
        """
        from core.controlMenu import ControlMenu  # Import here to avoid circular imports

        try:
            # First ensure we have the latest audio data
            self.plotPureTone()
            
            # Get parameters for the tone
            duration = self.sliders['Duration (s)'].value() / 100
            fs = self.default_values['fs']
            audio_to_load = self.selectedAudio  # The generated audio data
            
            # Create window title with parameters
            params = {
                'freq': self.sliders['Frequency (Hz)'].value(),
                'amp': self.sliders['Amplitude'].value() / 100,
                'phase': self.sliders['Phase (π rad)'].value() / 100,
                'offset': self.sliders['Offset'].value() / 100
            }
            title = f"Pure Tone {params['freq']}Hz"  # Title with frequency
            
            # Create a minimal controller if the main controller isn't properly set up
            if not hasattr(self.controller, 'adse'):
                from PyQt5.QtWidgets import QWidget
                self.controller = QWidget()  # Create a minimal controller
                self.controller.adse = type('', (), {})()  # Create a dummy adse object
                self.controller.adse.advancedSettings = lambda: print("Advanced settings not available")
            
            # Create new control window with the generated tone
            control_window = ControlMenu(title, fs, audio_to_load, duration, self.controller)
            
            # Store reference to the control window for management
            if not hasattr(self, 'control_windows'):
                self.control_windows = []
            self.control_windows.append(control_window)
            
            # Cleanup handler when window is closed
            def cleanup():
                if control_window in self.control_windows:
                    self.control_windows.remove(control_window)
            
            control_window.destroyed.connect(cleanup)
            
            # Show and activate the new window
            control_window.show()
            control_window.activateWindow()
        
        except Exception as e:
            print(f"Error loading to controller: {e}")
            # Show error message to user
            QMessageBox.critical(self, "Error", f"Could not load to controller: {str(e)}")
        

    def update_expression(self):
        """
        Update the mathematical expression display based on current parameters.
        
        Formats and displays the equation: y(t) = offset + amplitude·cos(2π·frequency·t + phase·π)
        with colored parameters for better visualization.
        """
        if not hasattr(self, 'sliders') or not self.sliders:
            return  # Safety check if sliders aren't initialized
            
        pi = "π"  # Unicode pi symbol
        # Create formatted mathematical expression with colored parameters
        expression = (
            f"<div style='text-align: center;'>"
            f"<span style='font-size: 22px;'>y(t) = {self.sliders['Offset'].value()/100:.2f} + </span>"
            f"<span style='font-size: 24px; color: #d63333;'>{self.sliders['Amplitude'].value()/100:.2f}</span>"  # Red for amplitude
            f"<span style='font-size: 22px;'>·cos( 2{pi}·</span>"
            f"<span style='font-size: 24px; color: #338033;'>{self.sliders['Frequency (Hz)'].value()}</span>"  # Green for frequency
            f"<span style='font-size: 22px;'>·t + </span>"
            f"<span style='font-size: 24px; color: #9933cc;'>{self.sliders['Phase (π rad)'].value()/100:.2f}{pi} )</span>"  # Purple for phase
            f"</div>"
        )
        self.math_display.setText(expression)  # Update the display

    def plotPureTone(self):
        """
        Generate and plot the pure tone based on current parameter values.
        
        This method:
        - Retrieves current parameter values from sliders
        - Generates the sine wave signal
        - Updates the waveform plot
        - Maintains interactive functionality
        """
        self.ax.clear()  # Clear previous plot
        
        # Get current parameter values from sliders
        duration = self.sliders['Duration (s)'].value() / 100  # Convert from slider units
        amplitude = self.sliders['Amplitude'].value() / 100
        frequency = self.sliders['Frequency (Hz)'].value()  # Integer value
        phase = self.sliders['Phase (π rad)'].value() / 100  # Phase in π radians
        offset = self.sliders['Offset'].value() / 100
        fs = self.default_values['fs']  # Fixed sample rate
        
        # Generate the sine wave signal
        samples = int(duration * fs)  # Calculate number of samples
        time = np.linspace(0, duration, samples, endpoint=False)  # Time array
        # Generate the tone: y(t) = A·cos(2πft + φ) + offset
        self.selectedAudio = amplitude * np.cos(2*np.pi*frequency*time + phase*np.pi) + offset
        
        # Plot the generated waveform
        self.ax.plot(time, self.selectedAudio, linewidth=1.5, color='blue')
        self.ax.set(xlim=[0, duration], 
                   ylim=[-1.1, 1.1],  # Fixed y-limits for normalized audio
                   xlabel='Time (s)', 
                   ylabel='Amplitude')
        self.ax.grid(True, linestyle=':', alpha=0.5)  # Add grid lines
        
        # Redraw canvas and update mathematical expression
        self.canvas.draw()
        self.update_expression()
        
        # Reinitialize span selector after plot update to maintain functionality
        self.setupAudioInteractions()

    def reset_to_defaults(self):
        """Reset all controls to their default values."""
        # Reset each slider to its default value
        self.sliders['Duration (s)'].setValue(int(self.default_values['duration'] * 100))
        self.sliders['Offset'].setValue(int(self.default_values['offset'] * 100))
        self.sliders['Amplitude'].setValue(int(self.default_values['amplitude'] * 100))
        self.sliders['Frequency (Hz)'].setValue(self.default_values['frequency'])
        self.sliders['Phase (π rad)'].setValue(int(self.default_values['phase'] * 100))
        
        # Update the display values for each slider
        for label, slider in self.sliders.items():
            display = slider.property('display_widget')
            if display:
                if label.endswith('Hz)'):  # Frequency is integer
                    display.setText(str(slider.value()))
                else:  # Other parameters are floats
                    display.setText(f"{slider.value()/100:.2f}")

        self.update_expression()  # Update mathematical display
        
        # Regenerate and plot the tone with default parameters
        self.plotPureTone()

    def create_slider(self, min_val, max_val, init_val, is_float=True):
        """
        Create a slider widget for parameter adjustment.
        
        Args:
            min_val: Minimum value for the parameter
            max_val: Maximum value for the parameter
            init_val: Initial value for the parameter
            is_float: Whether the parameter is float (scaled by 100) or integer
            
        Returns:
            QSlider configured for the specified parameter
        """
        slider = QSlider(Qt.Horizontal)
        # Set range (scaled by 100 for float parameters for finer control)
        if is_float:
            slider.setRange(int(min_val*100), int(max_val*100))
            slider.setValue(int(init_val*100))
        else:
            slider.setRange(min_val, max_val)
            slider.setValue(init_val)
            
        # Connect value change to plot update
        slider.valueChanged.connect(self.update_plot)
        return slider

    def create_value_display(self, slider, is_int=False):
        """
        Create a label to display the current value of a slider.
        
        Args:
            slider: The slider widget to monitor
            is_int: Whether to display as integer or float
            
        Returns:
            QLabel that updates with the slider value
        """
        # Get initial value (scaled for float parameters)
        value = slider.value() if is_int else slider.value() / 100
        # Create label with appropriate formatting
        label = QLabel(f"{value}" if is_int else f"{value:.2f}")
        
        # Connect slider value changes to label updates
        def update_label(value):
            if is_int:
                label.setText(f"{value}")
            else:
                label.setText(f"{value/100:.2f}")
                
        slider.valueChanged.connect(update_label)
        
        # Store reference to display widget for later access
        slider.setProperty('display_widget', label)
        return label

    def update_plot(self):
        """
        Update the plot when any slider value changes.
        
        This is connected to all sliders' valueChanged signals
        to provide real-time visualization updates.
        """
        self.plotPureTone()

    def saveDefaults(self):
        """
        Save current settings as new defaults.
        
        Note: This method needs implementation to persist settings.
        Currently serves as a placeholder for future functionality.
        """
        # TODO: Implement settings persistence
        pass