# worker.py
import os
import time
import json
import traceback
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, List, Tuple, Optional

# Dependencias de PyQt e Hilos
from PyQt6.QtCore import QThread, pyqtSignal, QMutex
from concurrent.futures import ThreadPoolExecutor, as_completed

# Dependencias de la Lógica de la Aplicación
from api_client import KemonoAPI
from grouper import group_posts_by_title # Mantenemos el fallback
from utils import sanitize_filename, ensure_dir, get_base_url

# Dependencias de Google Gemini y Pydantic
import google.genai as genai
from pydantic import BaseModel, Field, ValidationError

# --- Constantes ---
MAX_CONCURRENT_DOWNLOADS = 5
FILENAME_PADDING = 4
MANIFEST_FILENAME = "_manifest.txt"

# --- Modelos Pydantic para la IA de Gemini (Clave para la solución) ---
class PostForGemini(BaseModel):
    id: str
    title: str

class GeminiGroupResult(BaseModel):
    folder: str = Field(..., description="Un nombre de carpeta descriptivo y sanitizado para el grupo.")
    order: List[str] = Field(..., description="Una lista de los IDs de los posts en el orden lógico para este grupo.")

class GeminiOrganization(BaseModel):
    groups: List[GeminiGroupResult]

# ==============================================================================
# IMPLEMENTACIÓN DE GEMINI CON response_schema (MÉTODO RECOMENDADO Y ROBUSTO)
# ==============================================================================
def organize_posts_with_gemini(posts: List[Dict], api_key: str, log_func) -> Dict:
    """
    Organiza posts usando Gemini forzando un esquema de respuesta JSON con Pydantic.
    Este es el método más robusto y recomendado.
    """
    log_func("[Gemini IA] Iniciando organización con esquema de respuesta forzado...")
    if not posts:
        log_func("[Gemini IA] No hay posts para organizar. Omitiendo.")
        return {"groups": []}

    try:
        # 1. Instanciar el cliente
        client = genai.Client(api_key=api_key)

        # 2. Preparar datos para el prompt
        posts_for_prompt = [PostForGemini(id=p['id'], title=p['title']).model_dump() for p in posts if p.get('title')]
        if not posts_for_prompt:
            log_func("[Gemini IA] Ningún post tenía título para ser procesado. Omitiendo.")
            return {"groups": []}

        log_func(f"[Gemini IA] Enviando {len(posts_for_prompt)} posts al modelo Gemini Flash...")
        
        # 3. PROMPT SIMPLIFICADO: Nos enfocamos en la tarea, no en el formato.
        prompt = f"""
Eres un asistente experto en organizar descargas de arte digital.
Tu tarea es analizar la siguiente lista de posts de un artista y agruparlos en carpetas lógicas.

REGLAS DE AGRUPACIÓN:
1. Agrupa los posts que pertenezcan a la misma historia, serie, cómic, o conjunto de "trabajo en progreso" (WIP).
2. Los posts que no parezcan pertenecer a ningún grupo claro deben ir a una carpeta llamada "Varios".
3. Ordena los IDs de los posts dentro de cada grupo de forma lógica (ej. por número de parte si está en el título).

LISTA DE POSTS A ORGANIZAR:
{json.dumps(posts_for_prompt, indent=2, ensure_ascii=False)}
"""

        # 4. CONFIGURACIÓN CON response_schema (LA CLAVE DE LA SOLUCIÓN)
        generation_config = {
            "response_mime_type": "application/json",
            "response_schema": GeminiOrganization,  # Pasamos nuestro modelo Pydantic directamente
            "temperature": 0.2
        }

        # 5. Llamar a la API con el modelo Flash y la configuración estricta
        response = client.models.generate_content(
            model='gemini-1.5-flash-latest', # Usando el modelo Flash más reciente
            contents=prompt,
            config=generation_config
        )

        # 6. Usar el resultado ya parseado por la librería de Google
        if response.parsed:
            log_func(f"[Gemini IA] ¡Éxito! Gemini ha devuelto un objeto estructurado con {len(response.parsed.groups)} grupos.")
            # El objeto ya es una instancia de GeminiOrganization, solo lo convertimos a dict
            return response.parsed.model_dump()
        else:
            # Esto ocurre si la IA, a pesar de todo, genera algo que no cumple el esquema.
            log_func("[Gemini IA] Error: La IA devolvió datos que no coinciden con el esquema solicitado.")
            log_func(f"[Gemini IA] Respuesta de texto recibida (si existe): {response.text[:500]}")
            raise ValueError("La respuesta de Gemini no pudo ser parseada según el esquema.")
            
    except Exception as e:
        log_func(f"[Gemini IA] Ha ocurrido un error al comunicarse con la API de Gemini: {e}")
        raise

