# styles.py
DARK_STYLE = """
QWidget {
    background-color: #2b2b2b;
    color: #f0f0f0;
    font-size: 10pt;
}
QMainWindow {
    border: 1px solid #444; /* Opcional: borde ligero para la ventana */
}
QLineEdit {
    background-color: #3c3f41;
    border: 1px solid #555;
    padding: 5px;
    border-radius: 3px;
    color: #f0f0f0;
}
QPushButton {
    background-color: #555;
    color: #f0f0f0;
    border: 1px solid #666;
    padding: 5px 10px;
    border-radius: 3px;
    min-width: 80px;
}
QPushButton:hover {
    background-color: #666;
    border: 1px solid #777;
}
QPushButton:pressed {
    background-color: #444;
}
QPushButton:disabled {
    background-color: #404040;
    color: #888;
    border: 1px solid #555;
}
QProgressBar {
    border: 1px solid #555;
    border-radius: 3px;
    text-align: center;
    color: #f0f0f0;
    background-color: #3c3f41;
}
QProgressBar::chunk {
    background-color: #007acc; /* Azul brillante para la barra */
    width: 10px; /* Ajusta el ancho del segmento */
    margin: 0.5px;
}
QTextEdit {
    background-color: #3c3f41;
    border: 1px solid #555;
    color: #f0f0f0;
    border-radius: 3px;
}
QLabel {
    color: #f0f0f0;
}
/* Estilo para scrollbars si es necesario */
QScrollBar:vertical {
    border: 1px solid #444;
    background: #3c3f41;
    width: 12px;
    margin: 15px 0 15px 0;
    border-radius: 0px;
}
QScrollBar::handle:vertical {
    background: #666;
    min-height: 20px;
    border-radius: 5px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
    height: 15px;
    subcontrol-origin: margin;
}
QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
     background: none;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
     background: none;
}

QScrollBar:horizontal {
   border: 1px solid #444;
   background: #3c3f41;
   height: 12px;
   margin: 0px 15px 0 15px;
   border-radius: 0px;
}
QScrollBar::handle:horizontal {
    background: #666;
    min-width: 20px;
    border-radius: 5px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    border: none;
    background: none;
    width: 15px;
    subcontrol-origin: margin;
}
QScrollBar::left-arrow:horizontal, QScrollBar::right-arrow:horizontal {
     background: none;
}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
     background: none;
}
"""