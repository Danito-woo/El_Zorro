# api_client.py
import requests
import time
import os
from typing import List, Dict, Optional, Callable
from requests.exceptions import RequestException, HTTPError

API_BASE_URL = "https://kemono.su/api/v1/"
POSTS_PER_PAGE = 50

class KemonoAPI:
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        # Use a proper user agent
        self.session.headers.update({"User-Agent": "ElZorroDownloader/1.1 (User Request)"})

    def get_all_creator_posts(self, service: str, creator_id: str,
                              progress_callback: Optional[Callable[[int, int], None]] = None,
                              log_callback: Optional[Callable[[str], None]] = None,
                              check_cancel: Optional[Callable[[], bool]] = None) -> List[Dict]:
        # --- Function body remains the same as before ---
        # ... (copy the existing get_all_creator_posts logic here) ...
        all_posts = []
        offset = 0
        page_num = 1
        estimated_total = None

        while True:
            if check_cancel and check_cancel():
                if log_callback: log_callback("Operación cancelada por el usuario.")
                return []

            url = f"{self.base_url}{service}/user/{creator_id}"
            params = {'o': offset}
            current_url = f"{url}?o={offset}" # For logging
            if log_callback: log_callback(f"Consultando página {page_num}: {current_url}")

            try:
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                posts_page = response.json()

                if not posts_page:
                    if log_callback: log_callback("No se encontraron más posts.")
                    break

                current_count = len(all_posts) + len(posts_page)
                if progress_callback:
                     # Rough estimation logic (same as before)
                    if estimated_total is None and len(posts_page) == POSTS_PER_PAGE:
                         estimated_total = current_count + POSTS_PER_PAGE # Guess one more page
                    elif estimated_total is None:
                         estimated_total = current_count # This was the last page
                    elif len(posts_page) < POSTS_PER_PAGE:
                         estimated_total = current_count # This is definitely the last page

                    if estimated_total and estimated_total > 0:
                       # Fetching posts phase contributes up to 50% of overall progress
                       progress = min(int((current_count / estimated_total) * 50), 50)
                       progress_callback(progress, 0) # 0 for download phase progress yet

                all_posts.extend(posts_page)
                if log_callback: log_callback(f"Recibidos {len(posts_page)} posts. Total acumulado: {len(all_posts)}")

                if len(posts_page) < POSTS_PER_PAGE:
                    break

                offset += POSTS_PER_PAGE
                page_num += 1
                # Be polite to the API
                time.sleep(0.6) # Slightly increased delay

            except HTTPError as e:
                if e.response.status_code == 404:
                    if log_callback: log_callback(f"Error 404: Creador o servicio '{service}/{creator_id}' no encontrado.")
                else:
                    if log_callback: log_callback(f"Error HTTP {e.response.status_code} al obtener posts: {e}")
                return [] # Return empty on error
            except RequestException as e:
                if log_callback: log_callback(f"Error de conexión/red al obtener posts: {e}")
                return []
            except Exception as e:
                if log_callback: log_callback(f"Error inesperado al procesar respuesta API: {e}")
                return []

        if log_callback: log_callback(f"Recuperación de posts completa. Total: {len(all_posts)} posts.")
        return all_posts


    def download_image(self, url: str, save_path: str,
                       log_callback: Optional[Callable[[str], None]] = None,
                       check_cancel: Optional[Callable[[], bool]] = None,
                       max_retries: int = 2, # <<< Added Retry parameter
                       retry_delay: float = 3.0 # <<< Added Delay parameter
                       ) -> bool:
        """Downloads a single image with retry logic."""
        attempt = 0
        while attempt <= max_retries:
            if check_cancel and check_cancel():
                return False # Cancelled before or between retries

            attempt += 1
            try:
                # Use stream=True for efficient download of potentially large files
                response = self.session.get(url, stream=True, timeout=60) # Longer timeout for download
                response.raise_for_status() # Check for HTTP errors (4xx, 5xx)

                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if check_cancel and check_cancel():
                             if log_callback: log_callback(f"Descarga cancelada (durante escritura): {os.path.basename(save_path)}")
                             # Clean up partially downloaded file
                             f.close() # Close file before removing
                             try:
                                 os.remove(save_path)
                             except OSError as e:
                                 if log_callback: log_callback(f"Aviso: no se pudo eliminar archivo parcial {save_path}: {e}")
                             return False
                        f.write(chunk)
                return True # Download successful

            except HTTPError as e:
                 # Don't retry client errors (4xx) other than potential rate limits (429)
                 # Don't retry 404 Not Found
                 if e.response.status_code == 404:
                     if log_callback: log_callback(f"Error 404: Archivo no encontrado en {url}")
                     return False # Permanent failure
                 if 400 <= e.response.status_code < 500 and e.response.status_code != 429:
                     if log_callback: log_callback(f"Error HTTP {e.response.status_code} (cliente) no reintentable: {url} ({e})")
                     return False # Permanent client-side type error
                 # For server errors (5xx) or 429 (Too Many Requests), retry is reasonable
                 if log_callback: log_callback(f"Error HTTP {e.response.status_code} en intento {attempt}/{max_retries+1} para {url}: {e}")

            except RequestException as e:
                # Includes timeouts, connection errors etc. - worth retrying
                if log_callback: log_callback(f"Error de red/conexión en intento {attempt}/{max_retries+1} para {url}: {e}")

            except IOError as e:
                 if log_callback: log_callback(f"Error de E/S al guardar {save_path}: {e}")
                 return False # Likely a disk issue, don't retry usually

            except Exception as e:
                if log_callback: log_callback(f"Error inesperado en intento {attempt}/{max_retries+1} descargando {url}: {e}")
                # Depending on the error, might retry or not. Let's retry for now.

            # If we are here, an error occurred and we might retry
            if attempt <= max_retries:
                if log_callback: log_callback(f"Reintentando en {retry_delay}s...")
                # Wait before retrying, check for cancellation during wait
                for _ in range(int(retry_delay)):
                     if check_cancel and check_cancel():
                         return False
                     time.sleep(1)
            else:
                 if log_callback: log_callback(f"Máximo de reintentos ({max_retries}) alcanzado para {url}. Descarga fallida.")


        return False # Failed after all retries