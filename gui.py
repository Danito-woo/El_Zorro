# gui.py
import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QProgressBar, QTextEdit, QMessageBox,
    QFileDialog, QScrollArea, QSizePolicy, QSpacerItem # Added QScrollArea, QSizePolicy, QSpacerItem
)
from PyQt6.QtCore import Qt, pyqtSlot, QUrl, QSize, pyqtSignal
from PyQt6.QtGui import QDesktopServices, QMouseEvent # Added QDesktopServices, QMouseEvent
from worker import DownloadWorker
from styles import DARK_STYLE

# --- Clickable Label Class ---
class ClickableLabel(QLabel):
    """A QLabel that emits a clicked signal with its associated path when clicked."""
    # Define a signal that carries a string (the path)
    clicked_with_path = pyqtSignal(str)

    def __init__(self, text, path, parent=None):
        super().__init__(text, parent)
        self.path_to_open = path
        # Make the label look clickable
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # Basic styling to indicate it's clickable (optional)
        self.setStyleSheet("QLabel { color: #79a6d2; text-decoration: underline; }")
        self.setToolTip(f"Click para abrir carpeta:\n{self.path_to_open}")

    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press events to emit the signal."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked_with_path.emit(self.path_to_open)
        # Call base class implementation if needed, though often not necessary for labels
        # super().mousePressEvent(event)

