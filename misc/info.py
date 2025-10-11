"""
Application Information Module

This module provides the about/information panel for the Signal Visualizer application.
It displays project credits, institutional information, and academic references.

Key Features:
- Project team and contributor credits
- Institutional collaboration information
- Academic references and citations
- Clean, formatted information display

Dependencies:
- PyQt5: Graphical user interface components

Author: Matteo Tsikalakis-Reeder
Date: 25/09/2025
Version: 1.0
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QFrame)
from PyQt5.QtCore import Qt

class Info(QWidget):
    """
    Information panel displaying project credits and references.
    
    This widget provides comprehensive information about:
    - Project team members and their roles
    - Institutional collaborations (UPV/EHU and Musikene)
    - Academic references and external resources
    - Program icon and logo credits
    
    The information is presented in a clean, scrollable format
    suitable for an "About" dialog or information panel.

    Attributes:
        controller: Reference to main application controller
        master: Parent widget reference
    """

    def __init__(self, master, controller):
        """
        Initialize the Information panel widget.
        
        Args:
            master: Parent widget
            controller: Main application controller for coordination
        """
        super().__init__(master)
        self.controller = controller
        self.master = master
        self.initUI()  # Initialize user interface
        
    def initUI(self):
        """
        Initialize and configure the user interface.
        
        Creates a vertically stacked layout with:
        - Application title
        - Institutional collaboration information
        - Team member credits with role descriptions
        - Academic references and citations
        - External resource acknowledgments
        """
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignTop)  # Content starts from top
        
        # Create application title label with enhanced styling
        title = QLabel("Signal Visualizer")
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        
        # Institutional collaboration description
        intro = QLabel("A collaboration between University of the Basque Country (UPV/EHU)\nand Musikene, Higher School of Music of the Basque Country.")
        
        # Create a framed section for team member information
        people_frame = QFrame()
        people_layout = QVBoxLayout()
        
        def create_label_pair(role, name):
            """
            Helper function to create role-name label pairs.
            
            Args:
                role: Role description (italicized)
                name: Person's name
                
            Returns:
                tuple: (role_label, name_label) QLabel objects
            """
            role_label = QLabel(role)
            role_label.setStyleSheet("font-style: italic;")  # Italic for roles
            name_label = QLabel(name)
            return role_label, name_label
            
        # Create role-name pairs for all team members
        leader_role, leader_name = create_label_pair("Project leader:", "Inma Hernáez Rioja")
        contact_role, contact_name = create_label_pair("Project leader from Musikene:", "José María Bretos")
        dev_role, dev_name = create_label_pair("Developers:", "Matteo Tsikalakis Reeder, Leire Varela Aranguren, Valentin Lurier, Eder del Blanco Sierra, Mikel Díez García")
        icon_role, icon_name = create_label_pair("Program icon and logo made by:", "Sergio Santamaría Martínez")
        
        # Add all role-name pairs to people layout
        for widget in [leader_role, leader_name, contact_role, contact_name, 
                      dev_role, dev_name, icon_role, icon_name]:
            people_layout.addWidget(widget)
            
        people_frame.setLayout(people_layout)
        
        # References and acknowledgments section
        aholab = QLabel("\nHiTZ Basque Center for Language Technologies - Aholab Signal Processing Laboratory (UPV/EHU).\n")
        references = QLabel("References:")
        
        # External resource reference
        ref1 = QLabel("Function for creating brown (or red) noise made by Hristo Zhivomirov:\nHristo Zhivomirov (2020). Pink, Red, Blue and Violet Noise Generation with Matlab.\nhttps://www.mathworks.com/matlabcentral/fileexchange/42919-pink-red-blue-and-violet-noise-generation-with-matlab\nMATLAB Central File Exchange. Retrieved August 4, 2020.")
        
        # Academic thesis reference
        ref2 = QLabel("Master thesis describing the version of the software Signal Visualizer in Matlab made by Eder del Blanco Sierra:\nEder del Blanco Sierra (2020). Programa de apoyo a la enseñanza musical.\nUniversity of the Basque Country (UPV/EHU). Department of Communications Engineering. Retrieved August 8, 2020.\nThe function has been modified by Valentin Lurier and Mikel Díez García.")
        
        # Add all widgets to the main layout in order
        for widget in [title, intro, people_frame, aholab, references, ref1, ref2]:
            layout.addWidget(widget)
            
        self.setLayout(layout)  # Apply the layout to the widget