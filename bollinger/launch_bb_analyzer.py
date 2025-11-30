#!/usr/bin/env python3
"""
Launch Bollinger Bands Analyzer GUI

Quick launcher for the BB analysis interface.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from bollinger.gui import BBAnalyzerGUI
from PyQt6.QtWidgets import QApplication


def main():
    """Launch the BB Analyzer GUI."""
    app = QApplication(sys.argv)
    
    # Set application metadata
    app.setApplicationName("Bollinger Bands Analyzer")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("StockScreeer")
    
    # Create and show main window
    window = BBAnalyzerGUI()
    window.show()
    
    # Run event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
