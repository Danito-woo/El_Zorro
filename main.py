# main.py
import sys
from PyQt6.QtWidgets import QApplication
from gui import MainWindow

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setApplicationName("El Zorro")
    app.setOrganizationName("JejejeORG") # You might add some love here

    window = MainWindow()
    window.show()
    sys.exit(app.exec())