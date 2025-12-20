#!/usr/bin/env python
"""
EasyPlantFieldID - GIS Preprocessing and Seedling Detection GUI.

Main entry point for the application.

Usage
-----
    uv run python main.py

or:
    python main.py
"""

import sys
from pathlib import Path

# Add lib folder to path for SAM3 source code
lib_path = Path(__file__).parent / "lib"
if lib_path.exists():
    sys.path.insert(0, str(lib_path))

# Add src folder to path
src_path = Path(__file__).parent / "src"
if src_path.exists():
    sys.path.insert(0, str(src_path))


def main() -> int:
    """
    Main entry point for EasyPlantFieldID application.

    Returns
    -------
    int
        Exit code (0 for success, non-zero for error).
    """
    from loguru import logger
    from PySide6.QtWidgets import QApplication
    import pyqtgraph as pg

    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
               "<level>{message}</level>",
        level="DEBUG"
    )

    logger.info("Starting EasyPlantFieldID...")

    # Configure PyQtGraph
    pg.setConfigOptions(
        imageAxisOrder='row-major',
        antialias=True,
    )

    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("EasyPlantFieldID")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("UTokyo-FieldPhenomics-Lab")

    # Set application style
    app.setStyle("Fusion")

    # Import and create main window
    from src.gui.main_window import MainWindow

    window = MainWindow()
    window.show()

    logger.info("Application started successfully")

    # Run event loop
    exit_code = app.exec()

    logger.info(f"Application exited with code: {exit_code}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
