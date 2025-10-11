"""
Free Addition of Pure Tones Module

This module provides a dialog interface for generating complex tones by adding
multiple pure sine waves together. It features harmonic generation from piano
inputs and interactive audio visualization.

Key Features:
- Combine up to 6 pure tones with adjustable frequencies and amplitudes
- Piano keyboard interface for harmonic frequency generation
- Real-time waveform visualization with interactive selection
- Audio playback of generated tones and selected segments
- Integration with control windows for further processing

Dependencies:
- numpy: Numerical computations and signal generation
- sounddevice: Audio playback functionality
- matplotlib: Plotting and visualization
- PyQt5: Graphical user interface components
- queue: Audio playback queue for smooth, non-blocking playback
- threading: Background thread for audio playback


Author: Matteo Tsikalakis-Reeder
Date: 25/09/2025
Version: 1.0
"""

import sys
import numpy as np
import sounddevice as sd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.widgets import SpanSelector, Button

from PyQt5.QtWidgets import (
    QApplication, QDialog, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QSlider, QSpinBox, QPushButton, QGroupBox,  # Added QGroupBox here
    QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

from queue import Queue
import threading

from misc.help import Help  # Custom help system

class FreeAdditionPureTones(QDialog):
    """
    Free addition of pure tones generator with piano interface.
    
    This class provides functionality for:
    - Combining multiple pure sine waves with customizable parameters
    - Piano keyboard interface for generating harmonic frequencies
    - Real-time visualization of composite waveforms
    - Interactive audio playback and segment selection
    - Loading composite tones into control windows for processing
    
    Attributes:
        controller: Reference to main application controller
        fs: Sample rate for audio generation (48 kHz)
        selectedAudio: Currently selected audio segment
        help: Help system instance
        piano: Reference to piano dialog window
        amp_sliders: List of amplitude slider widgets
        freq_spinboxes: List of frequency spinbox widgets
        full_audio: Complete generated audio signal
        audio_duration: Duration of generated audio in seconds
    """

    def __init__(self, controller, parent=None):
        """
        Initialize the FreeAdditionPureTones dialog.
        
        Args:
            controller: Main application controller for coordination
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        self.controller = controller
        self.fs = 48000  # High sample frequency for better audio quality
        # Configure sounddevice defaults for optimal performance
        sd.default.samplerate = self.fs
        sd.default.blocksize = 1024  # Optimal for responsiveness
        sd.default.latency = 'low'  # Low latency playback
        self.selectedAudio = np.empty(1)  # Initialize empty audio array

        self.help = Help(self)  # Initialize help system like in PureTone

        self.piano = None  # Initialize piano reference
        self.pianoOpen = False  # Track piano window state
        self.amp_sliders = []  # Store amplitude sliders
        self.freq_spinboxes = []  # Store frequency spinboxes

        # Initialize audio storage
        self.full_audio = np.empty(1)  # Will store the complete generated audio
        self.selectedAudio = np.empty(1)  # Will store selected portions
        self.audio_duration = 0.0  # Duration of generated audio
        
        # Default values for tone parameters
        self.default_values = [
            'Free addition of pure tones',  # Title
            'duration', '0.3',              # Duration in seconds
            'octave', '4',                  # Default octave
            # Frequencies for 6 tones (Hz)
            'freq1', '440', 'freq2', '880', 'freq3', '1320',
            'freq4', '1760', 'freq5', '2200', 'freq6', '2640',
            # Amplitudes for 6 tones (0-1 scale)
            'amp1', '1.0', 'amp2', '0.83', 'amp3', '0.67',
            'amp4', '0.5', 'amp5', '0.33', 'amp6', '0.17'
        ]
        
        # Audio playback queue for smooth, non-blocking playback
        self.audio_queue = Queue()
        # Background thread for audio playback
        self.audio_thread = threading.Thread(target=self._audio_worker, daemon=True)
        self.audio_thread.start()

        '''
        # Load from CSV or use defaults (commented out - placeholder for future functionality)
        try:
            csv_data = self.aux.readFromCsv()
            if len(csv_data) > 4 and len(csv_data[4]) >= 28:
                self.default_values = csv_data[4]
        except Exception as e:
            print(f"Error loading defaults: {e}")
        '''
        
        self.initUI()  # Initialize user interface
        self.plotFAPT()  # Generate and display initial composite tone

    def initUI(self):
        """Initialize the user interface with controls and visualization."""
        # Main layout with minimal margins
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Control panel group box
        control_panel = QGroupBox("Tone Controls")
        control_layout = QGridLayout()
        control_panel.setLayout(control_layout)
        
        # Create controls for 6 tones (frequencies and amplitudes)
        for i in range(6):
            # Frequency controls
            control_layout.addWidget(QLabel(f"Frq{i+1}"), 0, i*2)  # Frequency label
            sb = QSpinBox()
            sb.setRange(0, 24000)  # Frequency range: 0-24 kHz
            int_dval = int(self.default_values[6+i*2])  # Get default value
            sb.setValue(int_dval)
            sb.setMaximumWidth(70)  # Reduced from 80 for compact layout
            self.freq_spinboxes.append(sb)  # Store reference
            control_layout.addWidget(sb, 1, i*2)  # Add to layout
            
            # Amplitude controls - made more compact
            control_layout.addWidget(QLabel(f"Amp{i+1}"), 0, i*2+1)  # Amplitude label
            slider = QSlider(Qt.Horizontal)
            slider.setRange(0, 100)  # 0-100 for 0.00-1.00 range
            slider.setValue(int(float(self.default_values[18+i*2]) * 100))  # Set default
            slider.setMaximumWidth(70)  # Reduced from 100 for compact layout
            self.amp_sliders.append(slider)  # Store reference
            control_layout.addWidget(slider, 1, i*2+1)  # Add to layout
            
            # Value display label for amplitude
            value_label = QLabel(f"{slider.value()/100:.2f}")  # Format as 0.00
            value_label.setAlignment(Qt.AlignCenter)
            value_label.setMaximumWidth(30)  # Reduced from 40
            # Connect slider changes to label updates
            slider.valueChanged.connect(lambda v, lbl=value_label: lbl.setText(f"{v/100:.2f}"))
            control_layout.addWidget(value_label, 2, i*2+1)  # Add below slider

        # Duration control row
        dur_layout = QHBoxLayout()
        dur_layout.addWidget(QLabel('Duration (s):'))
        
        # Duration slider
        self.dur_slider = QSlider(Qt.Horizontal)
        self.dur_slider.setRange(1, 3000)  # 0.01s to 30.00s (scaled by 100)
        self.dur_slider.setValue(int(float(self.default_values[2]) * 100))  # Set default
        dur_layout.addWidget(self.dur_slider)
        
        # Duration spinbox for precise input
        self.dur_spinbox = QSpinBox()
        self.dur_spinbox.setRange(1, 3000)  # Same range as slider
        self.dur_spinbox.setValue(int(float(self.default_values[2]) * 100))  # Set default
        self.dur_spinbox.setMaximumWidth(70)  # Reduced from 80
        dur_layout.addWidget(self.dur_spinbox)
        
        # Button layout
        btn_layout = QHBoxLayout()
        buttons = [
            ('Plot', self.plotFAPT),      # Regenerate and plot
            ('Piano', self.togglePiano),  # Toggle piano keyboard
            #('Save', self.saveDefaultValues),  # Placeholder for future functionality
            ('🛈 Help', self.showHelp)    # Show help
        ]
        
        # Create and configure buttons
        for text, callback in buttons:
            btn = QPushButton(text)
            btn.clicked.connect(callback)
            btn.setMaximumWidth(90 if text == 'Load to Controller' else 70)  # Reduced widths
            btn_layout.addWidget(btn)
            if text == 'Piano':  # Store reference to piano button for state management
                self.piano_btn = btn
        
        # Add components to main layout with stretch factors
        main_layout.addWidget(control_panel, 0)  # Fixed height
        main_layout.addLayout(dur_layout, 0)     # Fixed height  
        main_layout.addLayout(btn_layout, 0)     # Fixed height
        
        # Matplotlib figure for waveform visualization
        self.fig, self.ax = plt.subplots(figsize=(10, 6))  # Increased from (8, 4)
        self.canvas = FigureCanvas(self.fig)
        self.toolbar = NavigationToolbar(self.canvas, self)  # Plot navigation
        
        main_layout.addWidget(self.toolbar, 0)   # Fixed height
        main_layout.addWidget(self.canvas, 1)    # Expandable area
        
        # Set stretch factors to give more space to the plot
        main_layout.setStretchFactor(self.canvas, 10)  # Higher value gives more space
        
        self.setLayout(main_layout)
        
    def showHelp(self):
        """Show help window for this module."""
        if hasattr(self, 'help') and self.help:
            try:
                # Help ID 2 corresponds to "Addition of tones" help
                self.help.createHelpMenu(2)  
            except Exception as e:
                QMessageBox.warning(self, "Help Error", 
                                   f"Could not open help: {str(e)}")
        else:
            # Fallback help message
            QMessageBox.information(self, "Help", 
                                   "Addition of Pure Tones Help\n\n"
                                   "This module lets you combine up to 6 pure tones.\n"
                                   "- Set frequencies (Hz) for each tone\n"
                                   "- Adjust amplitudes (0-1)\n"
                                   "- Control total duration\n"
                                   "- Use piano keyboard to set harmonic frequencies")

    def on_close(self):
        """Clean up resources when window closes."""
        if self.pianoOpen:
            self.piano.close()  # Close piano window if open
        plt.close(self.fig)  # Close matplotlib figure
        
    def getFrequencies(self):
        """Get current frequency values from spinboxes."""
        return [sb.value() for sb in self.freq_spinboxes]
    
    def getAmplitudes(self):
        """Get current amplitude values from sliders (converted to 0-1 range)."""
        return [slider.value() / 100 for slider in self.amp_sliders]
    
    def getDuration(self):
        """Get current duration value from slider (converted to seconds)."""
        return self.dur_slider.value() / 100
    
    def showPiano(self):
        """Create and show the piano keyboard dialog."""
        self.piano = QDialog(self)
        self.piano.setWindowTitle("Piano Keyboard")
        self.piano.setWindowIcon(QIcon('icons/icon.ico'))
        self.piano.setFixedSize(1000, 350)  # Fixed size for piano
        
        main_layout = QVBoxLayout()
        self.piano.setLayout(main_layout)
        
        # Octave controls at top
        octave_layout = QHBoxLayout()
        octave_layout.addWidget(QLabel("Octave:"))
        
        self.octave_spinbox = QSpinBox()
        self.octave_spinbox.setRange(1, 8)  # Standard piano octave range
        self.octave_spinbox.setValue(4)  # Middle octave
        self.octave_spinbox.valueChanged.connect(self.update_piano_labels)  # Update note labels
        octave_layout.addWidget(self.octave_spinbox)
        
        # Store references to all piano keys
        self.piano_keys = []
        
        main_layout.addLayout(octave_layout)
        
        # Piano keys area
        keys_widget = QWidget()
        keys_layout = QGridLayout()
        keys_widget.setLayout(keys_layout)
        
        # Piano key configuration (white and black notes)
        # Format: (note_name, semitone_offset_from_C0)
        white_notes = [
            ('C', 0), ('D', 2), ('E', 4), ('F', 5), ('G', 7), ('A', 9), ('B', 11),
            ('C', 12), ('D', 14), ('E', 16), ('F', 17), ('G', 19), ('A', 21), ('B', 23)
        ]
        
        black_notes = [
            ('C#', 1), ('D#', 3), None, ('F#', 6), ('G#', 8), ('A#', 10),
            ('C#', 13), ('D#', 15), None, ('F#', 18), ('G#', 20), ('A#', 22)
        ]
        
        # Create white keys with black text
        for i, (note, value) in enumerate(white_notes):
            btn = QPushButton()
            btn.note_value = value  # Store semitone value
            btn.setStyleSheet("""
                QPushButton {
                    background-color: white;
                    color: black;  /* Black text */
                    border: 1px solid #ccc;
                    min-width: 50px;
                    min-height: 200px;
                    font-weight: bold;
                    font-size: 12px;
                    qproperty-alignment: 'AlignBottom|AlignHCenter';
                }
                QPushButton:pressed {
                    background-color: #ddd;
                }
            """)
            # Connect to play function with note value
            btn.clicked.connect(lambda checked, v=value: self.playPianoNote(v))
            keys_layout.addWidget(btn, 1, i*2, 2, 2)  # Position in grid
            self.piano_keys.append(btn)
        
        # Create black keys
        for i, key_info in enumerate(black_notes):
            if key_info is not None:
                note, value = key_info
                btn = QPushButton()
                btn.note_value = value  # Store semitone value
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: black;
                        color: white;
                        min-width: 36px;
                        min-height: 130px;
                        margin-right: 15px;
                        margin-left: 15px;
                        font-weight: bold;
                        font-size: 11px;
                        qproperty-alignment: 'AlignBottom|AlignHCenter';
                    }
                    QPushButton:pressed {
                        background-color: #555;
                    }
                """)
                # Connect to play function with note value
                btn.clicked.connect(lambda checked, v=value: self.playPianoNote(v))
                keys_layout.addWidget(btn, 0, (i*2)+1, 1, 2)  # Position above white keys
                self.piano_keys.append(btn)
        
        main_layout.addWidget(keys_widget)
        
        # Navigation buttons for octave changes
        nav_layout = QHBoxLayout()
        prev_btn = QPushButton("◄ Previous Octave")
        prev_btn.clicked.connect(self.decrease_octave)
        next_btn = QPushButton("Next Octave ►")
        next_btn.clicked.connect(self.increase_octave)
        
        nav_layout.addWidget(prev_btn)
        nav_layout.addWidget(next_btn)
        main_layout.addLayout(nav_layout)
        
        # Initial label update
        self.update_piano_labels()
        
        def on_close():
            """Handle piano window closure."""
            self.piano = None
            if hasattr(self, 'piano_btn'):
                self.piano_btn.setEnabled(True)  # Re-enable piano button
        
        self.piano.finished.connect(on_close)
        self.piano.show()
        if hasattr(self, 'piano_btn'):
            self.piano_btn.setEnabled(False)  # Disable piano button while open

    def playPianoNote(self, note_value):
        """Play a piano note and update frequency fields with harmonics."""
        try:
            # First update the frequency fields with harmonics
            self.notesHarmonics(note_value)
            
            # Calculate frequency from note value (MIDI standard)
            octave = self.octave_spinbox.value()
            midi_note = note_value + (octave * 12)  # Convert to MIDI note number
            # A4 = 440Hz is MIDI note 69
            frequency = 440 * (2 ** ((midi_note - 69) / 12))
            
            # Generate rich piano-like sound with harmonics
            duration = 0.5  # seconds
            samples = int(duration * self.fs)
            fade_samples = int(0.02 * self.fs)  # 20ms fade to prevent clicks
            
            t = np.linspace(0, duration, samples, False)
            # Add harmonics for richer piano sound
            signal = (0.6 * np.sin(2 * np.pi * frequency * t) +  # Fundamental
                     0.3 * np.sin(2 * np.pi * 2 * frequency * t) +  # 2nd harmonic
                     0.1 * np.sin(2 * np.pi * 3 * frequency * t))   # 3rd harmonic
            
            # Apply fade in/out to prevent clicking
            if fade_samples > 0:
                fade_in = np.linspace(0, 1, fade_samples) ** 2  # Quadratic fade
                fade_out = np.linspace(1, 0, fade_samples) ** 2
                signal[:fade_samples] *= fade_in
                signal[-fade_samples:] *= fade_out
            
            # Play the note using sounddevice
            with sd.OutputStream(samplerate=self.fs, blocksize=2048, channels=1) as stream:
                stream.write(signal.astype(np.float32))
                
        except Exception as e:
            print(f"Error playing note: {e}")

    def update_piano_labels(self):
        """Update all piano key labels based on current octave."""
        current_octave = self.octave_spinbox.value()
        note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        
        for btn in self.piano_keys:
            note_value = btn.note_value
            note_name = note_names[note_value % 12]  # Get note name from semitone
            octave = current_octave + (note_value // 12)  # Calculate actual octave
            btn.setText(f"{note_name}\n{octave}")  # Update button text

    def decrease_octave(self):
        """Decrease octave and update piano labels."""
        current = self.octave_spinbox.value()
        if current > 1:  # Don't go below octave 1
            self.octave_spinbox.setValue(current - 1)

    def increase_octave(self):
        """Increase octave and update piano labels."""
        current = self.octave_spinbox.value()
        if current < 8:  # Don't go above octave 8
            self.octave_spinbox.setValue(current + 1)

    def _audio_worker(self):
        """Background thread for smooth, non-blocking audio playback."""
        while True:
            signal, fs = self.audio_queue.get()  # Wait for audio data
            if signal is None:  # Exit signal
                break
            try:
                sd.play(signal, fs, blocking=True)  # Play the audio
                sd.wait()  # Wait for playback to finish
            except Exception as e:
                print(f"Audio playback error: {e}")

    def notesHarmonics(self, note_value):
        """Update all frequency fields with fundamental and harmonics of selected note."""
        try:
            octave = self.octave_spinbox.value()
            # Convert to frequency (A4 = 440Hz is note 69 in MIDI)
            midi_note = note_value + (octave * 12)
            fundfreq = 440 * (2 ** ((midi_note - 69) / 12))
            
            # Set fundamental frequency (1st harmonic)
            self.freq_spinboxes[0].setValue(int(round(fundfreq)))
            self.amp_sliders[0].setValue(100)  # Full amplitude for fundamental
            
            # Set harmonics (2nd through 6th) with decreasing amplitudes
            harmonics = [
                (2, 0.83),  # 2nd harmonic, 83% amplitude
                (3, 0.67),  # 3rd harmonic, 67% amplitude  
                (4, 0.5),   # 4th harmonic, 50% amplitude
                (5, 0.33),  # 5th harmonic, 33% amplitude
                (6, 0.17)   # 6th harmonic, 17% amplitude
            ]
            
            for i, (multiple, amp) in enumerate(harmonics, start=1):
                if i < len(self.freq_spinboxes):  # Safety check
                    freq = fundfreq * multiple  # Calculate harmonic frequency
                    self.freq_spinboxes[i].setValue(int(round(freq)))
                    self.amp_sliders[i].setValue(int(amp * 100))  # Set amplitude
            
            # Automatically update the plot with new harmonics
            self.plotFAPT()
            
        except Exception as e:
            print(f"Error updating harmonics: {e}")

    def togglePiano(self):
        """Properly manage piano window lifecycle - show or hide."""
        if not self.pianoOpen:
            self.showPiano()  # Show piano if not open
            self.pianoOpen = True
        else:
            self.piano.close()  # Close piano if open
            self.pianoOpen = False

    def plotFAPT(self):
        """Generate and plot the composite tone from all configured frequencies."""
        # Get current parameters
        duration = self.getDuration()
        samples = int(duration * self.fs)  # Calculate number of samples
        freqs = self.getFrequencies()  # Get all frequencies
        amps = self.getAmplitudes()  # Get all amplitudes
        
        # Generate time array
        time = np.linspace(0, duration, samples, endpoint=False)
        signal = np.zeros(samples)  # Initialize with zeros
        
        # Add each tone to the composite signal
        for freq, amp in zip(freqs, amps):
            if freq > 0:  # Only add if frequency is non-zero
                signal += amp * np.sin(2 * np.pi * freq * time)
        
        # Store the full audio signal for playback and loading
        self.full_audio = signal
        self.audio_duration = duration

        # Clear and update the plot
        self.ax.clear()
        self.ax.plot(time, signal, linewidth=1.5, color='blue')
        
        # Configure plot limits and labels
        limit = max(abs(signal)) * 1.1 if max(abs(signal)) > 0 else 1.1
        self.ax.set(
            xlim=[0, duration],
            ylim=[-limit, limit],  # Dynamic y-limits based on signal
            xlabel='Time (s)',
            ylabel='Amplitude'
        )
        self.ax.axhline(0, color='black', linewidth=0.5, linestyle='--')  # Zero line
        self.ax.grid(True, linestyle=':', alpha=0.7)  # Add grid
        
        # Add load button and span selector
        self.addLoadButton(signal, duration)
        
        self.canvas.draw()  # Refresh the display

    def addLoadButton(self, audio, duration):
        """Add a 'Load to Controller' button and span selector to the plot."""
        # Remove previous button if exists
        if hasattr(self, 'load_btn_ax'):
            self.load_btn_ax.remove()
            if hasattr(self, 'span'):
                del self.span
        
        # Store the current audio data
        self.full_audio = audio
        self.audio_duration = duration
        
        # Create new button in the figure
        self.load_btn_ax = self.fig.add_axes([0.8, 0.01, 0.15, 0.05])  # Position and size
        self.load_btn = Button(self.load_btn_ax, 'Load to Controller')
        
        # Connect the button to load method
        self.load_btn.on_clicked(lambda event: self.load_to_controller())
        
        # Create time array for span selection
        time = np.linspace(0, duration, len(audio), endpoint=False)
        
        def onselect(xmin, xmax):
            """Handle span selection for audio playback."""
            if not hasattr(self, 'full_audio') or len(self.full_audio) <= 1:
                return
                
            # Find indices corresponding to selected time range
            ini, end = np.searchsorted(time, (xmin, xmax))
            selected_audio = self.full_audio[ini:end+1].copy()
            
            # Store the selected span for title generation
            self.selected_span = (xmin, xmax)
            
            # Apply fade to prevent clicks at boundaries
            fade_samples = min(int(0.02 * self.fs), len(selected_audio)//4)
            if fade_samples > 0:
                fade_in = np.linspace(0, 1, fade_samples) ** 2  # Quadratic fade
                fade_out = np.linspace(1, 0, fade_samples) ** 2
                selected_audio[:fade_samples] *= fade_in
                selected_audio[-fade_samples:] *= fade_out
            
            self.selectedAudio = selected_audio  # Store selected audio
            
            # Play the selected segment
            try:
                sd.stop()  # Stop any current playback
                sd.play(selected_audio, self.fs, blocking=False)  # Non-blocking playback
            except Exception as e:
                print(f"Playback error: {e}")
        
        # Create span selector for interactive audio selection
        self.span = SpanSelector(
            self.ax,
            onselect,  # Selection callback
            'horizontal',  # Selection direction
            useblit=True,  # Use blitting for performance
            interactive=True,  # Allow interactive adjustment
            drag_from_anywhere=True  # Drag from anywhere in span
        )
        
        self.canvas.draw()  # Refresh the display
            
    def load_to_controller(self):
        """Load the current audio (or selection) into a new control window."""
        from core.controlMenu import ControlMenu  # Import here to avoid circular imports

        try:
            # First ensure we have audio data
            if not hasattr(self, 'full_audio'):
                self.plotFAPT()  # Regenerate the audio if needed
            
            # Determine which audio to load (selected segment or full audio)
            if hasattr(self, 'selectedAudio') and len(self.selectedAudio) > 1:
                audio_to_load = self.selectedAudio
                duration = len(self.selectedAudio) / self.fs
                # Create title with time span if available
                if hasattr(self, 'selected_span'):
                    start_time, end_time = self.selected_span
                    title = f"Free Addition {self.format_timestamp(start_time)}-{self.format_timestamp(end_time)}"
                else:
                    title = "Free Addition (selection)"
            else:
                audio_to_load = self.full_audio  # Load full audio
                duration = self.audio_duration
                title = "Free Addition"  # Simple title for full audio
            
            # Create a minimal controller if main controller isn't available
            if not hasattr(self.controller, 'adse'):
                from PyQt5.QtWidgets import QWidget
                self.controller = QWidget()
                self.controller.adse = type('', (), {})()  # Dummy object
                self.controller.adse.advancedSettings = lambda: print("Advanced settings not available")
            
            # Create new control window with the audio
            control_window = ControlMenu(title, self.fs, audio_to_load, duration, self.controller)
            
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
            QMessageBox.critical(self, "Error", f"Could not load to controller: {str(e)}")

    def format_timestamp(self, seconds):
        """Format seconds into MM:SS.mmm format for display in titles."""
        minutes, seconds = divmod(seconds, 60)
        return f"{int(minutes):02d}:{seconds:06.3f}"  # MM:SS.mmm format

    def closeEvent(self, event):
        """Clean up resources when closing the window."""
        self.audio_queue.put((None, None))  # Signal audio thread to exit
        if self.piano:  # Close piano window if open
            self.piano.close()
        super().closeEvent(event)

if __name__ == "__main__":
    # Standalone execution for testing
    app = QApplication(sys.argv)
    window = FreeAdditionPureTones(None)  # Create without controller
    window.show()
    sys.exit(app.exec_())