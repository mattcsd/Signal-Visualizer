"""
Signal Visulizer 

-- The Main window module that initializes the main menu and important variables, 
sets up the starting window. Besides creating the main menu toolbar that contains 
the program's functionalities and initializes them as frames it also prepares, 
keeps track and updates the (currently) open window functionality.
 Finally it handles cleanup on closing of frames-functionalities.

Dependencies:
 - PyQt5: As the graphical interface.
 - matplotlib: For basic plotting.



Author: Matteo Tsikalakis-Reeder
Date: 25/09/2025
Version: 1.0
"""


import sys
from PyQt5.QtWidgets import QToolButton, QWidgetAction, QHBoxLayout, QAction, QApplication, QMenuBar, QMenu, QMainWindow, QWidget, QVBoxLayout, QMenuBar, QMenu, QAction, QMessageBox, QDesktopWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QFont
import matplotlib.pyplot as plt

from misc.help import Help

# To avoid blurry fonts on Windows - DPI awareness for high resolution displays
if sys.platform == "win32":
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)

# If in mac the menu bar is not at the top as by default but within the window.
if sys.platform == "darwin":  # macOS
    QApplication.setAttribute(Qt.AA_DontUseNativeMenuBar)


class Start(QMainWindow):
    """
    Main application window for Signal Visualizer.
    Handles window initialization, menu creation, and frame management.
    """
    
    def __init__(self):
        """Initialize the main application window and its components."""
        super().__init__()
        self.setWindowTitle("Signal Visualizer")

        # Set window size and center it
        self.resize(900, 650)  # Increased size to accommodate Info content
        self.center_window()    # Center the window

        # Central widget and layout
        self.container = QWidget()
        self.setCentralWidget(self.container)
        self.layout = QVBoxLayout(self.container)
        self.container.setLayout(self.layout)

        # Dictionary to hold frames (pages) of the application
        self.frames = {}

        # Track all open windows for the window management menu
        self.all_open_windows = {
            'control_menus': [],  # Will reference Load's control_windows
            'plot_windows': []    # Will reference ControlMenu's plot_windows
        }
        
        # Initialize and show Info frame by default
        self.initialize_frame('Info')
        self.show_welcome_dialog()

        # Initialize Help system
        self.help = Help(self.container, self)
        # Set up the menu bar
        self.create_menu_bar()


    def show_welcome_dialog(self):
        """Display the welcome dialog on first run."""
        from misc.popupinfo import FirstRunDialog
        dialog = FirstRunDialog(self)
        dialog.exec_()

    def center_window(self):
        """Center the window on the screen."""
        screen = QDesktopWidget().screenGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def get_all_open_windows(self):
        """
        Collect all open control and plot windows from all sources.
        
        Returns:
            tuple: (control_windows, plot_windows) lists
        """
        control_windows = []
        plot_windows = []
        
        # Get control windows from Load frame if it exists
        if 'Load' in self.frames:
            control_windows.extend(self.frames['Load'].control_windows)
        
        # Get control windows from Record frame if it exists
        if 'Record' in self.frames and hasattr(self.frames['Record'], 'control_windows'):
            control_windows.extend(self.frames['Record'].control_windows)
        
        # Get plot windows from all control windows
        for ctrl_window in control_windows:
            if hasattr(ctrl_window, 'plot_windows') and ctrl_window.plot_windows:
                plot_windows.extend(ctrl_window.plot_windows)
        
        return control_windows, plot_windows

    def close_all_windows(self):
        """Close all open control and plot windows."""
        control_windows, plot_windows = self.get_all_open_windows()
        
        # Close all plot windows first
        for plot_window in plot_windows:
            try:
                plot_window.close()
                plot_window.deleteLater()
            except Exception as e:
                print(f"Error closing plot window: {e}")
        
        # Close all control windows
        for ctrl_window in control_windows:
            try:
                ctrl_window.close()
                ctrl_window.deleteLater()
            except Exception as e:
                print(f"Error closing control window: {e}")
        
        # Clear the lists in the frames
        if 'Load' in self.frames:
            self.frames['Load'].control_windows.clear()
        
        if 'Record' in self.frames and hasattr(self.frames['Record'], 'control_windows'):
            self.frames['Record'].control_windows.clear()

    def initialize_frame(self, page_name):
        """
        Initialize and display a frame based on the page name.
        
        Args:
            page_name (str): Name of the frame/page to initialize
        """
        # Clean up existing frame if it exists and has cleanup method
        if page_name in self.frames and hasattr(self.frames[page_name], 'cleanup'):
            self.frames[page_name].cleanup()
        
        # Initialize the appropriate frame based on page_name
        if page_name == 'SignalVisualizer':
            self.frames['SignalVisualizer'] = SignalVisualizer(self.container, self)
        elif page_name == 'Info':
            from misc.info import Info
            self.frames['Info'] = Info(self.container, self)
        elif page_name == 'Load':
            from utils.inputLoad import Load
            self.frames['Load'] = Load(self.container, self)
        elif page_name == 'Record':
            from utils.inputRecord import Record
            self.frames['Record'] = Record(self.container, self)
        elif page_name == 'Noise':
            from core.generators.generateNoise import Noise
            self.frames['Noise'] = Noise(self.container, self)
        elif page_name == 'PureTone':
            from core.generators.generatePureTone import PureTone
            self.frames['PureTone'] = PureTone(self.container, self)
        elif page_name == 'FreeAdditionPureTones':
            from core.generators.generateFreeAdd import FreeAdditionPureTones
            self.frames['FreeAdditionPureTones'] = FreeAdditionPureTones(self.container, self)
        elif page_name == 'SquareWave':
            from core.generators.generateSquareWave import SquareWave
            self.frames['SquareWave'] = SquareWave(self.container, self)
        elif page_name == 'SawtoothWave':
            from core.generators.generateSawtoothWave import SawtoothWave
            self.frames['SawtoothWave'] = SawtoothWave(self.container, self)
        elif page_name == 'Spectrogram':
            self.frames['Spectrogram'] = Spectrogram(self.container, self)
        elif page_name == 'Tuner':
            from utils.FFTtuner import AudioFFTVisualizer
            self.frames['Tuner'] = AudioFFTVisualizer(self.container, self)
        elif page_name == 'Cretan Lute':
            from utils.examples import BeatFrequencyVisualizer
            self.frames['Cretan Lute'] = BeatFrequencyVisualizer(self.container, self)
        
        # Show the initialized frame
        self.show_frame(page_name)

    def show_frame(self, page_name):
        """
        Show the frame corresponding to the given page name.
        
        Args:
            page_name (str): Name of the frame/page to display
        """
        if page_name in self.frames:
            # Clean up current frame if it exists and has cleanup method
            current_widget = self.layout.itemAt(0).widget() if self.layout.count() > 0 else None
            if current_widget and hasattr(current_widget, 'cleanup'):
                current_widget.cleanup()
            
            # Remove the current widget from the layout
            for i in reversed(range(self.layout.count())):
                widget = self.layout.itemAt(i).widget()
                widget.setParent(None)
                if hasattr(widget, 'cleanup'):  # Additional safety check
                    widget.cleanup()
            
            # Add the new frame to the layout
            self.layout.addWidget(self.frames[page_name])
            self.frames[page_name].setVisible(True)

    def create_menu_bar(self):
        """Create the menu bar with button-style dropdown items that support tooltips."""
        menubar = self.menuBar()
        
        # Apply stylesheet for consistent styling across the menu bar
        menubar.setStyleSheet("""
            /* Main menu bar */
            QMenuBar {
                background-color: #2c3e50;
                color: white;
                font-size: 1em;
                font-weight: bold;
                padding: 0.5em;
                spacing: 0.5em;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 0.5em 1em;
                border-radius: 0.25em;
            }
            QMenuBar::item:selected {
                background-color: #3498db;
            }
            QMenuBar::item:pressed {
                background-color: #2980b9;
            }
            
            /* Dropdown menus */
            QMenu {
                background-color: #34495e;
                color: white;
                border: 1px solid #555;
                padding: 0.25em;
                font-size: 1em;
                min-width: 12em;  /* Based on typical character width */
            }
            
            /* Menu buttons */
            QToolButton {
                background-color: transparent;
                color: white;
                border: none;
                padding: 0.75em 1.5em;
                text-align: left;
                min-width: 12em;
                min-height: 2.25em;
                font-size: 1em;
            }
            QToolButton:hover {
                background-color: #3498db;
                border-radius: 0.2em;
            }
            
            /* Tooltips */
            QToolTip {
                background-color: #34495e;
                color: white;
                border: 1px solid #3498db;
                padding: 0.5em;
                border-radius: 0.25em;
                font-size: 18pt;
                opacity: 230;
            }
            /* Submenu items - make them match main menu height */
            QMenu::item {
                padding: 0.75em 1.5em;  /* Increased vertical padding */
                min-height: 2.25em;      /* Explicit minimum height */
            }
            
            /* Submenu indicators */
            QMenu::indicator {
                width: 1em;
                height: 1em;
            }
            
            /* Submenu itself */
            QMenu::menu {
                margin: 0.25em;  /* Slight margin around submenu */
            }
        """)


        # Signal Visualizer menu - Application main options
        signal_menu = menubar.addMenu("Signal Visualizer")
        self._add_menu_button(signal_menu, "Info", "Show application information and instructions", 
                            lambda: self.initialize_frame('Info'))
        self._add_menu_button(signal_menu, "Exit", "Exit the application", self.close)

        # Generate menu - Signal generation options
        generate_menu = menubar.addMenu("Generate")
        self._add_menu_button(generate_menu, "Pure tone", "Generate a single frequency sine wave",
                             lambda: self.initialize_frame('PureTone'))
        self._add_menu_button(generate_menu, "Free addition of pure tones", 
                            "Combine multiple sine waves with custom frequencies",
                            lambda: self.initialize_frame('FreeAdditionPureTones'))
        self._add_menu_button(generate_menu, "Noise", "Generate different types of noise signals",
                             lambda: self.initialize_frame('Noise'))

        # Known periodic signals submenu
        known_menu = generate_menu.addMenu("Known periodic signals")
        self._add_menu_button(known_menu, "Square wave", "Generate a square wave signal",
                             lambda: self.initialize_frame('SquareWave'))
        self._add_menu_button(known_menu, "Sawtooth wave", "Generate a sawtooth wave signal",
                             lambda: self.initialize_frame('SawtoothWave'))

        # Input menu - Audio input options
        input_menu = menubar.addMenu("Input")
        self._add_menu_button(input_menu, "Load", "Load an audio file from disk",
                             lambda: self.initialize_frame('Load'))
        self._add_menu_button(input_menu, "Record", "Record audio from your microphone",
                             lambda: self.initialize_frame('Record'))

        # Tuner menu - Audio analysis tools
        tuner_menu = menubar.addMenu("Tuner")
        self._add_menu_button(tuner_menu, "Live STFT", "Real-time frequency analysis for tuning instruments",
                             lambda: self.initialize_frame('Tuner'))
        '''
        # Tools menu - Additional analysis tools (commented out)
        tools_menu = menubar.addMenu("Tools")
        self._add_menu_button(tools_menu, "Fundamental/Harmonics Separator",
                            "Separate fundamental frequency from harmonics",
                            lambda: self.show_separator_tool())
        '''

        # Examples menu - Pre-built demonstrations
        examples_menu = menubar.addMenu("Examples")
        self._add_menu_button(examples_menu, "Cretan Lute", "Example analysis of Cretan Lute audio",
                             lambda: self.initialize_frame('Cretan Lute'))

        # Open windows menu - Window management
        windows_menu = menubar.addMenu("Open windows")
        
        # Create submenus for different window types
        self.control_windows_menu = windows_menu.addMenu("Control Windows")
        self.plot_windows_menu = windows_menu.addMenu("Plot Windows")
        
        # Connect to aboutToShow to auto-update the menu when opened
        windows_menu.aboutToShow.connect(self.update_windows_menu)

        '''
        # Options menu - Application settings (commented out)
        options_menu = menubar.addMenu("Options")
        self._add_menu_button(options_menu, "Spectrogram", "Configure spectrogram display settings",
                             lambda: self.initialize_frame('Spectrogram'))
        '''

    def update_windows_menu(self):
        """Update the windows menu with current open windows dynamically."""
        # Clear existing menus to refresh the list
        self.control_windows_menu.clear()
        self.plot_windows_menu.clear()
        
        # Collect control windows from all sources
        control_windows, plot_windows = self.get_all_open_windows()
        
        # Add control windows with source indication
        for i, window in enumerate(control_windows, 1):
            # Determine source based on window title
            title = window.windowTitle()
            if "Recording" in title:
                icon = "🎙️"  # Microphone for recordings
            else:
                icon = "📁"   # Folder for loaded files
            
            # Create action for each control window
            action = QAction(f"{i}. {icon} {title}", self)
            action.triggered.connect(lambda _, w=window: self.focus_window(w))
            self.control_windows_menu.addAction(action)
            
        # Add plot windows with grouping by their parent control window
        plot_count = 1
        for ctrl_window in control_windows:
            # Only add group if there are plot windows for this control window
            if hasattr(ctrl_window, 'plot_windows') and ctrl_window.plot_windows:
                # Add separator with control window title (except before first group)
                if plot_count > 1:
                    self.plot_windows_menu.addSeparator()
                
                # Determine source icon for header
                title = ctrl_window.windowTitle()
                if "Recording" in title:
                    icon = "🎙️"
                else:
                    icon = "📁"
                
                # Add clickable header for the control window
                header = QAction(f"📌 {icon} {title}", self)
                header.setFont(QFont("Arial", weight=QFont.Bold))
                header.triggered.connect(lambda _, w=ctrl_window: self.focus_window(w))
                self.plot_windows_menu.addAction(header)
                
                # Add plot windows for this control window
                for plot_window in ctrl_window.plot_windows:
                    action = QAction(f"    {plot_count}. {plot_window.windowTitle()}", self)
                    action.triggered.connect(lambda _, w=plot_window: self.focus_window(w))
                    self.plot_windows_menu.addAction(action)
                    plot_count += 1

    def focus_window(self, window):
        """
        Bring a window to focus.
        
        Args:
            window: The window object to focus
        """
        if window:
            window.raise_()
            window.activateWindow()

    def _add_menu_button(self, menu, text, tooltip, callback):
        """
        Helper method to create a button-like menu item with tooltip.
        
        Args:
            menu: The parent menu to add the button to
            text (str): The text to display on the button
            tooltip (str): The tooltip text to show on hover
            callback: The function to call when the button is clicked
            
        Returns:
            QWidgetAction: The created action object
        """
        action = QWidgetAction(menu)
        button = QToolButton()
        button.setText(text)
        button.setToolTip(tooltip)
        button.setCursor(Qt.PointingHandCursor)

        # ONLY CHANGE THE FONT SIZE - keep other styling original
        font = button.font()
        font.setPointSize(15)  # Adjust this value as needed (default is usually 9-10)
        button.setFont(font)

        # Apply styling to the button
        button.setStyleSheet("""
            QToolButton {
                background-color: transparent;
                color: white;
                border: none;
                padding: 0.75em 1.5em;
                text-align: left;
                min-width: 12em;
                min-height: 2.25em;
                font-size: 16pt;    #hover message font size
            }
            QToolButton:hover {
                background-color: #3498db;
                border-radius: 0.2em;
            }
        """)
        button.clicked.connect(callback)
        action.setDefaultWidget(button)
        menu.addAction(action)
        return action

    def show_separator_tool(self):
        """Show the separator tool in a new window (placeholder implementation)."""
        if not hasattr(self, 'separator_window') or not self.separator_window.isVisible():
            self.separator_window = FundamentalHarmonicsSeparator()
            self.separator_window.show()
            
            # If you have audio loaded in the main window, pass it to the separator
            if hasattr(self, 'current_audio') and self.current_audio is not None:
                self.separator_window.load_signal(self.current_audio, self.current_fs)

    def launch_tuner(self):
        """Launch the live audio tuner (placeholder implementation)."""
        try:
            # First check if we already have a tuner running
            if hasattr(self, 'tuner_window') and self.tuner_window.isVisible():
                self.tuner_window.raise_()
                return
            
            # Import the tuner module if it's in a separate file
            from your_tuner_module import TunerWindow
            
            # Create and show the tuner window
            self.tuner_window = TunerWindow(parent=self)
            self.tuner_window.show()
            
            # Connect close event for cleanup
            self.tuner_window.destroyed.connect(self.cleanup_tuner)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not launch tuner: {str(e)}")

    def cleanup_tuner(self):
        """Clean up tuner resources (placeholder implementation)."""
        if hasattr(self, 'tuner_window'):
            try:
                self.tuner_window.close()
                self.tuner_window.deleteLater()
            except:
                pass
            del self.tuner_window

    def closeEvent(self, event):
        """
        Handle the window close event.
        Prompts the user to confirm quitting and closes matplotlib figures.
        
        Args:
            event: The close event
        """
        reply = QMessageBox.question(
            self,
            "Quit",
            "Do you want to quit?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            # Close all open windows first
            self.close_all_windows()
            
            # Close all matplotlib figures
            plt.close('all')
            
            # Accept the close event
            event.accept()
        else:
            event.ignore()

class SignalVisualizer(QWidget):
    """
    Base widget class for signal visualization components.
    Serves as a parent class for specific visualization widgets.
    """
    
    def __init__(self, master, controller):
        """
        Initialize the signal visualizer widget.
        
        Args:
            master: The parent widget
            controller: The main application controller
        """
        super().__init__(master)
        self.controller = controller
        self.master = master


if __name__ == "__main__":
    """Main entry point for the application."""
    app = QApplication(sys.argv)
    window = Start()
    window.show()
    sys.exit(app.exec_())