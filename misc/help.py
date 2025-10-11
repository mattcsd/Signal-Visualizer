"""
Help System Module

This module provides a comprehensive help system for the Signal Visualizer application.
It features a dialog window with categorized help topics and HTML content display.

Key Features:
- Radio button navigation between help topics
- HTML content display with support for embedded resources
- Persistent help window management
- Context-aware help topic loading

Dependencies:
- PyQt5: Graphical user interface components
- PyQt5.QtWebEngineWidgets: HTML content rendering
- os: File path operations

Author: Matteo Tsikalakis-Reeder
Date: 25/09/2025
Version: 1.0
"""

import os
import sys

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QRadioButton, 
                            QWidget, QFrame, QLabel)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl

class Help(QWidget):
    """
    Help system widget providing context-sensitive documentation.
    
    This class manages the help system interface with:
    - Radio button navigation for different help topics
    - HTML content display with proper resource loading
    - Window lifecycle management
    - Topic-to-file path mapping
    
    Attributes:
        controller: Reference to main application controller
        help_window: Main help dialog window instance
        html_paths: Dictionary mapping topic IDs to HTML file paths
        radio_group: List of radio button widgets for topic selection
        web_view: QWebEngineView for displaying HTML content
    """

    def __init__(self, controller, parent=None):
        """
        Initialize the Help system widget.
        
        Args:
            controller: Main application controller for coordination
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        self.controller = controller
        self.help_window = None  # Main help dialog window

        # Determine base path (development vs bundled app)
        if getattr(sys, 'frozen', False):
            # Running inside PyInstaller bundle
            base_path = sys._MEIPASS
        else:
            # Running from source
            base_path = os.path.abspath(".")

        # Build absolute paths for help HTML files
        self.html_paths = {
            1: os.path.join(base_path, 'html', 'en', 'generate_pure_tone', 'Generatepuretone.html'),
            2: os.path.join(base_path, 'html', 'en', 'harmonic_synthesis', 'Harmonicsynthesis.html'),
            3: os.path.join(base_path, 'html', 'en', 'generate_square_wave', 'Generatesquarewave.html'),
            4: os.path.join(base_path, 'html', 'en', 'generate_sawtooth_signal', 'Generatesawtoothsignal.html'),
            5: os.path.join(base_path, 'html', 'en', 'generate_noise', 'Generatenoise.html'),
            6: os.path.join(base_path, 'html', 'en', 'load_audio_file', 'Loadaudiofile.html'),
            7: os.path.join(base_path, 'html', 'en', 'record_audio', 'Recordaudio.html'),
            8: os.path.join(base_path, 'html', 'en', 'visualization_window', 'Visualizationwindow.html')
        }


    def createHelpMenu(self, value):
        """
        Create and display the help menu dialog.
        
        Initializes the help window with radio button navigation and HTML content
        display. If the window already exists, it brings it to the front.
        
        Args:
            value: Initial help topic ID to display
        """
        if self.help_window is None:
            self.help_window = QDialog(self)
            self.help_window.setWindowTitle('Help Menu')
            # Remove context help button from title bar
            self.help_window.setWindowFlags(self.help_window.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            self.help_window.resize(975, 600)  # Fixed window size
            
            # Main layout with minimal margins
            main_layout = QHBoxLayout()
            main_layout.setContentsMargins(5, 5, 5, 5)
            
            # Left panel for radio button navigation
            left_panel = QFrame()
            left_layout = QVBoxLayout()
            left_layout.setSpacing(5)  # Compact spacing between buttons
            
            # Create radio buttons for all help topics
            self.radio_group = []
            for i in range(1, 9):
                radio = QRadioButton(self.get_button_text(i))
                radio.setChecked(i == value)  # Select initial topic
                radio.clicked.connect(self.create_radio_handler(i))
                left_layout.addWidget(radio)
                self.radio_group.append(radio)
            
            left_panel.setLayout(left_layout)
            main_layout.addWidget(left_panel)
            
            # Right panel for HTML content display
            self.web_view = QWebEngineView()
            main_layout.addWidget(self.web_view, 1)  # Web view gets most space
            
            self.help_window.setLayout(main_layout)
            self.help_window.finished.connect(self.on_help_close)  # Cleanup on close
        
        # Show initial content and bring window to front
        self.show_help(value)
        self.help_window.show()
        self.help_window.raise_()
        self.help_window.activateWindow()

    def on_help_close(self):    
        """
        Clean up when help window is closed.
        
        Resets the help_window reference to allow recreation
        and provides optional debug output.
        """
        self.help_window = None
        print("Help window closed")  # Optional debug output

    def create_radio_handler(self, value):
        """
        Create a radio button click handler for specific help topic.
        
        Args:
            value: Help topic ID for this radio button
            
        Returns:
            function: Configured click handler function
        """
        def handler():
            print(f"Loading help page {value}")
            self.show_help(value)
        return handler

    def show_help(self, value):
        """
        Display the specified help topic content.
        
        Loads HTML content from file and displays it in the web view.
        Updates radio button selection state and handles file loading errors.
        
        Args:
            value: Help topic ID to display
        """
        if not self.help_window:  # Safety check if window was closed
                return

        print(f"Loading help page {value}")  # Debug output

        html_file = self.html_paths.get(value)
        if html_file and os.path.exists(html_file):
            try:
                # Absolute path is already set in self.html_paths
                base_dir = os.path.dirname(html_file)

                # Read HTML content with UTF-8 encoding
                with open(html_file, 'r', encoding='utf-8') as file:
                    html_content = file.read()

                # Set base URL for relative resource paths (images, CSS, etc.)
                base_url = QUrl.fromLocalFile(base_dir + '/')
                self.web_view.setHtml(html_content, base_url)

                # Update radio button selection state
                for i, radio in enumerate(self.radio_group, start=1):
                    radio.setChecked(i == value)

            except Exception as e:
                print(f"Error loading help content: {str(e)}")
                self.web_view.setHtml(
                    f"<h1>Error</h1><p>Could not load help page: {str(e)}</p>"
                )
        else:
            # File not found → show error in the web view
            self.web_view.setHtml(
                f"<h1>Not Found</h1><p>Help page {value} is missing.</p>"
            )


    def get_button_text(self, value):
        """
        Get display text for help topic radio button.
        
        Args:
            value: Help topic ID
            
        Returns:
            str: Human-readable topic name
        """
        help_topics = {
            1: "Pure Tone",
            2: "Harmonic Synthesis",
            3: "Square Wave",
            4: "Sawtooth Wave", 
            5: "Noise Generation",
            6: "Load Audio File",
            7: "Record Audio",
            8: "Visualization"
        }
        return help_topics.get(value, f"Help {value}")