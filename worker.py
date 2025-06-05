# worker.py
import os
import time
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal, QMutex, QMutexLocker # Added QMutex for thread safety
from concurrent.futures import ThreadPoolExecutor, as_completed
from api_client import KemonoAPI
from grouper import group_posts_by_title
from utils import sanitize_filename, ensure_dir, get_base_url
from typing import Dict, List, Tuple

MAX_CONCURRENT_DOWNLOADS = 5
FILENAME_PADDING = 4 # How many digits for sequential filenames (e.g., 4 -> 0001, 0002)
MANIFEST_FILENAME = "_manifest.txt"

class DownloadWorker(QThread):
    # Overall Progress: overall(%), download_phase(%), processed_img_count, total_img_count
    progress = pyqtSignal(int, int, int, int)
    # Log messages
    log = pyqtSignal(str)
    # Final status: Success (True/False), Final Message
    finished = pyqtSignal(bool, str)
    # GUI Update Signals
    # Emits list of tuples: [(group_name, group_folder_path, total_images_in_group), ...]
    groups_ready = pyqtSignal(list)
    # Emits updates after an image is processed (downloaded, skipped, failed)
    # group_name, was_successful, was_skipped (exists/duplicate), failed_after_retry
    image_processed = pyqtSignal(str, bool, bool, bool)

    def __init__(self, service: str, creator_id: str, output_dir: str):
        super().__init__()
        self.service = service
        self.creator_id = creator_id
        self.output_dir = Path(output_dir)
        self.api = KemonoAPI()
        self._is_cancelled = False
        self.site_base_url = get_base_url(self.api.base_url)
        # Use a set for processed URLs (adding should be atomic enough from main thread)
        self.processed_urls_in_session = set()
        # Mutex for thread-safe access to shared counters if needed (though currently updated sequentially)
        self.counter_mutex = QMutex()
        # Counters - reset at start
        self.total_images_downloaded = 0
        self.total_images_skipped_duplicate = 0
        self.total_images_skipped_exists = 0
        self.total_images_failed = 0
        self.images_processed_count = 0


    def is_cancelled(self) -> bool:
        return self._is_cancelled

    def cancel(self):
        self.log.emit("Solicitud de cancelación recibida...")
        self._is_cancelled = True

    def _prepare_download_tasks_and_manifests(self, grouped_posts: Dict[str, List[Dict]]) -> Tuple[List[Dict], List[Tuple[str, str, int]]]:
        """
        Prepares download tasks with sequential filenames and generates manifest files.
        Returns:
            - List of task dictionaries for the executor.
            - List of tuples for GUI: (group_name, group_folder_path, image_count).
        """
        all_tasks = []
        group_info_for_gui = []
        manifest_lines_by_group = {} # Store lines before writing

        # Sanitize the creator folder name
        sanitized_creator_folder = sanitize_filename(f"{self.service}_{self.creator_id}")
        base_user_dir = self.output_dir / sanitized_creator_folder
        ensure_dir(str(base_user_dir))
        self.log.emit(f"Directorio base del creador: {base_user_dir}")

        # Sort groups alphabetically by name for consistent processing order (optional)
        sorted_group_names = sorted(grouped_posts.keys())

        for group_name in sorted_group_names:
            posts_in_group = grouped_posts[group_name]
            # Group name comes pre-sanitized from grouper.py
            group_dir = base_user_dir / group_name
            ensure_dir(str(group_dir))
            manifest_path = group_dir / MANIFEST_FILENAME
            manifest_lines_by_group[group_name] = [] # Initialize manifest lines for this group

            images_in_group = []
            # 1. Collect all image sources within the group, preserving order
            # Posts are already sorted by 'published' date in grouper.py
            for post in posts_in_group:
                post_id = post.get('id', 'unknown_id')
                # Add main 'file' if exists
                if post.get('file') and post['file'].get('path'):
                    file_info = post['file']
                    images_in_group.append({
                        'url': f"{self.site_base_url}{file_info['path']}",
                        'original_name': file_info.get('name', 'file'),
                        'post_id': post_id,
                        'path_in_api': file_info['path'], # Needed for extension
                        'internal_index': 0 # 0 for main file
                    })
                # Add 'attachments'
                for idx, attachment in enumerate(post.get('attachments', [])):
                    if attachment.get('path'):
                        images_in_group.append({
                            'url': f"{self.site_base_url}{attachment['path']}",
                            'original_name': attachment.get('name', f'att_{idx}'),
                            'post_id': post_id,
                            'path_in_api': attachment['path'], # Needed for extension
                            'internal_index': idx + 1 # 1+ for attachments
                        })

            # 2. Generate sequential filenames and tasks, prepare manifest
            group_image_count = len(images_in_group)
            if group_image_count > 0:
                 group_info_for_gui.append((group_name, str(group_dir), group_image_count))

            for seq_index, img_data in enumerate(images_in_group):
                seq_num = seq_index + 1
                # Format sequential number with padding (e.g., 0001)
                seq_str = f"{seq_num:0{FILENAME_PADDING}d}"
                # Get extension safely
                original_extension = Path(img_data['path_in_api']).suffix
                if not original_extension: original_extension = ".jpg" # Fallback extension
                # Sanitize original name *just in case* it's used in manifest
                sanitized_original_name = sanitize_filename(img_data['original_name'], replace_space_with='_')

                # New filename based on sequence
                new_filename = f"{seq_str}{original_extension}"
                save_path = group_dir / new_filename

                # Prepare task dictionary
                task = {
                    'url': img_data['url'],
                    'save_path': save_path,
                    'group_name': group_name, # Needed for GUI updates
                    'identifier': f"'{new_filename}' (Grupo: '{group_name}', Original: '{sanitized_original_name}', Post: {img_data['post_id']})"
                }
                all_tasks.append(task)

                # Prepare manifest line
                manifest_line = f"{new_filename} : {sanitized_original_name} (PostID: {img_data['post_id']})"
                manifest_lines_by_group[group_name].append(manifest_line)

            # 3. Write manifest file for the group (do this *before* starting downloads for the group)
            if manifest_lines_by_group[group_name]:
                 try:
                     with open(manifest_path, 'w', encoding='utf-8') as f_manifest:
                         f_manifest.write("# Mapping: Sequential Filename : Original Filename (PostID: ...)\n")
                         f_manifest.write("-" * 60 + "\n")
                         f_manifest.write("\n".join(manifest_lines_by_group[group_name]))
                     self.log.emit(f"Manifest creado/actualizado para '{group_name}': {manifest_path.name}")
                 except IOError as e:
                     self.log.emit(f"ERROR: No se pudo escribir el manifest '{manifest_path.name}' para el grupo '{group_name}': {e}")

        return all_tasks, group_info_for_gui


    def _download_task_runner(self, task_info: Dict) -> Dict:
        """The function executed by each download thread."""
        url = task_info['url']
        save_path = task_info['save_path']
        identifier = task_info['identifier']
        group_name = task_info['group_name'] # Get group name

        # Check cancellation *before* starting download attempt
        if self.is_cancelled():
            return {'url': url, 'success': False, 'cancelled': True, 'skipped': False, 'identifier': identifier, 'group_name': group_name}

        # Perform the download using the API client's method with retries
        success = self.api.download_image(
            url, str(save_path),
            log_callback=None, # Log from main thread based on result
            check_cancel=self.is_cancelled,
            max_retries=2,
            retry_delay=3.0
        )

        return {
            'url': url,
            'success': success,
            'cancelled': self.is_cancelled() and not success, # Cancelled during download or wait
            'skipped': False, # Not skipped by this runner function
            'identifier': identifier,
            'group_name': group_name # Pass group name back
        }

    def run(self):
        """Main execution logic for the worker thread."""
        self.log.emit(f"Iniciando proceso para {self.service}/{self.creator_id}...")
        # Reset state for this run
        self._is_cancelled = False
        self.processed_urls_in_session.clear()
        self.total_images_downloaded = 0
        self.total_images_skipped_duplicate = 0
        self.total_images_skipped_exists = 0
        self.total_images_failed = 0
        self.images_processed_count = 0

        try:
            # --- 1. Fetch all posts ---
            self.log.emit("Fase 1: Obteniendo lista de posts...")
            self.progress.emit(0, 0, 0, 0)
            all_posts = self.api.get_all_creator_posts(
                self.service, self.creator_id,
                progress_callback=lambda p, d: self.progress.emit(p, 0, 0, 0),
                log_callback=self.log.emit,
                check_cancel=self.is_cancelled
            )
            # Handle cancellation/failure during fetch
            if self.is_cancelled():
                self.log.emit("Operación cancelada durante la obtención de posts.")
                self.finished.emit(False, "Cancelado durante obtención de posts.")
                return
            if not all_posts:
                self.log.emit("No se encontraron posts o hubo un error en la API.")
                self.finished.emit(False, "No se encontraron posts o error API.")
                return
            self.log.emit(f"Fase 1 completa. {len(all_posts)} posts recuperados.")
            self.progress.emit(50, 0, 0, 0)

            # --- 2. Filter, Group, Prepare Tasks & Manifests ---
            self.log.emit("Fase 2: Filtrando, agrupando, ordenando y preparando tareas...")
            grouped_posts = group_posts_by_title(all_posts)
            if not grouped_posts:
                 self.log.emit("No se encontraron posts con imágenes válidas tras agrupar.")
                 self.finished.emit(True, "Completado. No había imágenes válidas.")
                 return

            # This function now also writes manifests and returns GUI info
            all_download_tasks, group_info_for_gui = self._prepare_download_tasks_and_manifests(grouped_posts)
            total_images_to_process = len(all_download_tasks)

            if total_images_to_process == 0:
                 self.log.emit("Preparación completada. No hay imágenes para descargar (posiblemente todas ya existían o eran duplicadas?).")
                 # We might have created empty folders and manifests, which is okay.
                 # Let's signal the GUI anyway so it can show the (empty) groups.
                 self.groups_ready.emit(group_info_for_gui)
                 time.sleep(0.1) # Give GUI time to update
                 self.finished.emit(True, "Completado. No había imágenes nuevas para descargar.")
                 return

            self.log.emit(f"Fase 2 completa. {len(group_info_for_gui)} grupos listos. {total_images_to_process} imágenes candidatas.")
            # Signal GUI that groups are ready
            self.groups_ready.emit(group_info_for_gui)
            self.progress.emit(60, 0, 0, total_images_to_process) # Start download phase at 60%

            # --- 3. Execute Downloads Concurrently ---
            self.log.emit(f"Fase 3: Iniciando descarga concurrente (máx {MAX_CONCURRENT_DOWNLOADS})...")
            futures = []
            with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_DOWNLOADS) as executor:
                # Submit tasks after checking duplicates/existence
                for task in all_download_tasks:
                    if self.is_cancelled(): break

                    url = task['url']
                    save_path = task['save_path']
                    identifier = task['identifier']
                    group_name = task['group_name']
                    skipped = False
                    success = False # Default state for this task

                    # Check 1: Already processed URL in this session?
                    if url in self.processed_urls_in_session:
                        self.log.emit(f"OMITIDO (URL Duplicada Sesión): {identifier}")
                        skipped = True
                        self.total_images_skipped_duplicate += 1
                    # Check 2: File already exists on disk?
                    elif save_path.exists():
                        self.log.emit(f"OMITIDO (Ya Existe): {identifier}")
                        skipped = True
                        self.total_images_skipped_exists += 1
                        self.processed_urls_in_session.add(url) # Mark as processed if exists
                    else:
                        # If not skipped, submit the download task
                        future = executor.submit(self._download_task_runner, task)
                        futures.append(future)
                        # Don't update progress/emit signal here, wait for future completion

                    # If skipped, update progress and emit GUI signal immediately
                    if skipped:
                        self.images_processed_count += 1
                        # Emit progress for GUI (group specific)
                        self.image_processed.emit(group_name, False, True, False) # group, success=no, skipped=yes, failed=no
                        # Update overall progress
                        if total_images_to_process > 0:
                            dl_prog = int((self.images_processed_count / total_images_to_process) * 100)
                            ov_prog = 60 + int((self.images_processed_count / total_images_to_process) * 40)
                            self.progress.emit(min(ov_prog, 100), min(dl_prog, 100), self.images_processed_count, total_images_to_process)

                self.log.emit(f"Se han enviado {len(futures)} tareas de descarga reales al ejecutor.")

                # Process results as they complete
                for future in as_completed(futures):
                    if self.is_cancelled() and not future.done(): future.cancel()

                    try:
                        result = future.result()
                        self.images_processed_count += 1
                        group_name = result['group_name']
                        was_successful = result['success']
                        was_cancelled = result['cancelled']
                        was_skipped = result['skipped'] # Should be false here
                        failed_after_retry = not was_successful and not was_cancelled and not was_skipped

                        # Update counters safely (optional mutex use)
                        # with QMutexLocker(self.counter_mutex): # Usually not needed if only this thread modifies
                        if was_successful:
                            self.total_images_downloaded += 1
                            self.processed_urls_in_session.add(result['url'])
                            self.log.emit(f"OK: {result['identifier']}")
                        elif was_cancelled:
                            self.log.emit(f"CANCELADO: {result['identifier']}")
                        elif failed_after_retry:
                            self.total_images_failed += 1
                            self.log.emit(f"FALLO (tras reintentos): {result['identifier']}")

                        # Emit progress for GUI (group specific) regardless of outcome
                        self.image_processed.emit(group_name, was_successful, was_skipped, failed_after_retry)

                        # Update overall progress bar
                        if total_images_to_process > 0:
                            dl_prog = int((self.images_processed_count / total_images_to_process) * 100)
                            ov_prog = 60 + int((self.images_processed_count / total_images_to_process) * 40)
                            self.progress.emit(min(ov_prog, 100), min(dl_prog, 100), self.images_processed_count, total_images_to_process)

                    except Exception as exc:
                        # This catches errors in future.result() or processing the result
                        self.images_processed_count += 1
                        self.total_images_failed += 1
                        # Try to get group name if possible from the future's task if stored differently, otherwise use placeholder
                        group_name_for_error = "Desconocido"
                        # TODO: Find a way to get group_name if future.result() fails (e.g., store task info with future)
                        self.log.emit(f"ERROR al procesar resultado de tarea para grupo {group_name_for_error}: {exc}")
                        self.image_processed.emit(group_name_for_error, False, False, True) # Emit failure signal
                        # Update overall progress
                        if total_images_to_process > 0:
                            dl_prog = int((self.images_processed_count / total_images_to_process) * 100)
                            ov_prog = 60 + int((self.images_processed_count / total_images_to_process) * 40)
                            self.progress.emit(min(ov_prog, 100), min(dl_prog, 100), self.images_processed_count, total_images_to_process)

                    if self.is_cancelled(): break # Check cancellation within the results loop

            # --- 4. Finalization ---
            self.log.emit("Fase 3 (Descargas) completada.")
            if not self.is_cancelled() and self.images_processed_count >= total_images_to_process:
                 self.progress.emit(100, 100, self.images_processed_count, total_images_to_process)

            summary_parts = [f"{self.total_images_downloaded} descargadas"]
            if self.total_images_skipped_exists > 0: summary_parts.append(f"{self.total_images_skipped_exists} omitidas (existían)")
            if self.total_images_skipped_duplicate > 0: summary_parts.append(f"{self.total_images_skipped_duplicate} omitidas (duplicadas)")
            if self.total_images_failed > 0: summary_parts.append(f"{self.total_images_failed} fallidas (tras reintentos)")
            summary = ", ".join(summary_parts) + "."

            if self.is_cancelled():
                final_msg = f"Operación Cancelada. Resumen: {summary}"
            else:
                final_msg = f"Proceso Completado. Resumen: {summary}"

            self.log.emit(final_msg)
            self.finished.emit(not self.is_cancelled() and self.total_images_failed == 0, final_msg)

        except Exception as e:
            self.log.emit(f"Error crítico inesperado en el worker: {e}")
            import traceback
            self.log.emit(traceback.format_exc())
            self.finished.emit(False, f"Error crítico: {e}")