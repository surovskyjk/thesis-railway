import sys
from PySide6.QtWidgets import QApplication
from gui import MainWindow

# Main Function

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


# Run the application

if __name__ == "__main__":
    main()

