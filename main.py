# main.py
import sys
from PyQt6.QtWidgets import QApplication
from gui import MainWindow

if __name__ == '__main__':
    app = QApplication(sys.argv)
    # You might want to set application info (optional)
    # app.setApplicationName("El Zorro")
    # app.setOrganizationName("YourNameOrOrg") # Helps with settings paths etc.

    window = MainWindow()
    window.show()
    sys.exit(app.exec())