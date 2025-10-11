"""
Audio File Loader Module

This module provides a graphical interface for loading, visualizing, and selecting 
portions of audio files. It allows users to open audio files, visualize waveform, 
select specific time segments, and load those segments into control windows for 
further processing in a larger audio application.

Key Features:
- Support for WAV and MP3 audio files
- Interactive waveform visualization with zoom/pan capabilities
- Time segment selection using span selector
- Audio playback of selected segments
- Integration with control windows for advanced audio processing

Dependencies:
- numpy: Numerical computations
- sounddevice: Audio playback
- soundfile: Audio file I/O
- librosa: Audio analysis and processing
- PyQt5: Graphical user interface
- matplotlib: Plotting and visualization


Author: Matteo Tsikalakis-Reeder
Date: 25/09/2025
Version: 1.0
"""

import numpy as np
import sounddevice as sd
import soundfile as sf
import librosa
import struct
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QPushButton, 
                            QVBoxLayout, QHBoxLayout, QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.widgets import SpanSelector, Button
from matplotlib.figure import Figure

import sys
import os

# Maximum number of control windows that can be open simultaneously
MAX_WINDOWS = 5

class Load(QWidget):
    """
    Main widget for loading and visualizing audio files.
    
    This class provides functionality for:
    - Loading audio files from disk
    - Visualizing audio waveforms
    - Selecting time segments interactively
    - Playing back audio segments
    - Loading segments into control windows for processing
    
    Attributes:
        controller: Reference to main application controller
        master: Parent widget
        selectedAudio: Currently selected audio segment as numpy array
        fs: Sample rate of loaded audio (default: 44100 Hz)
        file_path: Path to the currently loaded audio file
        control_windows: List tracking all open control windows
        selected_span: Tuple storing the start and end time of selected segment
    """
    
    def __init__(self, master, controller):
        """
        Initialize the Load widget.
        
        Args:
            master: Parent widget
            controller: Main application controller for coordination between components
        """
        super().__init__(master)
        self.controller = controller
        self.master = master
        self.selectedAudio = np.empty(1)  # Initialize empty audio array
        self.fs = 44100  # Default sample rate
        self.file_path = ""  # No file loaded initially

        self.control_windows = []  # List to track all open control windows
        self.selected_span = (0, 0)  # Track selected time span (start, end)
        
        self.controller = controller  # Reference to main controller

        self.setupUI()  # Initialize the user interface
        
    def setupUI(self):
        """Set up the user interface with buttons, plot area, and controls."""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)  # Add margins around the layout
        
        # Create control row for buttons
        control_row = QHBoxLayout()
        control_row.setContentsMargins(0, 0, 0, 0)
        control_row.setSpacing(10)
        
        # Create open file button (slightly bigger)
        self.open_button = QPushButton('Open Audio File')
        self.open_button.setFont(QFont("Arial", 16, QFont.Bold))  # Bigger font, bold
        self.open_button.setFixedHeight(45)  # Slightly taller
        self.open_button.setMinimumWidth(200)  # Wider button
        self.open_button.clicked.connect(self.loadAudio)
        self.open_button.setStyleSheet("""
            QPushButton {
                background-color: #4477ff;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #6699ff;
            }
            QPushButton:pressed {
                background-color: #3355cc;
            }
        """)
        
        # Create help button (slightly smaller)
        self.help_button = QPushButton("🛈 Help")
        self.help_button.setFont(QFont("Arial", 14))  # Slightly smaller font
        self.help_button.setFixedWidth(100)  # Smaller width
        self.help_button.setFixedHeight(35)  # Smaller height
        self.help_button.clicked.connect(lambda: self.controller.help.createHelpMenu(6))
        self.help_button.setStyleSheet("""
            QPushButton {
                background-color: #555555;
                color: white;
                border: none;
                padding: 8px 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #777777;
            }
            QPushButton:pressed {
                background-color: #333333;
            }
        """)
        
        # Add buttons to control row
        control_row.addWidget(self.open_button)
        control_row.addWidget(self.help_button)
        control_row.addStretch()  # Push buttons to left, empty space to right
        
        # Figure setup for waveform visualization
        self.fig = Figure(figsize=(8, 4))
        self.ax = self.fig.add_subplot(111)  # Single subplot for audio waveform
        self.canvas = FigureCanvas(self.fig)  # Canvas for embedding matplotlib in Qt
        self.toolbar = NavigationToolbar(self.canvas, self)  # Toolbar for plot navigation
        
        # Add widgets to layout
        main_layout.addLayout(control_row)
        main_layout.addWidget(self.toolbar)
        main_layout.addWidget(self.canvas)
        
        self.setLayout(main_layout)  # Apply the layout to this widget
        
    def loadAudio(self):
        """
        Load an audio file from disk and prepare it for visualization.
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
        
        library_dir = base_dir / "library"
        
        # Create library directory if it doesn't exist
        if not library_dir.exists():
            try:
                library_dir.mkdir(parents=True, exist_ok=True)
                QMessageBox.information(
                    self,
                    "Library Directory Created",
                    f"The 'library' directory was created at:\n{library_dir}"
                )
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "Directory Creation Failed",
                    f"Could not create library directory: {str(e)}\nUsing current directory instead."
                )
                library_dir = Path.cwd()  # Fallback to current working directory
        
        # Ensure we have a valid directory
        if not library_dir.exists():
            library_dir = Path.home() / "Documents"  # Ultimate fallback
        
        # Open file dialog
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Open Audio File", 
            str(library_dir),
            "Audio Files (*.wav *.mp3);;WAV Files (*.wav);;MP3 Files (*.mp3);;All Files (*)"
        )
        
        if not file_path:
            return
            
        self.file_path = file_path
        
        try:
            audio, self.fs = librosa.load(file_path, sr=None, mono=False)
            
            if audio.ndim > 1:
                QMessageBox.warning(
                    self, 
                    "Stereo File", 
                    "This file is in stereo mode. It will be converted to mono."
                )
                ampMax = np.max(np.abs(audio))
                audio = np.mean(audio, axis=0)
                audio = audio * ampMax / np.max(np.abs(audio))
            
            self.plotAudio(audio)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load file: {str(e)}")

    def plotAudio(self, audio):
        """
        Plot the audio waveform and set up interactive controls.
        
        Args:
            audio: numpy array containing the audio data to visualize
        """
        self.ax.clear()  # Clear previous plot

        # Reset selected span when loading new audio
        self.selected_span = None
        self.selectedAudio = np.empty(1)  # Reset selected audio
        
        # Calculate time array for x-axis
        duration = librosa.get_duration(filename=self.file_path)
        time = np.linspace(0, duration, len(audio), endpoint=False)
        
        # Plot the audio waveform
        self.ax.plot(time, audio, linewidth=1)
        self.ax.axhline(y=0, color='black', linewidth=0.5, linestyle='--')  # Zero reference line
        self.ax.set(
            xlim=[0, duration],  # Set x-axis limits to full duration
            xlabel='Time (s)',
            ylabel='Amplitude',
            title=Path(self.file_path).stem  # Use filename without extension as title
        )
        self.ax.grid(True, linestyle=':', alpha=0.5)  # Add grid lines
        
        # Add load button to the plot
        self.addLoadButton()
        
        # Setup span selector for interactive audio selection
        self.setupSpanSelector(time, audio)
        
        self.canvas.draw()  # Refresh the canvas to show new plot
        
    def setupSpanSelector(self, time, audio):
        """
        Set up the span selector for interactive time segment selection.
        
        Args:
            time: numpy array of time values for x-axis
            audio: numpy array of audio data for y-axis
        """
        # Remove existing span selector if it exists
        if hasattr(self, 'span'):
            self.span.disconnect_events()
            del self.span
            
        def on_select(xmin, xmax):
            """
            Callback function called when a time span is selected.
            
            Args:
                xmin: Start time of selected span (seconds)
                xmax: End time of selected span (seconds)
            """
            if len(audio) <= 1:  # Skip if no audio data
                return
                
            # Convert time values to sample indices
            idx_min = np.argmax(time >= xmin)
            idx_max = np.argmax(time >= xmax)
            self.selectedAudio = audio[idx_min:idx_max]  # Extract selected audio segment
            self.selected_span = (xmin, xmax)  # Store the selected time span
            sd.play(self.selectedAudio, self.fs)  # Play the selected segment
            
        # Create span selector widget
        self.span = SpanSelector(
            self.ax,
            on_select,  # Callback function
            'horizontal',  # Selection direction
            useblit=True,  # Use blitting for better performance
            interactive=True,  # Allow dragging selection handles
            drag_from_anywhere=True  # Can drag from anywhere in the span
        )

    def format_timestamp(self, seconds):
        """
        Convert seconds to mm:ss.xxx format for display.
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted timestamp string (mm:ss.xxx)
        """
        minutes = int(seconds // 60)
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:06.3f}"[:8]  # Truncate to mm:ss.xx format

    def addLoadButton(self):
        """Add load and stop buttons to the plot interface."""
        # Remove existing buttons if they exist
        if hasattr(self, 'load_button_ax'):
            self.fig.delaxes(self.load_button_ax)
        if hasattr(self, 'stop_button_ax'):
            self.fig.delaxes(self.stop_button_ax)
            
        # Create button axes for both buttons (position: [left, bottom, width, height])
        self.stop_button_ax = self.fig.add_axes([0.65, 0.01, 0.12, 0.05])
        self.load_button_ax = self.fig.add_axes([0.8, 0.01, 0.15, 0.05])
        
        # Create Stop Audio button
        self.stop_button = Button(self.stop_button_ax, 'Stop Audio')
        self.stop_button.on_clicked(lambda event: sd.stop())  # Stop audio playback
        
        # Create Load to Controller button
        self.load_button = Button(self.load_button_ax, 'Load to Controller')
        
        def on_load(event):
            """
            Callback function for loading selected audio to control window.
            
            This function:
            - Checks if maximum window limit is reached
            - Determines whether to load selected segment or entire file
            - Creates a new control window with the audio data
            - Updates the windows tracking list
            - Handles window closure cleanup
            """
            from core.controlMenu import ControlMenu  # Import here to avoid circular imports

            # Manage maximum number of open windows
            if len(self.control_windows) >= MAX_WINDOWS:
                oldest = self.control_windows.pop(0)  # Remove oldest window
                oldest.close()  # Close the window
                
            # Determine which audio to load (selected segment or entire file)
            if self.selectedAudio.shape == (1,):  # No selection made, use entire audio
                audio_to_load = self.ax.lines[0].get_ydata()  # Get all audio data from plot
                duration = len(audio_to_load) / self.fs  # Calculate duration
                start_time = 0
                end_time = duration
            else:  # Use selected segment
                audio_to_load = self.selectedAudio
                duration = len(audio_to_load) / self.fs
                start_time, end_time = self.selected_span
                
            # Create window title with appropriate information
            name = Path(self.file_path).stem  # Filename without extension
            if self.selectedAudio.shape != (1,):  # Only show span if selection was made
                title = f"{name} {self.format_timestamp(start_time)}-{self.format_timestamp(end_time)}"
            else:
                title = name  # Just use filename for entire file
                
            # Create new control window with the audio data
            control_window = ControlMenu(title, self.fs, audio_to_load, duration, self.controller)
            
            # Update windows menu in controller if available
            if hasattr(self.controller, 'update_windows_menu'):
                self.controller.update_windows_menu()
                
            # Store the title early since windowTitle() may fail later during cleanup
            window_title = control_window.windowTitle()
            
            def handle_close():
                """
                Cleanup function called when control window is closed.
                
                Removes the window from tracking list and performs cleanup.
                """
                try:
                    # Check if window still exists in the list
                    if control_window in self.control_windows:
                        self.control_windows.remove(control_window)
                        print(f"Removed window: '{window_title}'. Total windows: {len(self.control_windows)}")
                        # Print all remaining windows for debugging
                        print("Current windows:", [w.base_name for w in self.control_windows])
                    else:
                        print(f"Window '{window_title}' not found in control_windows list")
                except RuntimeError:
                    # This catches cases where the window is partially destroyed
                    print(f"Window '{window_title}' already destroyed during cleanup")
                
            # Connect the destroyed signal to cleanup function
            control_window.destroyed.connect(handle_close)
            
            # Add new window to tracking list
            self.control_windows.append(control_window)
            print(f"Added window: '{control_window.windowTitle()}'. Total windows: {len(self.control_windows)}")
            print("All windows:", [w.base_name for w in self.control_windows])            
            
            control_window.show()  # Make window visible
            control_window.activateWindow()  # Bring window to front

        # Connect the load button to the callback function
        self.load_button.on_clicked(on_load)
        
    def showHelp(self):
        """Display help information about using the audio loader."""
        QMessageBox.information(
            self, 
            "Help", 
            "Audio File Loader Help\n\n"
            "1. Click 'Open Audio File' to browse for a WAV file\n"
            "2. Select a portion of the audio with your mouse to play just that section\n"
            "3. Click 'Load to Controller' to send the audio to the control menu\n"
            "   - If no selection is made, the entire file will be loaded"
        )