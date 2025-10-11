"""
First Run / Welcome Dialog Module

This module provides a welcome dialog that appears on first run or when requested.
It gives users an overview of application features and current beta status.

Key Features:
- Welcome message with beta version disclaimer
- Comprehensive feature overview organized by menu
- "Don't show again" option using QSettings
- Scrollable content area for extensive information
- Styled HTML content for welcome message

Dependencies:
- PyQt5: Graphical user interface components
- PyQt5.QtCore.QSettings: Persistent application settings

Author: Matteo Tsikalakis-Reeder
Date: 25/09/2025
Version: 1.0
"""

from PyQt5.QtWidgets import (QSizePolicy, QWidget, QDialog, QLabel, QVBoxLayout, QPushButton, 
                             QScrollArea, QGroupBox, QCheckBox)
from PyQt5.QtCore import QSettings, Qt

class FirstRunDialog(QDialog):
    """
    Welcome dialog for first-time users and beta testers.
    
    This dialog provides:
    - Welcome message with beta version disclaimer
    - Organized overview of application features by menu
    - Persistent "Don't show again" option
    - Scrollable content area for extensive information
    - Styled HTML content for visual appeal
    
    The dialog uses QSettings to remember user preference for
    showing the welcome message on subsequent runs.

    Attributes:
        dont_show_checkbox: Checkbox for persistent preference
    """

    def __init__(self, parent=None):
        """
        Initialize the First Run Dialog.
        
        Args:
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        self.setWindowTitle("Welcome to Signal Visualizer")
        self.resize(600, 500)  # Reasonable default size
        
        # Main layout with consistent margins
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Welcome message - fixed at top (non-scrolling)
        welcome_label = QLabel("""
            <div style="
                background-color: #f0f8ff;
                padding: 15px;
                border-radius: 8px;
                border: 1px solid #d3d3d3;
                margin-bottom: 10px;
            ">
                <h1 style="color: #2c3e50; margin-top: 0; text-align: center;">
                    Welcome to Signal Visualizer <span style="font-size: 0.7em;">(Beta Version)</span>
                </h1>
                
                <div style="background-color: white; padding: 12px; border-radius: 6px; margin: 10px 0;">
                    <h3 style="color: #3498db; margin-top: 0;">Some notes:</h3>
                    <ul style="margin: 5px 0; padding-left: 25px;">
                        <li style="margin-bottom: 8px;"><b>Waveform interaction:</b> Click-hold and select a span to play any waveform</li>
                        <li style="margin-bottom: 8px;"><b>Save function:</b> you can save to .csv from the Control Menu</li>
                        <li style="margin-bottom: 8px;"><b>Help pages/examples explanation:</b> Will be added when we reach final version</li>
                        <li style="margin-bottom: 8px;"><b>Examples page:</b> If you go full screen, in case the GUI is a little faulty just click "Replot".</li>
                        <li style="margin-bottom: 8px;"><b>If in generator</b> the signal seem short (so you can visualize them better) set duration from below</li>
                    </ul>
                </div>
                <p style="font-style: italic; color: #7f8c8d; text-align: center; margin-bottom: 0;">
                    Thank you for testing our beta version! Your feedback is valuable.
                </p>
                <p style="font-size: 0.5em;color: #3498db; text-align: center; margin-bottom: 0;">
                    For any issues/problems/questions contact csd4058@csd.uoc.gr
                </p>
            </div>
        """)
        welcome_label.setWordWrap(True)
        main_layout.addWidget(welcome_label)

        # Scroll Area for extensive content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # No horizontal scrolling
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)     # Vertical only when needed

        # Content widget for scrollable area
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(5, 5, 5, 5)
        content_layout.setSpacing(15)

        # Add organized menu explanations
        self.add_menu_section(content_layout, "Signal Visualizer Menu", [
            "Info: View information about the application",
            "Exit: Close the program"
        ])
        
        # Generate menu section with introductory text
        self.add_menu_section(content_layout, "Generate Menu", [
            "Pure tone: Generate a single frequency tone",
            "Free addition of pure tones: Combine multiple tones",
            "Noise: Generate different types of noise signals",
            "Known periodic signals → Square wave: Generate square wave signals",
            "Known periodic signals → Sawtooth wave: Generate sawtooth wave signals"
        ], 
        intro_text="The Generate menu contains tools for creating various types of audio signals. ")

        # Input menu section
        self.add_menu_section(content_layout, "Input Menu", [
            "Load: Load audio files from your computer",
            "Record: Record audio from your microphone"
        ])
        
        # Tuner menu section
        self.add_menu_section(content_layout, "Tuner Menu", [
            "Live STFT: Real-time audio frequency analysis"
        ])
        
        # Examples menu section
        self.add_menu_section(content_layout, "Examples Menu", [
            "Cretan Lute: Example of some recordings i made to analyse what i found interesting concepts"
        ])

        # Set size policy to ensure proper scrolling behavior
        content_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        content_widget.setMinimumSize(500, 400)  # Minimum size to ensure scroll appears

        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

        # Bottom controls section
        self.dont_show_checkbox = QCheckBox("Don't show this again")
        main_layout.addWidget(self.dont_show_checkbox)

        # Action button
        close_button = QPushButton("Get Started")
        close_button.clicked.connect(self.accept)  # Close dialog on click
        main_layout.addWidget(close_button)
    
    def add_menu_section(self, layout, title, items, intro_text=None):
        """
        Helper method to add a formatted menu section to the layout.
        
        Creates a grouped section with title and bullet-point items.
        Optional introductory text can be provided for context.
        
        Args:
            layout: Parent layout to add the section to
            title: Section title text
            items: List of menu item descriptions
            intro_text: Optional introductory text (default: None)
        """
        group = QGroupBox(title)
        group_layout = QVBoxLayout()
        
        # Add introductory text if provided
        if intro_text:
            intro_label = QLabel(intro_text)
            intro_label.setWordWrap(True)
            intro_label.setStyleSheet("font-style: italic; margin-bottom: 10px;")
            group_layout.addWidget(intro_label)
        
        # Add each menu item as a bullet point
        for item in items:
            label = QLabel(f"• {item}")
            label.setWordWrap(True)  # Ensure long text wraps properly
            group_layout.addWidget(label)
        
        group.setLayout(group_layout)
        layout.addWidget(group)