# ==============================================================================
# CLASE DEL WORKER (EL RESTO DEL CÓDIGO PERMANECE IGUAL, ES MODULAR)
# ==============================================================================
class DownloadWorker(QThread):
    progress = pyqtSignal(int, int, int, int)
    log = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    groups_ready = pyqtSignal(list)
    image_processed = pyqtSignal(str, bool, bool, bool)

    def __init__(self, service: str, creator_id: str, output_dir: str):
        super().__init__()
        self.service = service
        self.creator_id = creator_id
        self.output_dir = Path(output_dir)
        self.api = KemonoAPI()
        self._is_cancelled = False
        self.site_base_url = get_base_url(self.api.base_url)
        self.processed_urls_in_session = set()
        self.counter_mutex = QMutex()
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
        all_tasks = []
        group_info_for_gui = []
        manifest_lines_by_group = {}

        sanitized_creator_folder = sanitize_filename(f"{self.service}_{self.creator_id}")
        base_user_dir = self.output_dir / sanitized_creator_folder
        ensure_dir(str(base_user_dir))
        self.log.emit(f"Directorio base del creador: {base_user_dir}")

        sorted_group_names = sorted(grouped_posts.keys())

        for group_name in sorted_group_names:
            posts_in_group = grouped_posts[group_name]
            group_dir = base_user_dir / group_name
            ensure_dir(str(group_dir))
            manifest_path = group_dir / MANIFEST_FILENAME
            manifest_lines_by_group[group_name] = []

            images_in_group = []
            for post in posts_in_group:
                post_id = post.get('id', 'unknown_id')
                if post.get('file') and post['file'].get('path'):
                    file_info = post['file']
                    images_in_group.append({
                        'url': f"{self.site_base_url}{file_info['path']}",
                        'original_name': file_info.get('name', 'file'),
                        'post_id': post_id,
                        'path_in_api': file_info['path'],
                    })
                for attachment in post.get('attachments', []):
                    if attachment.get('path'):
                        images_in_group.append({
                            'url': f"{self.site_base_url}{attachment['path']}",
                            'original_name': attachment.get('name', f'att_{attachment.get("id")}'),
                            'post_id': post_id,
                            'path_in_api': attachment['path'],
                        })

            group_image_count = len(images_in_group)
            if group_image_count > 0:
                 group_info_for_gui.append((group_name, str(group_dir), group_image_count))

            for seq_index, img_data in enumerate(images_in_group):
                seq_num = seq_index + 1
                seq_str = f"{seq_num:0{FILENAME_PADDING}d}"
                original_extension = Path(img_data['path_in_api']).suffix or ".jpg"
                sanitized_original_name = sanitize_filename(img_data['original_name'], replace_space_with='_')
                new_filename = f"{seq_str}{original_extension}"
                save_path = group_dir / new_filename

                task = {
                    'url': img_data['url'],
                    'save_path': save_path,
                    'group_name': group_name,
                    'identifier': f"'{new_filename}' (Grupo: '{group_name}', Original: '{sanitized_original_name}', Post: {img_data['post_id']})"
                }
                all_tasks.append(task)

                manifest_line = f"{new_filename} : {sanitized_original_name} (PostID: {img_data['post_id']})"
                manifest_lines_by_group[group_name].append(manifest_line)

            if manifest_lines_by_group[group_name]:
                 try:
                     with open(manifest_path, 'w', encoding='utf-8') as f_manifest:
                         f_manifest.write("# Mapping: Sequential Filename : Original Filename (PostID: ...)\n")
                         f_manifest.write("-" * 60 + "\n")
                         f_manifest.write("\n".join(manifest_lines_by_group[group_name]))
                     self.log.emit(f"Manifest creado para '{group_name}': {manifest_path.name}")
                 except IOError as e:
                     self.log.emit(f"ERROR: No se pudo escribir el manifest para '{group_name}': {e}")

        return all_tasks, group_info_for_gui

    def _download_task_runner(self, task_info: Dict) -> Dict:
        url = task_info['url']
        save_path = task_info['save_path']
        identifier = task_info['identifier']
        group_name = task_info['group_name']

        if self.is_cancelled():
            return {'url': url, 'success': False, 'cancelled': True, 'skipped': False, 'identifier': identifier, 'group_name': group_name}

        success = self.api.download_image(
            url, str(save_path),
            check_cancel=self.is_cancelled
        )

        return {
            'url': url,
            'success': success,
            'cancelled': self.is_cancelled() and not success,
            'skipped': False,
            'identifier': identifier,
            'group_name': group_name
        }

    def run(self):
        self.log.emit(f"Iniciando proceso para {self.service}/{self.creator_id}...")
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
            if self.is_cancelled():
                self.finished.emit(False, "Cancelado durante obtención de posts.")
                return
            if not all_posts:
                self.finished.emit(False, "No se encontraron posts o hubo un error en la API.")
                return
            self.log.emit(f"Fase 1 completa. {len(all_posts)} posts recuperados.")
            self.progress.emit(50, 0, 0, 0)

            # --- 2. Group posts ---
            self.log.emit("Fase 2: Agrupando posts y preparando tareas...")
            
            env_path = Path(__file__).parent.parent / '.env'
            if not env_path.exists():
                env_path = Path(__file__).parent / '.env'
            load_dotenv(dotenv_path=env_path)
            gemini_key = os.getenv("GEMINI_API_KEY")

            grouped_posts = None
            if gemini_key:
                try:
                    gemini_result = organize_posts_with_gemini(all_posts, gemini_key, self.log.emit)
                    
                    if gemini_result and gemini_result.get("groups"):
                        posts_by_id = {p['id']: p for p in all_posts}
                        grouped_posts = {}
                        for group_info in gemini_result["groups"]:
                            folder_name = sanitize_filename(group_info["folder"])
                            post_list = [posts_by_id[post_id] for post_id in group_info["order"] if post_id in posts_by_id]
                            if post_list:
                                grouped_posts[folder_name] = post_list
                        self.log.emit("[Gemini IA] Grupos de IA procesados y listos para la descarga.")
                
                except Exception as e:
                    self.log.emit(f"[ADVERTENCIA] La organización con Gemini IA falló: {e}. Se usará el método de agrupación por título.")
            else:
                self.log.emit("[Info] No se encontró la API Key de Gemini. Se usará la agrupación por título estándar.")

            if grouped_posts is None:
                self.log.emit("Usando el método de agrupación por título...")
                grouped_posts = group_posts_by_title(all_posts)

            if not grouped_posts:
                self.finished.emit(True, "Completado. No se encontraron posts con imágenes para agrupar.")
                return

            all_download_tasks, group_info_for_gui = self._prepare_download_tasks_and_manifests(grouped_posts)
            total_images_to_process = len(all_download_tasks)

            if total_images_to_process == 0:
                 self.log.emit("No hay imágenes nuevas para descargar.")
                 self.groups_ready.emit(group_info_for_gui)
                 time.sleep(0.1)
                 self.finished.emit(True, "Completado. No había imágenes nuevas para descargar.")
                 return

            self.log.emit(f"Fase 2 completa. {len(group_info_for_gui)} grupos listos. {total_images_to_process} imágenes candidatas.")
            self.groups_ready.emit(group_info_for_gui)
            self.progress.emit(60, 0, 0, total_images_to_process)

            # --- 3. Execute Downloads Concurrently ---
            self.log.emit(f"Fase 3: Iniciando descarga concurrente (máx {MAX_CONCURRENT_DOWNLOADS})...")
            with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_DOWNLOADS) as executor:
                futures = []
                for task in all_download_tasks:
                    if self.is_cancelled(): break
                    url, save_path, identifier, group_name = task['url'], task['save_path'], task['identifier'], task['group_name']
                    skipped = False
                    if url in self.processed_urls_in_session:
                        skipped, self.total_images_skipped_duplicate = True, self.total_images_skipped_duplicate + 1
                    elif save_path.exists():
                        skipped, self.total_images_skipped_exists = True, self.total_images_skipped_exists + 1
                        self.processed_urls_in_session.add(url)
                    
                    if skipped:
                        self.images_processed_count += 1
                        self.image_processed.emit(group_name, False, True, False)
                    else:
                        futures.append(executor.submit(self._download_task_runner, task))

                for future in as_completed(futures):
                    if self.is_cancelled(): future.cancel()
                    try:
                        result = future.result()
                        self.images_processed_count += 1
                        was_successful, was_cancelled = result['success'], result['cancelled']
                        failed_after_retry = not was_successful and not was_cancelled

                        if was_successful:
                            self.total_images_downloaded += 1
                            self.processed_urls_in_session.add(result['url'])
                            self.log.emit(f"OK: {result['identifier']}")
                        elif was_cancelled:
                            self.log.emit(f"CANCELADO: {result['identifier']}")
                        else:
                            self.total_images_failed += 1
                            self.log.emit(f"FALLO: {result['identifier']}")

                        self.image_processed.emit(result['group_name'], was_successful, False, failed_after_retry)
                    except Exception as exc:
                        self.images_processed_count += 1
                        self.total_images_failed += 1
                        self.log.emit(f"ERROR procesando tarea: {exc}")
                        self.image_processed.emit("Desconocido", False, False, True)
                    
                    if total_images_to_process > 0:
                        dl_prog = int((self.images_processed_count / total_images_to_process) * 100)
                        ov_prog = 60 + int(dl_prog * 0.4)
                        self.progress.emit(min(ov_prog, 100), min(dl_prog, 100), self.images_processed_count, total_images_to_process)
                    if self.is_cancelled(): break

            # --- 4. Finalization ---
            self.log.emit("Fase de descargas completada.")
            if not self.is_cancelled():
                 self.progress.emit(100, 100, self.images_processed_count, total_images_to_process)

            summary_parts = [f"{self.total_images_downloaded} descargadas"]
            if self.total_images_skipped_exists > 0: summary_parts.append(f"{self.total_images_skipped_exists} omitidas (existían)")
            if self.total_images_skipped_duplicate > 0: summary_parts.append(f"{self.total_images_skipped_duplicate} omitidas (duplicadas)")
            if self.total_images_failed > 0: summary_parts.append(f"{self.total_images_failed} fallidas")
            summary = ", ".join(summary_parts) + "."

            final_msg = f"Operación Cancelada. Resumen: {summary}" if self.is_cancelled() else f"Proceso Completado. Resumen: {summary}"
            self.log.emit(final_msg)
            self.finished.emit(not self.is_cancelled() and self.total_images_failed == 0, final_msg)

        except Exception as e:
            self.log.emit(f"Error crítico inesperado en el worker: {e}")
            self.log.emit(traceback.format_exc())
            self.finished.emit(False, f"Error crítico: {e}")