# --- Main Window Class ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("El Zorro - Descargador Kemono v1.1")
        # Increased default size to accommodate the new panel
        self.setGeometry(100, 100, 950, 600)

        self.setStyleSheet(DARK_STYLE)
        self.worker = None
        self.group_widgets = {} # Stores {'group_name': {'pbar': QProgressBar, 'label': ClickableLabel, 'total': int, 'completed': int}}

        # --- Central Widget and Main Layout (Horizontal Split) ---
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_h_layout = QHBoxLayout(central_widget) # Horizontal layout for left/right panels

        # --- Left Panel (Inputs, Buttons, Progress, Logs) ---
        left_v_layout = QVBoxLayout()

        # Input Area
        input_layout = QHBoxLayout()
        self.service_label = QLabel("Servicio:")
        self.service_input = QLineEdit()
        self.service_input.setPlaceholderText("fanbox, patreon, etc.")
        self.id_label = QLabel("ID Creador:")
        self.id_input = QLineEdit()
        self.id_input.setPlaceholderText("ID numérico del creador")
        input_layout.addWidget(self.service_label)
        input_layout.addWidget(self.service_input, 1)
        input_layout.addWidget(self.id_label)
        input_layout.addWidget(self.id_input, 1)
        left_v_layout.addLayout(input_layout)

        # Output Directory
        output_layout = QHBoxLayout()
        self.output_label = QLabel("Guardar en:")
        self.output_path_display = QLineEdit()
        self.output_path_display.setReadOnly(True)
        default_output = r"E:\El_Zorro\downloads"
        if not os.path.exists(os.path.join(os.path.expanduser("~"), "Downloads")):
             default_output = os.path.join(os.path.expanduser("~"), "ElZorro_Descargas")
        self.output_path_display.setText(os.path.abspath(default_output))
        self.browse_button = QPushButton("...")
        self.browse_button.setFixedWidth(30)
        self.browse_button.clicked.connect(self.browse_output_directory)
        output_layout.addWidget(self.output_label)
        output_layout.addWidget(self.output_path_display, 1)
        output_layout.addWidget(self.browse_button)
        left_v_layout.addLayout(output_layout)

        # --- Gemini API Key Input (only if not in .env) ---
        env_path = os.path.join(os.path.dirname(__file__), ".env")
        has_api_key = False
        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip().startswith("GEMINI_API_KEY=") and len(line.strip().split("=")[1]) > 0:
                            has_api_key = True
                            break
            except Exception:
                has_api_key = False

        if not has_api_key:
            gemini_layout = QHBoxLayout()
            self.gemini_label = QLabel("Gemini API Key:")
            self.gemini_input = QLineEdit()
            self.gemini_input.setPlaceholderText("Pega tu API key de Gemini aquí")
            self.gemini_save_button = QPushButton("Guardar en .env")
            self.gemini_save_button.clicked.connect(self.save_gemini_key_to_env)
            gemini_layout.addWidget(self.gemini_label)
            gemini_layout.addWidget(self.gemini_input, 1)
            gemini_layout.addWidget(self.gemini_save_button)
            left_v_layout.addLayout(gemini_layout)

        # Buttons
        button_layout = QHBoxLayout()
        self.download_button = QPushButton("Descargar")
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.setEnabled(False)
        button_layout.addWidget(self.download_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addStretch()
        left_v_layout.addLayout(button_layout)

        # Overall Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Listo")
        left_v_layout.addWidget(QLabel("Progreso General:"))
        left_v_layout.addWidget(self.progress_bar)

        # Log Area
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        left_v_layout.addWidget(QLabel("Registro:"))
        left_v_layout.addWidget(self.log_output, 1) # Stretch log area vertically

        # Add left panel layout to main horizontal layout
        left_panel_widget = QWidget()
        left_panel_widget.setLayout(left_v_layout)
        main_h_layout.addWidget(left_panel_widget, 2) # Give left panel more initial width (ratio 2:1)

        # --- Right Panel (Group List with Progress Bars) ---
        right_v_layout = QVBoxLayout()
        right_v_layout.addWidget(QLabel("Progreso por Grupo:"))

        self.group_scroll_area = QScrollArea()
        self.group_scroll_area.setWidgetResizable(True) # Important!
        self.group_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff) # Hide horizontal scrollbar

        # This inner widget will hold the actual list layout
        self.group_list_container = QWidget()
        self.group_list_layout = QVBoxLayout(self.group_list_container)
        self.group_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop) # Align items to the top
        self.group_list_layout.setContentsMargins(5, 5, 5, 5)
        self.group_list_layout.setSpacing(6)

        self.group_scroll_area.setWidget(self.group_list_container) # Put the container in the scroll area
        right_v_layout.addWidget(self.group_scroll_area, 1) # Let scroll area stretch

        # Add right panel layout to main horizontal layout
        right_panel_widget = QWidget()
        right_panel_widget.setLayout(right_v_layout)
        main_h_layout.addWidget(right_panel_widget, 1) # Right panel takes less initial width

        # --- Connect Signals ---
        self.download_button.clicked.connect(self.start_download)
        self.cancel_button.clicked.connect(self.cancel_download)

    def showEvent(self, event):
        super().showEvent(event)
        # Permite acceso global desde QApplication
        app = QApplication.instance()
        app.mainWindow = self

    def browse_output_directory(self):
        start_dir = self.output_path_display.text()
        if not os.path.isdir(start_dir):
            start_dir = os.path.expanduser("~")
        directory = QFileDialog.getExistingDirectory(self, "Seleccionar Directorio de Salida", start_dir)
        if directory:
            self.output_path_display.setText(os.path.abspath(directory))

    def save_gemini_key_to_env(self):
        key = self.gemini_input.text().strip()
        if not key:
            QMessageBox.warning(self, "API Key vacía", "Por favor, ingresa una API Key de Gemini válida.")
            return
        env_path = os.path.join(os.path.dirname(__file__), ".env")
        # Lee el .env actual
        lines = []
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        found = False
        for i, line in enumerate(lines):
            if line.startswith("GEMINI_API_KEY="):
                lines[i] = f"GEMINI_API_KEY={key}\n"
                found = True
        if not found:
            lines.append(f"GEMINI_API_KEY={key}\n")
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        QMessageBox.information(self, "Guardado", "API Key de Gemini guardada en .env correctamente.")

    def start_download(self):
        service = self.service_input.text().strip().lower()
        creator_id = self.id_input.text().strip()
        output_dir = self.output_path_display.text().strip()

        # Basic validation
        if not service or not creator_id or not output_dir:
            QMessageBox.warning(self, "Entrada incompleta", "Por favor, completa Servicio, ID Creador y Directorio de Salida.")
            return
        if not creator_id.isdigit(): # Basic check
             QMessageBox.warning(self, "ID Inválido", "El ID del creador debe ser numérico.")
             return

        # Check/Create output directory
        if not os.path.isdir(output_dir):
             reply = QMessageBox.question(self, "Directorio no existe", f"El directorio '{output_dir}' no existe.\n¿Crearlo?",
                                          QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.Yes)
             if reply == QMessageBox.StandardButton.Yes:
                 try: os.makedirs(output_dir, exist_ok=True)
                 except OSError as e:
                     QMessageBox.critical(self, "Error", f"No se pudo crear directorio: {e}")
                     return
             else: return

        if self.worker is not None and self.worker.isRunning():
            QMessageBox.information(self, "En progreso", "Ya hay una descarga en curso.")
            return

        # Reset UI state before starting
        self.log_output.clear()
        self.clear_group_list() # Clear the right panel
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Iniciando...")
        self.set_ui_running(True)

        # Create and connect worker
        self.worker = DownloadWorker(service, creator_id, output_dir)
        self.worker.log.connect(self.log_message)
        self.worker.progress.connect(self.update_overall_progress) # Overall progress bar
        self.worker.finished.connect(self.download_finished)
        self.worker.groups_ready.connect(self.populate_group_list)    # <<< Connect new signal
        self.worker.image_processed.connect(self.update_group_progress) # <<< Connect new signal

        self.worker.start()

    def cancel_download(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.log_message("Enviando señal de cancelación...")
            self.cancel_button.setEnabled(False)
            self.cancel_button.setText("Cancelando...")

    def clear_group_list(self):
        """Removes all widgets from the group list layout."""
        self.group_widgets.clear() # Clear the storage dictionary
        # Remove widgets from layout properly
        while self.group_list_layout.count():
            child = self.group_list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    @pyqtSlot(list)
    def populate_group_list(self, groups_data):
        """Receives group info from worker and builds the right panel list."""
        self.log_message(f"Recibida lista de {len(groups_data)} grupos.")
        self.clear_group_list() # Ensure it's empty before populating

        if not groups_data:
             # Optionally add a label indicating no groups found
             no_groups_label = QLabel("No se encontraron grupos con imágenes.")
             self.group_list_layout.addWidget(no_groups_label)
             self.group_widgets["_placeholder_"] = {'widget': no_groups_label} # Store placeholder widget info
             return

        for group_name, folder_path, total_images in groups_data:
            # Create a widget row for each group
            group_row_widget = QWidget()
            row_layout = QHBoxLayout(group_row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0) # Compact layout

            # Clickable Label for Name and Opening Folder
            group_label = ClickableLabel(group_name, folder_path)
            group_label.setWordWrap(True) # Allow wrapping if name is long
            # Connect the custom signal to the handler
            group_label.clicked_with_path.connect(self.open_folder_path)

            # Progress Bar for the Group
            pbar = QProgressBar()
            pbar.setRange(0, total_images if total_images > 0 else 1) # Avoid division by zero
            pbar.setValue(0)
            pbar.setTextVisible(True)
            pbar.setFormat(f"0 / {total_images}")
            # Set a fixed height and allow label to determine width needed
            pbar.setFixedHeight(18)
            pbar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)


            row_layout.addWidget(group_label, 1) # Label takes available space
            row_layout.addWidget(pbar, 1)      # Progress bar takes available space

            self.group_list_layout.addWidget(group_row_widget)

            # Store widgets for later updates
            self.group_widgets[group_name] = {
                'pbar': pbar,
                'label': group_label,
                'path': folder_path,
                'total': total_images,
                'completed': 0,
                'failed': 0,
                'skipped': 0
            }
        # Add a spacer at the end to push items up if the list is short
        # self.group_list_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))


    @pyqtSlot(str)
    def open_folder_path(self, path):
        """Opens the given folder path in the default file explorer."""
        self.log_message(f"Abriendo carpeta: {path}")
        if not os.path.isdir(path):
            self.log_message(f"Advertencia: La carpeta '{path}' no existe.")
            # Maybe try opening the parent directory?
            parent_dir = os.path.dirname(path)
            if os.path.isdir(parent_dir):
                 self.log_message(f"Intentando abrir directorio padre: {parent_dir}")
                 QDesktopServices.openUrl(QUrl.fromLocalFile(parent_dir))
            else:
                 QMessageBox.warning(self, "Carpeta no encontrada", f"La carpeta especificada no existe:\n{path}")
            return

        QDesktopServices.openUrl(QUrl.fromLocalFile(path))


    @pyqtSlot(str)
    def log_message(self, message):
        self.log_output.append(message)
        # Auto-scroll to bottom
        self.log_output.verticalScrollBar().setValue(self.log_output.verticalScrollBar().maximum())

    @pyqtSlot(int, int, int, int)
    def update_overall_progress(self, overall_progress, download_phase_progress, processed_count, total_count):
        """Updates the main progress bar at the bottom."""
        self.progress_bar.setValue(overall_progress)
        if total_count > 0:
             if overall_progress < 60 : # Fetching/Grouping phase
                 self.progress_bar.setFormat(f"Preparando... {overall_progress}%")
             else: # Download phase
                 self.progress_bar.setFormat(f"Descarga General: {processed_count}/{total_count} ({download_phase_progress}%) | Total: {overall_progress}%")
        elif overall_progress == 0:
             self.progress_bar.setFormat("Iniciando...")
        else: # If total_count is 0 but progress advances (e.g., only manifests created)
             self.progress_bar.setFormat(f"Procesando... {overall_progress}%")


    @pyqtSlot(str, bool, bool, bool)
    def update_group_progress(self, group_name, was_successful, was_skipped, failed_after_retry):
        """Updates the progress bar for a specific group."""
        if group_name in self.group_widgets:
            group_info = self.group_widgets[group_name]
            pbar = group_info['pbar']
            total = group_info['total']

            # Increment completed count only if not skipped
            if not was_skipped:
                group_info['completed'] += 1
            if failed_after_retry:
                 group_info['failed'] += 1
            if was_skipped:
                 group_info['skipped'] += 1

            # Calculate current value for progress bar (completed + skipped + failed)
            current_value = group_info['completed'] + group_info['skipped'] + group_info['failed']

            # Update progress bar value and text
            if total > 0:
                pbar.setValue(current_value)
                # Provide more detailed text
                text = f"{current_value}/{total}"
                details = []
                if group_info['completed'] > 0 : details.append(f"OK:{group_info['completed']}")
                if group_info['skipped'] > 0 : details.append(f"Skip:{group_info['skipped']}")
                if group_info['failed'] > 0 : details.append(f"Fail:{group_info['failed']}")
                if details: text += f" ({', '.join(details)})"
                pbar.setFormat(text)
            else:
                pbar.setFormat("N/A") # Or "0/0" if total is 0

            # Optional: Change progress bar color on failure? (More complex styling)
            # if failed_after_retry:
            #     pbar.setStyleSheet("QProgressBar::chunk { background-color: red; }")

        else:
            self.log_message(f"Advertencia: Intento de actualizar progreso para grupo desconocido '{group_name}'")

    @pyqtSlot(bool, str)
    def download_finished(self, success, message):
        self.log_message(f"--- FINALIZADO ---")
        self.log_message(message) # Log the final summary message

        # Show popup message based on outcome
        if "Cancelada" in message:
             QMessageBox.warning(self, "Cancelado", message)
             self.progress_bar.setFormat("Cancelado")
        elif not success and "Error" in message: # Distinguish errors from normal completion
             QMessageBox.critical(self, "Error", message)
             self.progress_bar.setFormat("Finalizado con Errores")
        elif not success: # Other non-success cases (e.g., failed downloads but process completed)
             QMessageBox.warning(self, "Finalizado con problemas", message)
             self.progress_bar.setFormat("Finalizado con Fallos")
        else: # Success
             QMessageBox.information(self, "Completado", message)
             self.progress_bar.setFormat("¡Completado!")

        self.set_ui_running(False) # Re-enable UI
        self.worker = None # Clear worker reference

    def set_ui_running(self, running):
        """Enable/disable UI elements based on running state."""
        self.download_button.setEnabled(not running)
        self.cancel_button.setEnabled(running)
        if not running: self.cancel_button.setText("Cancelar")
        self.service_input.setEnabled(not running)
        self.id_input.setEnabled(not running)
        self.browse_button.setEnabled(not running)
        self.output_path_display.setEnabled(not running)

    def closeEvent(self, event):
        if self.worker is not None and self.worker.isRunning():
            reply = QMessageBox.question(self, 'Descarga en progreso',
                                         "Una descarga está en curso. ¿Seguro que quieres salir?\nLa descarga será cancelada.",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.log_message("Cerrando aplicación y cancelando descarga...")
                self.cancel_download()
                if self.worker: self.worker.wait(500)
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

    @pyqtSlot(bool, str)
    def download_finished(self, success, message):
        self.log_message(f"--- FINALIZADO ---")
        # The 'message' already contains the detailed summary from the worker now
        self.log_message(message)

        # Determine final status for display
        final_status_text = ""
        if "Cancelada" in message:
             QMessageBox.warning(self, "Cancelado", message)
             final_status_text = "Cancelado"
        elif not success and ("fallidas" in message or "Error" in message): # Check for failure indicators
             QMessageBox.critical(self, "Finalizado con Errores", message)
             final_status_text = "Finalizado con Errores"
        elif not success: # Generic non-success (e.g., maybe only skips?)
            QMessageBox.warning(self, "Finalizado con Advertencias", message)
            final_status_text = "Finalizado con Advertencias"
        else: # Full Success
             QMessageBox.information(self, "Completado", message)
             final_status_text = "¡Completado!"

        self.progress_bar.setFormat(final_status_text) # Update overall progress bar text
        self.set_ui_running(False) # Re-enable UI
        self.worker = None

    def show_gemini_groups_popup(self, gemini_groups):
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QLabel, QPushButton
        dialog = QDialog(self)
        dialog.setWindowTitle("Organización IA: Grupos sugeridos por Gemini")
        layout = QVBoxLayout(dialog)
        label = QLabel("Grupos y posts sugeridos por Gemini:")
        layout.addWidget(label)
        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Grupo (Carpeta)", "Posts incluidos"])
        groups = gemini_groups.get('groups', [])
        table.setRowCount(len(groups))
        for i, group in enumerate(groups):
            group_name = group.get('folder', '')
            posts = group.get('order', [])
            table.setItem(i, 0, QTableWidgetItem(group_name))
            table.setItem(i, 1, QTableWidgetItem("\n".join(posts)))
        table.resizeColumnsToContents()
        layout.addWidget(table)
        btn = QPushButton("Cerrar")
        btn.clicked.connect(dialog.accept)
        layout.addWidget(btn)
        dialog.setLayout(layout)
        dialog.exec()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    # Set application name for better integration (optional)
    app.setApplicationName("ElZorroDownloader")
    app.setOrganizationName("YourOrg") # Replace if desired

    window = MainWindow()
    window.show()
    sys.exit(app.exec())