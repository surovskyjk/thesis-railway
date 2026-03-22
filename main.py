import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from gui import MainWindow

# Relative path for icon resource, compatible with PyInstaller
def get_resource_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', Path(__file__).parent)
    return base_path / relative_path

# Main Function
def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Set application icon
    app.setWindowIcon(QIcon(str(get_resource_path("icon.png"))))

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


# Run the application

if __name__ == "__main__":
    main()

