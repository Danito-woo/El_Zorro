# web_gallery_flask_managed_v4.py (Corrected and Updated version)
import os
import sys
import threading
import webbrowser
from pathlib import Path
from urllib.parse import unquote, quote
import time
import socket
import shutil
import re # Para validaciones y extraccion de numeros

# <<< Imports para Flask >>>
from flask import (
    Flask, request, redirect, url_for, send_from_directory,
    abort, Response, flash, session, get_flashed_messages
)
from flask_cors import CORS

# --- Configuración ---
# ¡¡¡ASEGÚRATE DE QUE ESTA RUTA SEA CORRECTA!!!
ROOT_GALLERY_DIR = Path("E:/El_Zorro/downloads") # <<< CAMBIA ESTO A TU RUTA EXACTA
DEFAULT_PORT = 8088
ALLOWED_IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.avif')

# <<< Inicialización de Flask y CORS >>>
app = Flask(__name__)
CORS(app)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/' # Cambia esto por algo aleatorio y secreto
print("Flask-CORS inicializado. Secret Key configurada.")

# Almacenamiento del estado
current_selection = {
    "creator_dir": None,
    "creator_name": None
}

# --- HTML Templates (Incluidos estilos y script básicos) ---
HTML_STYLE_BLOCK = """
<style>
    body { font-family: sans-serif; background-color: #1e1e1e; color: #d4d4d4; margin: 0; padding: 20px; }
    h1, h2 { text-align: center; color: #dcdcaa; border-bottom: 1px solid #444; padding-bottom: 10px; margin-bottom: 20px; }
    a { color: #9cdcfe; text-decoration: none; } a:hover { text-decoration: underline; }
    .container { max-width: 1200px; margin: 0 auto; padding: 0 15px; }
    .error { color: #ce9178; border: 1px solid #ce9178; background-color: #3a2d2d; padding: 10px; margin-bottom: 15px; border-radius: 4px; text-align: center;}
    .info { color: #888; font-size: 0.9em; text-align: center; margin-top: 20px; }
    .flash-messages { list-style: none; padding: 0; margin: 0 0 20px 0; }
    .flash-messages li { padding: 10px 15px; margin-bottom: 10px; border-radius: 4px; text-align: center; }
    .flash-success { background-color: #3a4a3a; border: 1px solid #6a8a6a; color: #b5cea8; }
    .flash-error { background-color: #3a2d2d; border: 1px solid #ce9178; color: #ce9178; }
    .item-list { list-style: none; padding: 0; margin: 0 auto; max-width: 800px;}
    .item-list li { background-color: #2a2a2a; margin-bottom: 10px; border-radius: 5px; border: 1px solid #444; display: flex; justify-content: space-between; align-items: center; padding: 10px 15px; transition: background-color 0.2s ease; }
    .item-list li:hover { background-color: #3a3a3a; }
    .item-name { flex-grow: 1; margin-right: 15px; }
    .item-actions form { display: inline-block; margin-left: 8px; }
    button, input[type=submit], input[type=button] { background-color: #4a4a4a; color: #d4d4d4; border: 1px solid #666; padding: 5px 10px; border-radius: 3px; cursor: pointer; font-size: 0.9em; vertical-align: middle;}
    button:hover, input[type=submit]:hover, input[type=button]:hover { background-color: #5a5a5a; border-color: #888; }
    button.delete, input.delete { background-color: #6d3333; border-color: #9a5353; color: #f1b0b0; }
    button.delete:hover, input.delete:hover { background-color: #8b4343; }
    input[type=text] { background-color: #3c3c3c; border: 1px solid #666; color: #d4d4d4; padding: 5px 8px; border-radius: 3px; margin-right: 5px; vertical-align: middle;}
    input[type=number] { background-color: #3c3c3c; border: 1px solid #666; color: #d4d4d4; padding: 5px 8px; border-radius: 3px; width: 60px; margin-right: 5px; vertical-align: middle;}
    input[type=checkbox] { vertical-align: middle; margin-right: 5px;}

    /* Gallery Styles */
    .gallery-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 20px; }
    .group-item { position: relative; background-color: #2a2a2a; border: 1px solid #444; border-radius: 5px; text-align: center; overflow: hidden; padding-bottom: 45px; /* Space for buttons */ }
    .group-item img { max-width: 100%; height: 150px; object-fit: cover; display: block; margin-bottom: 10px; background-color: #333; }
    .group-item span { display: block; font-size: 0.9em; word-wrap: break-word; margin-bottom: 8px; padding: 0 5px; }
    .group-item .item-actions { position: absolute; bottom: 5px; left: 0; right: 0; text-align: center; }
     .group-item .item-actions form { margin: 0 4px; } /* Adjust spacing */
    .no-preview { height: 150px; background-color: #333; display: flex; align-items: center; justify-content: center; font-size:0.8em; color:#777; margin-bottom: 10px;}
    .item-count { position: absolute; top: 5px; right: 5px; background-color: rgba(0, 0, 0, 0.7); color: #fff; font-size: 0.8em; font-weight: bold; padding: 2px 6px; border-radius: 8px; line-height: 1; pointer-events: none; z-index: 2; }
    /* Image Grid Styles */
    .image-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 20px; }
    .image-item { position: relative; background-color: #2a2a2a; border: 1px solid #444; border-radius: 5px; overflow: hidden; padding-bottom: 35px; /* Space for delete button */ display: flex; flex-direction: column; } /* Use flex for better layout */
    .image-item img { max-width: 100%; height: auto; display: block; border-radius: 4px 4px 0 0; cursor: pointer; background-color: #333; flex-shrink: 0;} /* Prevent shrinking */
    .image-item .item-info { padding: 5px 8px; font-size: 0.8em; color: #ccc; text-align: center; flex-grow: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; } /* Info below image */
    .image-item .item-actions { position: absolute; bottom: 5px; left: 0; right: 0; text-align: center; background-color: rgba(42,42,42,0.8); padding: 2px 0; } /* Background for actions */
    .image-item .item-actions form { margin: 0; } /* No margin for inner form */
    .breadcrumb { margin-bottom: 20px; font-size: 0.9em; text-align:center; }
    /* Lightbox styles */
    .lightbox { display: none; position: fixed; z-index: 999; padding-top: 50px; left: 0; top: 0; width: 100%; height: 100%; overflow: auto; background-color: rgba(0,0,0,0.9); justify-content: center; align-items: center; }
    .lightbox-content { margin: auto; display: block; max-width: 90%; max-height: 90vh; } .lightbox-caption { text-align: center; color: #ccc; padding: 10px 0; font-size: 1.1em; }
    .lightbox-close { position: absolute; top: 15px; right: 35px; color: #f1f1f1; font-size: 40px; font-weight: bold; transition: 0.3s; cursor:pointer; } .lightbox-close:hover { color: #bbb; }

    /* Search and Merge styles */
    .controls-bar { text-align: center; margin-bottom: 20px; padding-bottom: 15px; border-bottom: 1px solid #444; }
    .controls-bar form { display: inline-block; margin: 0 10px; vertical-align: middle; }
    .controls-bar form input[type="text"], .controls-bar form input[type="submit"], .controls-bar form button { vertical-align: middle; }
    .merge-controls { margin-top: 20px; padding-top: 15px; border-top: 1px solid #444; }
    .merge-controls label { margin-right: 10px; }
</style>
<script>
    function confirmDelete(message) { return confirm(message || '¿Estás seguro? Esta acción no se puede deshacer.'); }
    function openLightbox(element) {{ var lb = document.getElementById('myLightbox'); lb.style.display = 'flex'; document.getElementById('lightboxImg').src = element.src; document.getElementById('lightboxCaption').innerHTML = element.alt; document.body.style.overflow = 'hidden'; }}
    function closeLightbox() {{ document.getElementById('myLightbox').style.display = 'none'; document.body.style.overflow = 'auto'; }}
    function closeLightboxOnClick(event) {{ if (event.target == document.getElementById('myLightbox')) {{ closeLightbox(); }} }}
    document.addEventListener('keydown', function(event) {{ if (event.key === "Escape") {{ closeLightbox(); }} }});

    // Merge functionality script
    document.addEventListener('DOMContentLoaded', function() {
        const mergeForm = document.getElementById('mergeForm');
        const mergeButton = document.getElementById('mergeButton');
        const checkboxes = document.querySelectorAll('input[name="selected_groups"]');

        function updateMergeButtonState() {
            let checkedCount = 0;
            checkboxes.forEach(cb => {
                if (cb.checked) {
                    checkedCount++;
                }
            });
            mergeButton.disabled = checkedCount < 2;
        }

        checkboxes.forEach(cb => {
            cb.addEventListener('change', updateMergeButtonState);
        });

        // Initial state update
        updateMergeButtonState();

        if (mergeForm) {
             mergeForm.addEventListener('submit', function(event) {
                 const newNameInput = document.getElementById('newMergeGroupName');
                 if (!newNameInput.value.trim()) {
                     alert('Por favor, ingresa un nombre para el nuevo grupo fusionado.');
                     event.preventDefault(); // Prevent form submission
                     return false;
                 }
                 let checkedCount = 0;
                 checkboxes.forEach(cb => { if (cb.checked) checkedCount++; });
                 if (checkedCount < 2) {
                     alert('Selecciona al menos dos grupos para fusionar.');
                     event.preventDefault();
                     return false;
                 }
                 const selectedNames = Array.from(checkboxes).filter(cb => cb.checked).map(cb => cb.value).join(', ');
                 if (!confirm(`¿Estás seguro que quieres fusionar los grupos "${selectedNames}" en el nuevo grupo llamado "${newNameInput.value.trim()}"?`)) {
                     event.preventDefault();
                     return false;
                 }
             });
        }

        // Reorganize functionality script (Group Page)
        const reorganizeForm = document.getElementById('reorganizeForm');
        if (reorganizeForm) {
            reorganizeForm.addEventListener('submit', function(event) {
                const numberInputs = document.querySelectorAll('.image-item input[type="number"]');
                const numbers = Array.from(numberInputs).map(input => input.value.trim()); // Trim whitespace
                const filenames = document.querySelectorAll('.image-item input[type="hidden"][name^="filename_"]');
                const fileOrder = [];

                // Collect filename and desired number pairs
                filenames.forEach(hiddenInput => {
                    const encodedFilename = hiddenInput.value;
                    const numberInput = document.querySelector(`input[name="order_${encodedFilename}"]`);
                    if (numberInput) {
                        fileOrder.push({
                            filename: encodedFilename,
                            number: numberInput.value.trim()
                        });
                    }
                });

                // Basic validation: check for empty or non-positive numbers
                for (const item of fileOrder) {
                    const num = parseInt(item.number, 10);
                    if (item.number === '' || isNaN(num) || num <= 0) {
                        alert('Por favor, asegúrate de que todos los números sean válidos y positivos.');
                        event.preventDefault();
                        return false;
                    }
                }

                 // Optional: Add validation for duplicate numbers if needed, though server handles sequential renaming
                 // Simple check for duplicates
                 const nums = fileOrder.map(item => item.number);
                 const uniqueNums = new Set(nums);
                 if (uniqueNums.size !== nums.length) {
                     if (!confirm('Advertencia: Hay números duplicados. Las imágenes se ordenarán por el número y luego por su nombre original. ¿Continuar?')) {
                          event.preventDefault();
                          return false;
                     }
                 } else {
                      if (!confirm('¿Estás seguro que quieres reorganizar las imágenes con los números asignados?')) {
                           event.preventDefault();
                           return false;
                      }
                 }


            });
        }

    });
</script>
"""

HTML_SELECTOR_TEMPLATE = """
<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Galería El Zorro - Seleccionar Creador</title>{style_block}</head>
<body><div class="container"><h1>Selecciona un Creador</h1>{flash_messages}
    {error_message}
    <div class="controls-bar">
        <form action="{cleanup_action_root}" method="post" onsubmit="return confirmDelete('¿Seguro que quieres eliminar TODAS las carpetas vacías en el directorio principal?');">
            <input type="submit" value="Limpiar Carpetas Vacías (Raíz)">
        </form>
    </div>
    <ul class="item-list">
        {creator_list_items}
    </ul>
    <p class="info">Directorio base: {base_dir_display}</p>
</div></body></html>
"""

# Modified HTML_INDEX_TEMPLATE to include search and merge controls
HTML_INDEX_TEMPLATE = """
<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Galería El Zorro - {creator_name}</title>{style_block}</head>
<body><div class="container"><h1>Galería para: {creator_name}</h1>{flash_messages}
    <div class="controls-bar">
        <a href="{change_creator_link}">« Cambiar Creador</a>
        <form action="{rename_creator_action}" method="post" style="display:inline;" onsubmit="var name=this.new_name.value; if(!name || !name.trim()) {{alert('Ingresa un nombre.'); return false;}} return confirm('¿Renombrar creador a \\'' + name.trim() + '\\'?');">
            <input type="text" name="new_name" placeholder="Nuevo nombre creador" required>
            <input type="submit" value="Renombrar Creador">
        </form>
        <form action="{delete_creator_action}" method="post" style="display:inline;" onsubmit="return confirmDelete('¡PELIGRO! ¿Seguro que quieres ELIMINAR TODO el contenido de \\'{creator_name}\\'?');">
            <input type="submit" value="Eliminar Creador" class="delete">
        </form>
    </div>

    <div class="controls-bar merge-controls">
        <form action="{search_action}" method="get" style="display:inline;">
            <label for="search_query">Buscar Grupo:</label>
            <input type="text" id="search_query" name="query" value="{current_search_query}" placeholder="Nombre del grupo">
            <input type="submit" value="Buscar">
        </form>
         <form action="{cleanup_action_creator}" method="post" onsubmit="return confirmDelete('¿Seguro que quieres eliminar TODAS las carpetas vacías en el directorio del creador?');">
            <input type="submit" value="Limpiar Carpetas Vacías (Aquí)">
        </form>
    </div>

    <h2>Grupos:</h2>

    <form id="mergeForm" action="{merge_action}" method="post">
        <div class="controls-bar merge-controls">
             <label for="newMergeGroupName">Fusionar seleccionados en:</label>
             <input type="text" id="newMergeGroupName" name="new_group_name" placeholder="Nombre del nuevo grupo" required>
             <button type="submit" id="mergeButton" disabled>Fusionar Grupos</button>
        </div>
        <div class="gallery-grid">
            {group_items_html}
        </div>
    </form>

    {no_groups_message}
</div></body></html>
"""

# Modified HTML_GROUP_TEMPLATE to include reorganization form
HTML_GROUP_TEMPLATE = """
<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{group_name_display} - Galería El Zorro</title>{style_block}</head>
<body><div class="container">
    <div class="breadcrumb"><a href="{breadcrumb_link}">« Volver a '{creator_name}'</a></div>
    <h1>{group_name_display}</h1>{flash_messages}
    <div class="controls-bar">
        <form action="{rename_group_action}" method="post" style="display:inline;" onsubmit="var name=this.new_name.value; if(!name || !name.trim()) {{alert('Ingresa un nombre.'); return false;}} return confirm('¿Renombrar grupo a \\'' + name.trim() + '\\'?');">
            <input type="text" name="new_name" placeholder="Nuevo nombre grupo" required>
            <input type="submit" value="Renombrar Grupo">
        </form>
        <form action="{delete_group_action}" method="post" style="display:inline;" onsubmit="return confirmDelete('¿Seguro que quieres ELIMINAR el grupo \\'{group_name_display}\\' y todas sus imágenes?');">
            <input type="submit" value="Eliminar Grupo" class="delete">
        </form>
    </div>

    <h2>Imágenes:</h2>
    <form id="reorganizeForm" action="{reorganize_action}" method="post">
        <div class="controls-bar">
             <button type="submit">Guardar Orden</button>
             <span class="info" style="margin-left: 15px;">Asigna números a las imágenes para cambiar su orden.</span>
        </div>
        <div class="image-grid">
            {image_items_html}
        </div>
    </form>

    {no_images_message}
    <div id="myLightbox" class="lightbox" onclick="closeLightboxOnClick(event)">
        <span class="lightbox-close" onclick="closeLightbox()">×</span>
        <img class="lightbox-content" id="lightboxImg"><div id="lightboxCaption" class="lightbox-caption"></div>
    </div>
</div></body></html>
"""


# --- Funciones Auxiliares ---
def get_local_ip():
    s = None
    try: s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.settimeout(0.1); s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]; return ip
    except socket.error as e: print(f"WARN: No se pudo determinar IP local ({e}). Usando 127.0.0.1."); return "127.0.0.1"
    finally:
        if s: s.close()

def is_safe_path(base_dir, path_to_check):
    """Verifica si path_to_check está de forma segura dentro de base_dir."""
    # This function should be resilient even if paths don't exist, for validation purposes
    try:
        # Get absolute paths for comparison
        base = Path(base_dir).resolve()
        target = Path(path_to_check).resolve()
        # Check if target is inside base or same as base
        return target.is_relative_to(base) or target == base
    except Exception:
        # Handles cases like base_dir not existing initially or invalid paths
        # print(f"DEBUG: is_safe_path check failed for {path_to_check} relative to {base_dir}")
        return False

def is_safe_name(name):
    """Verifica si un nombre de archivo/directorio es 'seguro'."""
    # Check for empty string, None, path traversal attempts, and common invalid characters
    if not name or not isinstance(name, str) or not name.strip(): return False # Added strip()
    # Basic check against path separators and null bytes
    if '/' in name or '\\' in name or '\x00' in name: return False
    # Prevent names that are just '.' or '..'
    if name == '.' or name == '..': return False
    # Prevent names starting or ending with space/dot
    if name.startswith('.') or name.endswith('.') or name.startswith(' ') or name.endswith(' '): return False
     # Check for characters considered unsafe or reserved on common filesystems
    unsafe_chars = '<>:"|?*' # Common unsafe characters on Windows
    if any(char in name for char in unsafe_chars): return False
    # Use a regex to allow alphanumeric, spaces, underscores, hyphens, dots (but not leading/trailing)
    # and ensure the whole string matches.
    if not re.fullmatch(r'^[a-zA-Z0-9_\-\.\s]+$', name):
         print(f"DEBUG: is_safe_name failed regex check for '{name}'")
         return False

    return True

def get_safe_path(base_dir, *subdirs):
    """Construye y validates a path ensuring it is within base_dir."""
    try:
        base = Path(base_dir).resolve(strict=True)
        if not is_safe_path(ROOT_GALLERY_DIR, base):
            print(f"ERROR: get_safe_path - Base dir inválido o fuera de ROOT: {base_dir}")
            return None

        current_path = base

        for subdir in subdirs:
            subdir_str = str(subdir)
            if not is_safe_name(subdir_str):
                print(f"ERROR: get_safe_path - Subdir no seguro: {subdir_str}")
                return None
            current_path = current_path / subdir_str

        # Resolve the final path and check if it is within the *original validated base_dir*
        final_resolved_path = current_path.resolve()

        if is_safe_path(base, final_resolved_path):
             # Return the path object constructed, not the resolved path
             # This is important for operations like mkdir or rename targets
             return current_path
        else:
             print(f"WARN: get_safe_path - Ruta final resuelta {final_resolved_path} fuera de base segura {base_dir}")
             return None

    except FileNotFoundError:
        # The base_dir itself was not found. This can happen if trying to build a path
        # within a creator directory that was deleted, or if ROOT_GALLERY_DIR is wrong.
        # For cases like creating a new creator dir under ROOT, base_dir *is* ROOT_GALLERY_DIR
        # which is checked to exist initially.
        # If the base_dir (like creator_dir) disappears during a session, operations will fail here.
        # print(f"DEBUG: get_safe_path - Base dir no encontrado: {base_dir}")
        return None
    except Exception as e:
        print(f"ERROR: get_safe_path - Excepción durante construcción/validación de ruta: {e}")
        return None


def build_absolute_url(endpoint, **values):
    """Construye una URL absoluta HTTP usando el host de la solicitud."""
    # Needs request context
    try:
        base_url = f"http://{request.host}"
        # url_for automatically handles encoding for path components
        relative_path = url_for(endpoint, **values)
        return f"{base_url}{relative_path}"
    except RuntimeError:
        print("WARN: build_absolute_url llamado fuera de contexto de solicitud."); return "#error_url" # Fallback
    except Exception as e:
        print(f"ERROR: build_absolute_url - {e}"); return "#error_url"

def render_flash_messages():
    """Genera HTML para los mensajes flash."""
    messages = get_flashed_messages(with_categories=True)
    if not messages: return ""
    html = '<ul class="flash-messages">'
    for category, message in messages:
        css_class = 'flash-success' if category == 'success' else 'flash-error'
        html += f'<li class="{css_class}">{message}</li>'
    html += '</ul>'
    return html

def find_empty_dirs(base_path):
    """Encuentra recursivamente directorios vacíos dentro de base_path."""
    empty_dirs = []
    if not base_path or not base_path.is_dir(): return empty_dirs

    # Need to resolve base_path first to compare against it safely
    try:
         base_resolved = base_path.resolve(strict=True)
    except (FileNotFoundError, Exception) as e:
         print(f"ERROR: find_empty_dirs - Invalid base_path: {base_path}, {e}"); return empty_dirs


    for root, dirs, files in os.walk(base_path, topdown=False): # topdown=False visits children before parent
        current_dir_path = Path(root)
        try:
             # Ensure the current directory being checked is inside the original base path
             if not is_safe_path(base_resolved, current_dir_path):
                  print(f"SECURITY WARNING: find_empty_dirs - Skipping path outside base: {current_dir_path}"); continue

             # Check if the current directory (root) is empty after visiting its children
             # It's empty if there are no files AND no subdirectories left (since we visited subdirs already)
             if not os.listdir(root): # Check if directory is truly empty
                  empty_dirs.append(current_dir_path)

        except Exception as e:
             print(f"ERROR: find_empty_dirs - Error processing dir {current_dir_path}: {e}"); continue


    # Filter out the base_path itself if it was accidentally included (shouldn't be with topdown=False unless base_path is empty initially)
    # and re-ensure they are still within the base_path for safety (belt and suspenders)
    return [d for d in empty_dirs if d != base_path and is_safe_path(base_resolved, d)]

# --- Rutas de Flask ---

@app.route('/')
def index():
    """Página principal: Muestra selector o índice del creador."""
    flash_html = render_flash_messages()
    query = request.args.get('query', '').strip() # Get search query

    if current_selection["creator_dir"]:
        # --- Mostrar Índice del Creador Seleccionado ---
        creator_dir = current_selection["creator_dir"]
        creator_name = current_selection["creator_name"]

        # Re-validar el directorio actual por si fue eliminado/movido externamente
        creator_path_obj = get_safe_path(ROOT_GALLERY_DIR, creator_name) # Re-validate using safe path getter
        if not creator_path_obj or not creator_path_obj.is_dir():
             print(f"ERROR: Estado inválido en index (dir: {creator_dir}). Reseteando.")
             flash('El directorio del creador ya no es válido.', 'error')
             current_selection.update({"creator_dir": None, "creator_name": None})
             # Redirecting back to index without creator will show the selector
             return redirect(url_for('index'))

        # Update current_selection["creator_dir"] to the resolved safe path string
        # This handles cases where the path might have been symbolic or slightly different before resolving
        # Ensures consistency for future operations.
        current_selection["creator_dir"] = str(creator_path_obj)


        group_items_html = []
        no_groups_msg = ""
        try:
            # Use the validated creator_path_obj for file system operations
            all_group_paths = sorted([d for d in creator_path_obj.iterdir() if d.is_dir()])

            # Apply search filter if query is present
            if query:
                 filtered_group_paths = [d for d in all_group_paths if query.lower() in d.name.lower()]
                 if not filtered_group_paths:
                      no_groups_msg = f"<p class='info'>No se encontraron grupos con el término '{query}'.</p>"
                 group_paths_to_display = filtered_group_paths
            else:
                 group_paths_to_display = all_group_paths
                 if not group_paths_to_display:
                     no_groups_msg = "<p class='info'>No se encontraron grupos.</p>"

            if group_paths_to_display:
                for group_path_obj in group_paths_to_display:
                    group_name = group_path_obj.name
                    # is_safe_name check is crucial here as this name comes directly from the filesystem
                    if not is_safe_name(group_name):
                        print(f"WARN: Ignorando directorio con nombre inseguro: {group_path_obj}")
                        continue # Ignorar nombres inválidos

                    preview_img_src_abs = None
                    item_count = 0
                    try:
                         # Use iterdir for efficiency on potentially large directories
                         image_files = [f.name for f in group_path_obj.iterdir() if f.is_file() and f.suffix.lower() in ALLOWED_IMAGE_EXTENSIONS]
                         item_count = len(image_files)
                         # Attempt numeric sort first, fallback to alphabetical
                         try: images_sorted = sorted(image_files, key=lambda x: int(Path(x).stem))
                         except (ValueError, TypeError): images_sorted = sorted(image_files)
                         if images_sorted:
                             # Need to encode group_name and filename for the URL
                             preview_img_src_abs = build_absolute_url('serve_image', group_name_encoded=quote(group_name), filename=quote(images_sorted[0]))
                    except OSError as e: print(f"WARN: Leyendo grupo {group_path_obj} para preview: {e}"); pass # Silently skip preview on error

                    preview_html = "<div class='no-preview'>Sin Previa</div>"
                    if preview_img_src_abs: preview_html = f'<img src="{preview_img_src_abs}" alt="Previa de {group_name}" loading="lazy">'
                    count_html = f'<div class="item-count">{item_count}</div>' if item_count > 0 else ''

                    # --- Actions for each group item ---
                    # Need to encode the group name for URLs, but display the raw name
                    encoded_group_name = quote(group_name)
                    rename_action = build_absolute_url('rename_group', group_name_encoded=encoded_group_name)
                    delete_action = build_absolute_url('delete_group', group_name_encoded=encoded_group_name)
                    group_link = build_absolute_url('show_group', group_name_encoded=encoded_group_name)

                    # Add checkbox for merge functionality
                    merge_checkbox = f'<input type="checkbox" name="selected_groups" value="{encoded_group_name}">'

                    actions_html = f"""
                    <div class="item-actions">
                        <form action="{rename_action}" method="post" style="display:inline;" onsubmit="var name=this.new_name.value; if(!name || !name.trim()) {{alert('Ingresa un nombre.'); return false;}} return confirm('Renombrar grupo a \\'' + name.trim() + '\\'?');">
                            <input type="text" name="new_name" size="10" placeholder="Nuevo nombre" required><input type="submit" value="Renombrar">
                        </form>
                        <form action="{delete_action}" method="post" style="display:inline;" onsubmit="return confirmDelete('Eliminar grupo \\'{group_name}\\'?');">
                            <input type="submit" value="Eliminar" class="delete">
                        </form>
                    </div>"""
                    group_items_html.append(
                        f'<div class="group-item">{merge_checkbox}{count_html}<a href="{group_link}">{preview_html}<span>{group_name}</span></a>{actions_html}</div>'
                    )
        except OSError as e:
            print(f"ERROR: Leyendo {creator_path_obj}: {e}. Reseteando."); current_selection.update({"creator_dir": None, "creator_name": None}); flash(f"Error al leer grupos de '{creator_name}'.", "error"); return redirect(url_for('index'))

        # --- URLs for creator-level actions ---
        rename_creator_action = build_absolute_url('rename_creator')
        delete_creator_action = build_absolute_url('delete_creator')
        search_action = build_absolute_url('index') # Search results reload the index page with a query param
        merge_action = build_absolute_url('merge_groups')
        cleanup_action_creator = build_absolute_url('cleanup_empty_folders_creator')


        html_content = HTML_INDEX_TEMPLATE.format(
            style_block=HTML_STYLE_BLOCK, flash_messages=flash_html, creator_name=creator_name,
            group_items_html="\n".join(group_items_html), no_groups_message=no_groups_msg,
            change_creator_link=build_absolute_url('select_creator'),
            rename_creator_action=rename_creator_action, delete_creator_action=delete_creator_action,
            search_action=search_action, current_search_query=query, # Pass the current query back
            merge_action=merge_action,
            cleanup_action_creator=cleanup_action_creator # CORRECTED placeholder name here
        )
        return Response(html_content, mimetype='text/html')

    else:
        # --- Mostrar Selector de Creador ---
        error_msg_html = ""
        list_items_html = []
        cleanup_action_root = build_absolute_url('cleanup_empty_folders_root') # Cleanup at root level

        if not ROOT_GALLERY_DIR.is_dir(): error_msg_html = f"<p class='error'>Error: Directorio base '{ROOT_GALLERY_DIR}' no existe.</p>"
        else:
            try:
                creators = sorted([d for d in ROOT_GALLERY_DIR.iterdir() if d.is_dir()])
                if not creators: error_msg_html = "<p class='error'>No se encontraron creadores.</p>"
                else:
                    for creator_path in creators:
                        cname = creator_path.name
                        # is_safe_name check is crucial here
                        if not is_safe_name(cname):
                             print(f"WARN: Ignorando directorio de creador con nombre inseguro: {creator_path}")
                             continue # Ignorar nombres inválidos
                        encoded_cname = quote(cname)
                        load_link = build_absolute_url('load_creator', creator=encoded_cname)
                        list_items_html.append(f'<li><span class="item-name"><a href="{load_link}">{cname}</a></span></li>')
            except OSError as e: error_msg_html = f"<p class='error'>Error al leer directorio base: {e}</p>"

        html_content = HTML_SELECTOR_TEMPLATE.format(
            style_block=HTML_STYLE_BLOCK, flash_messages=flash_html, error_message=error_msg_html,
            creator_list_items="\n".join(list_items_html), base_dir_display=ROOT_GALLERY_DIR,
            cleanup_action_root=cleanup_action_root # Placeholder name for root cleanup
        )
        return Response(html_content, mimetype='text/html')

# --- Rutas de Carga y Selección ---
@app.route('/load')
def load_creator():
    creator_encoded = request.args.get('creator');
    if not creator_encoded: abort(400, description="Falta parámetro 'creator'.")
    creator_name = unquote(creator_encoded)
    if not is_safe_name(creator_name): flash("Nombre de creador inválido.", "error"); return redirect(url_for('index'))
    # Use get_safe_path to validate that it's DENTRO de ROOT_GALLERY_DIR
    potential_path_obj = get_safe_path(ROOT_GALLERY_DIR, creator_name)

    if potential_path_obj and potential_path_obj.is_dir():
        # Store the validated, resolved path string
        current_selection.update({"creator_dir": str(potential_path_obj.resolve()), "creator_name": creator_name})
        print(f"INFO: Cargado creador: {creator_name}"); flash(f"Galería '{creator_name}' cargada.", "success")
        return redirect(url_for('index'))
    else: print(f"ERROR: Intento de carga inválida: {potential_path_obj}"); flash(f"Directorio '{creator_name}' no encontrado/inválido.", "error"); return redirect(url_for('index'))

@app.route('/select')
def select_creator():
    current_selection.update({"creator_dir": None, "creator_name": None}); print("INFO: Selección reseteada."); flash("Selección de creador reiniciada.", "success"); return redirect(url_for('index'))

# --- Ruta para mostrar Grupo ---
@app.route('/group/<path:group_name_encoded>')
def show_group(group_name_encoded):
    flash_html = render_flash_messages()
    if not current_selection["creator_dir"]: flash("Selecciona creador primero.", "error"); return redirect(url_for('index'))

    group_name = unquote(group_name_encoded)
    creator_dir = current_selection["creator_dir"]
    creator_name = current_selection["creator_name"]

    if not is_safe_name(group_name): abort(400, "Nombre de grupo inválido.")

    # Get the validated group path relative to the creator directory
    group_dir_path_obj = get_safe_path(creator_dir, group_name)

    # Re-validar si el grupo existe and is a directory within the validated creator_dir
    if not group_dir_path_obj or not group_dir_path_obj.is_dir(): flash(f"Grupo '{group_name}' no encontrado.", "error"); return redirect(url_for('index'))


    image_items_html = []
    no_images_msg = ""
    try:
        # Get only image files using the validated group path
        image_files = [f.name for f in group_dir_path_obj.iterdir() if f.is_file() and f.suffix.lower() in ALLOWED_IMAGE_EXTENSIONS]
        # Attempt numeric sort first, fallback to alphabetical
        try: image_files_sorted = sorted(image_files, key=lambda x: int(Path(x).stem))
        except (ValueError, TypeError): image_files_sorted = sorted(image_files) # Fallback a orden alfabético

        if not image_files_sorted: no_images_msg = "<p class='info'>No se encontraron imágenes.</p>"
        else:
            for i, img_file in enumerate(image_files_sorted): # Use enumerate to get current order/index
                # is_safe_name check is crucial here
                if not is_safe_name(img_file):
                     print(f"WARN: Skipping image with unsafe name: {group_dir_path_obj / img_file}")
                     continue # Seguridad

                encoded_img_file = quote(img_file)
                img_src_abs = build_absolute_url('serve_image', group_name_encoded=group_name_encoded, filename=encoded_img_file)
                alt_text = f"{img_file} (Grupo: {group_name})"
                delete_action = build_absolute_url('delete_image', group_name_encoded=group_name_encoded, filename=encoded_img_file)

                # Extract current number for the input field (if file is NNN.ext)
                current_number_match = re.match(r'^(\d+)\.', img_file)
                current_number = current_number_match.group(1) if current_number_match else str(i + 1) # Use current index + 1 as default

                actions_html = f"""
                <div class="item-actions">
                    <input type="number" name="order_{encoded_img_file}" value="{current_number}" min="1" required>
                    <input type="hidden" name="filename_{encoded_img_file}" value="{encoded_img_file}">
                    <form action="{delete_action}" method="post" onsubmit="return confirmDelete('Eliminar imagen \\'{img_file}\\'?');" style="display:inline;">
                        <input type="submit" value="X" class="delete">
                    </form>
                </div>"""
                # Add image filename below the image
                image_items_html.append(
                    f'<div class="image-item"><img src="{img_src_abs}" alt="{alt_text}" loading="lazy" onclick="openLightbox(this)"><div class="item-info">{img_file}</div>{actions_html}</div>'
                )
    except OSError as e: print(f"ERROR leyendo grupo '{group_name}': {e}"); flash(f"Error al leer grupo '{group_name}'.", "error"); return redirect(url_for('index'))

    # --- URLs for group-level actions ---
    rename_group_action = build_absolute_url('rename_group', group_name_encoded=group_name_encoded)
    delete_group_action = build_absolute_url('delete_group', group_name_encoded=group_name_encoded)
    reorganize_action = build_absolute_url('reorganize_group', group_name_encoded=group_name_encoded)


    html_content = HTML_GROUP_TEMPLATE.format(
        style_block=HTML_STYLE_BLOCK, flash_messages=flash_html, group_name_display=group_name,
        image_items_html="\n".join(image_items_html), no_images_message=no_images_msg,
        creator_name=creator_name or "", breadcrumb_link=build_absolute_url('index'),
        rename_group_action=rename_group_action, delete_group_action=delete_group_action,
        reorganize_action=reorganize_action
    )
    return Response(html_content, mimetype='text/html')

# --- Ruta para servir Imágenes ---
@app.route('/<path:group_name_encoded>/<path:filename>')
def serve_image(group_name_encoded, filename):
    if not current_selection["creator_dir"]: abort(404, description="No hay creador seleccionado.")
    group_name = unquote(group_name_encoded); filename_decoded = unquote(filename)

    # Validate group name
    if not is_safe_name(group_name): abort(400, "Nombre de grupo inválido.")

    # Validate filename and extension
    filename_path = Path(filename_decoded)
    if not is_safe_name(filename_path.name) or filename_path.suffix.lower() not in ALLOWED_IMAGE_EXTENSIONS: abort(400, "Nombre/tipo de archivo inválido.")

    # Obtener ruta segura al directorio del grupo
    group_dir_path_obj = get_safe_path(current_selection["creator_dir"], group_name)
    if not group_dir_path_obj or not group_dir_path_obj.is_dir(): abort(404, f"Grupo '{group_name}' no encontrado.")

    # Use send_from_directory for serving the file safely
    try:
        # send_from_directory handles path validation internally, ensuring 'filename' is within 'directory'.
        response = send_from_directory(directory=str(group_dir_path_obj), path=filename_decoded, conditional=True)
        response.headers['Cache-Control'] = 'public, max-age=3600'; return response
    except FileNotFoundError: abort(404, f"Archivo '{filename_decoded}' no encontrado en '{group_name}'.")
    except Exception as e: print(f"ERROR sirviendo {filename_decoded}: {e}"); abort(500, "Error interno.")


# --- RUTAS POST PARA ACCIONES ---

@app.route('/delete_image/<path:group_name_encoded>/<path:filename>', methods=['POST'])
def delete_image(group_name_encoded, filename):
    if not current_selection["creator_dir"]: flash("Operación no permitida.", "error"); return redirect(url_for('index'))
    group_name = unquote(group_name_encoded); filename_decoded = unquote(filename)

    if not is_safe_name(group_name): flash("Nombre de grupo inválido.", "error"); return redirect(url_for('index'))
    if not is_safe_name(filename_decoded) or Path(filename_decoded).suffix.lower() not in ALLOWED_IMAGE_EXTENSIONS: flash("Nombre/tipo de archivo inválido.", "error"); return redirect(url_for('index'))

    img_path = get_safe_path(current_selection["creator_dir"], group_name, filename_decoded)

    if not img_path or not img_path.is_file(): flash(f"Imagen '{filename_decoded}' no encontrada.", "error")
    else:
        try: os.remove(img_path); print(f"INFO: Eliminada: {img_path}"); flash(f"Imagen '{filename_decoded}' eliminada.", "success")
        except OSError as e: print(f"ERROR: Eliminando {img_path}: {e}"); flash(f"Error al eliminar '{filename_decoded}': {e}", "error")
        except Exception as e: print(f"ERROR: Eliminando {img_path}: {e}"); flash("Error inesperado.", "error")

    # Redirigir de vuelta al grupo
    return redirect(url_for('show_group', group_name_encoded=group_name_encoded))

@app.route('/delete_group/<path:group_name_encoded>', methods=['POST'])
def delete_group(group_name_encoded):
    if not current_selection["creator_dir"]: flash("Operación no permitida.", "error"); return redirect(url_for('index'))
    group_name = unquote(group_name_encoded)
    if not is_safe_name(group_name): flash("Nombre de grupo inválido.", "error"); return redirect(url_for('index'))

    group_path = get_safe_path(current_selection["creator_dir"], group_name)

    if not group_path or not group_path.is_dir(): flash(f"Grupo '{group_name}' no encontrado.", "error")
    else:
        try: shutil.rmtree(group_path); print(f"INFO: Grupo eliminado: {group_path}"); flash(f"Grupo '{group_name}' eliminado.", "success")
        except OSError as e: print(f"ERROR: Eliminando {group_path}: {e}"); flash(f"Error al eliminar '{group_name}': {e}", "error")
        except Exception as e: print(f"ERROR: Eliminando {group_path}: {e}"); flash("Error inesperado.", "error")

    # Redirigir al índice del creador
    return redirect(url_for('index'))

@app.route('/delete_creator', methods=['POST'])
def delete_creator():
    if not current_selection["creator_dir"]: flash("Operación no permitida.", "error"); return redirect(url_for('index'))
    creator_dir = current_selection["creator_dir"]; creator_name = current_selection["creator_name"]

    # Re-validar que es hijo directo de ROOT for extra safety, though get_safe_path should cover this
    try:
         creator_path_obj = Path(creator_dir) # Use Path object
         # Resolve both paths before comparing parent
         if not creator_path_obj.resolve().parent == ROOT_GALLERY_DIR.resolve():
              flash("Error de seguridad grave: Intento de eliminar directorio fuera del ROOT.", "error"); print(f"SECURITY ERROR: Intento de eliminar {creator_dir}"); current_selection.update({"creator_dir": None, "creator_name": None}); return redirect(url_for('index'))
         if not creator_path_obj.is_dir(): # Also check if it's actually a directory
              flash("Error: El directorio del creador no es válido.", "error"); print(f"SECURITY ERROR: Creador dir no es directorio: {creator_dir}"); current_selection.update({"creator_dir": None, "creator_name": None}); return redirect(url_for('index'))

    except Exception as e:
         flash("Error de seguridad al validar ruta.", "error"); print(f"SECURITY ERROR: Excepción al validar {creator_dir}: {e}"); current_selection.update({"creator_dir": None, "creator_name": None}); return redirect(url_for('index'))


    try:
        shutil.rmtree(creator_dir); print(f"INFO: Creador eliminado: {creator_dir}"); flash(f"Creador '{creator_name}' eliminado.", "success"); current_selection.update({"creator_dir": None, "creator_name": None}); return redirect(url_for('index'))
    except OSError as e: print(f"ERROR: Eliminando {creator_dir}: {e}"); flash(f"Error al eliminar '{creator_name}': {e}", "error"); return redirect(url_for('index')) # Volver al índice del creador si falla
    except Exception as e: print(f"ERROR: Eliminando {creator_dir}: {e}"); flash("Error inesperado.", "error"); return redirect(url_for('index'))

@app.route('/rename_group/<path:group_name_encoded>', methods=['POST'])
def rename_group(group_name_encoded):
    if not current_selection["creator_dir"]: flash("Operación no permitida.", "error"); return redirect(url_for('index'))
    old_group_name = unquote(group_name_encoded); new_group_name = request.form.get('new_name', '').strip()
    creator_dir = current_selection["creator_dir"]

    redirect_url_on_fail = url_for('show_group', group_name_encoded=group_name_encoded) # Where to go back if it fails

    # Validate names
    if not is_safe_name(old_group_name): flash("Nombre original inválido.", "error"); return redirect(url_for('index')) # Can't redirect to original group if name is bad
    if not is_safe_name(new_group_name): flash("Nuevo nombre inválido.", "error"); return redirect(redirect_url_on_fail)
    if old_group_name == new_group_name: flash("Nombres iguales.", "error"); return redirect(redirect_url_on_fail)

    # Get validated paths
    old_path = get_safe_path(creator_dir, old_group_name)
    # get_safe_path ensures the target path is also within the creator_dir
    new_path = get_safe_path(creator_dir, new_group_name)

    if not old_path or not old_path.is_dir(): flash(f"Grupo original '{old_group_name}' no encontrado.", "error"); return redirect(url_for('index')) # Go to index if original group is gone
    if not new_path: flash("Nueva ruta inválida/insegura.", "error"); return redirect(redirect_url_on_fail)
    # Check if the target path exists and is not the source path (which it shouldn't be if names are different)
    if new_path.exists() and new_path != old_path: flash(f"Ya existe '{new_group_name}'.", "error"); return redirect(redirect_url_on_fail)

    try:
        os.rename(old_path, new_path); print(f"INFO: Renombrado: {old_path} -> {new_path}"); flash(f"Renombrado a '{new_group_name}'.", "success")
        # Redirect to the *new* name's URL
        return redirect(url_for('show_group', group_name_encoded=quote(new_group_name)))
    except OSError as e: print(f"ERROR: Renombrando {old_path}: {e}"); flash(f"Error al renombrar: {e}", "error"); return redirect(redirect_url_on_fail)
    except Exception as e: print(f"ERROR: Renombrando {old_path}: {e}"); flash("Error inesperado.", "error"); return redirect(redirect_url_on_fail)

@app.route('/rename_creator', methods=['POST'])
def rename_creator():
    if not current_selection["creator_dir"]: flash("Operación no permitida.", "error"); return redirect(url_for('index'))
    old_creator_dir = current_selection["creator_dir"]
    old_creator_name = current_selection["creator_name"]
    new_creator_name = request.form.get('new_name', '').strip()

    redirect_url_on_fail = url_for('index') # Always redirect to index if creator rename fails

    # Validate names
    if not is_safe_name(new_creator_name): flash("Nuevo nombre inválido.", "error"); return redirect(redirect_url_on_fail)
    if old_creator_name == new_creator_name: flash("Nombres iguales.", "error"); return redirect(redirect_url_on_fail)

    # Get validated paths
    # Re-validate old path using ROOT_GALLERY_DIR as base
    old_creator_path_obj = get_safe_path(ROOT_GALLERY_DIR, old_creator_name)
    # Get new path using ROOT_GALLERY_DIR as base
    new_creator_path_obj = get_safe_path(ROOT_GALLERY_DIR, new_creator_name)


    if not old_creator_path_obj or not old_creator_path_obj.is_dir():
         flash(f"Directorio original del creador '{old_creator_name}' no encontrado o inválido.", "error");
         current_selection.update({"creator_dir": None, "creator_name": None}); # Reset selection if original path is bad
         return redirect(url_for('index'))

    if not new_creator_path_obj: flash("Nueva ruta de creador inválida/insegura.", "error"); return redirect(redirect_url_on_fail)

    # Check if the target path exists and is not the source path
    if new_creator_path_obj.exists() and new_creator_path_obj != old_creator_path_obj:
         flash(f"Ya existe un creador llamado '{new_creator_name}'.", "error"); return redirect(redirect_url_on_fail)

    try:
        os.rename(old_creator_path_obj, new_creator_path_obj); print(f"INFO: Renombrado creador: {old_creator_path_obj} -> {new_creator_path_obj}"); flash(f"Creador renombrado a '{new_creator_name}'.", "success")
        # Update session with the new path and name (store the resolved path string)
        current_selection.update({"creator_dir": str(new_creator_path_obj.resolve()), "creator_name": new_creator_name})
        return redirect(url_for('index')) # Redirect to the newly named creator's index
    except OSError as e: print(f"ERROR: Renombrando creador {old_creator_path_obj}: {e}"); flash(f"Error al renombrar creador: {e}", "error"); return redirect(redirect_url_on_fail)
    except Exception as e: print(f"ERROR: Renombrando creador {old_creator_path_obj}: {e}"); flash("Error inesperado.", "error"); return redirect(redirect_for('index')) # Redirect to index on unexpected error


# --- FEATURE: Reorganize Images ---
@app.route('/reorganize_group/<path:group_name_encoded>', methods=['POST'])
def reorganize_group(group_name_encoded):
    if not current_selection["creator_dir"]: flash("Operación no permitida.", "error"); return redirect(url_for('index'))
    group_name = unquote(group_name_encoded)

    redirect_url_on_fail = url_for('show_group', group_name_encoded=group_name_encoded)

    if not is_safe_name(group_name): flash("Nombre de grupo inválido.", "error"); return redirect(url_for('index'))

    group_dir_path = get_safe_path(current_selection["creator_dir"], group_name)
    if not group_dir_path or not group_dir_path.is_dir(): flash(f"Grupo '{group_name}' no encontrado.", "error"); return redirect(url_for('index'))

    # Get data from the form
    # The form sends input fields named like "order_encodedfilename" and "filename_encodedfilename"
    order_data = []
    for key, value in request.form.items():
        if key.startswith('order_'):
            try:
                # Extract the original encoded filename from the input name
                encoded_filename = key[len('order_'):]
                # Get the desired number
                order_num_str = value.strip()
                if not order_num_str: raise ValueError("Empty number")
                order_num = int(order_num_str)

                # Get the actual filename from the corresponding hidden input
                original_encoded_filename = request.form.get(f'filename_{encoded_filename}')

                if not original_encoded_filename or original_encoded_filename != encoded_filename:
                     # Basic consistency check - something is wrong with the form data
                     print(f"WARN: reorganize_group - Data mismatch for key {key}");
                     flash("Error interno: Datos del formulario inconsistentes.", "error")
                     return redirect(redirect_url_on_fail) # Abort early on bad form data

                # Decode the original filename for validation and processing
                original_filename = unquote(original_encoded_filename)

                # Validate filename and order number
                if not is_safe_name(original_filename) or Path(original_filename).suffix.lower() not in ALLOWED_IMAGE_EXTENSIONS:
                     print(f"WARN: reorganize_group - Unsafe or invalid filename in form: {original_filename}");
                     flash(f"Nombre de archivo inválido en el formulario: {original_filename}", "error")
                     return redirect(redirect_url_on_fail) # Abort early
                if order_num <= 0:
                     flash(f"Número de orden inválido ({order_num}) para {original_filename}.", "error");
                     return redirect(redirect_url_on_fail) # Abort early

                order_data.append((order_num, original_filename))
            except ValueError:
                flash(f"Número de orden inválido ('{value}') para un archivo.", "error"); return redirect(redirect_url_on_fail)
            except Exception as e:
                print(f"ERROR: reorganize_group - Processing form data for key {key}: {e}");
                flash("Error procesando datos del formulario.", "error"); return redirect(redirect_url_on_fail)

    if not order_data:
        flash("No se recibió información de imágenes para reorganizar.", "error"); return redirect(redirect_url_on_fail)

    # Sort images based on the desired order number, then by original name for stability on duplicate numbers
    order_data.sort(key=lambda x: (x[0], x[1])) # Sort by number (x[0]), then filename (x[1])

    success_count = 0
    failed_renames = []
    total_images = len(order_data)

    # Determine padding for new filenames (e.g., 001, 010, 100)
    padding = len(str(total_images))
    if padding < 3: padding = 3 # Minimum padding of 3 digits

    # Iterate through the sorted list and rename files sequentially
    for i, (order_num, original_filename) in enumerate(order_data):
        # Construct the new filename (NNN.ext) using the index in the sorted list (0-based)
        new_filename = f"{i+1:0{padding}d}{Path(original_filename).suffix}" # Use 1-based index for filenames

        old_file_path = get_safe_path(group_dir_path, original_filename)
        # Construct the new path using the group_dir_path as base (already validated)
        new_file_path = group_dir_path / new_filename # Path handles joining safely

        # Safety checks: ensure old file path is valid/exists and new path is within the group dir
        if not old_file_path or not old_file_path.is_file():
             print(f"WARN: reorganize_group - Source file not found or invalid during rename: {old_file_path}");
             failed_renames.append(original_filename)
             continue # Skip this rename

        if not is_safe_path(group_dir_path, new_file_path):
             print(f"SECURITY ERROR: reorganize_group - Attempted to create file outside group dir: {new_file_path}");
             failed_renames.append(original_filename)
             continue # Skip this rename

        # Only attempt rename if the new name is different from the old name
        if old_file_path != new_file_path:
            try:
                os.rename(old_file_path, new_file_path)
                success_count += 1
                # print(f"INFO: Renamed: {old_file_path.name} -> {new_file_path.name}") # Debug
            except OSError as e:
                print(f"ERROR: Renaming {old_file_path}: {e}"); failed_renames.append(original_filename)
            except Exception as e:
                print(f"ERROR: Renaming {old_file_path}: {e}"); failed_renames.append(original_filename)
        else:
            # File is already in the correct position and has the correct name (NNN.ext)
            # or user assigned a number that coincidentally resulted in the same sequential name
            pass # No rename needed

    if success_count > 0:
        flash(f"Reorganización completada. {success_count} imágenes renombradas.", "success")
    if failed_renames:
        flash(f"Error al renombrar las siguientes imágenes: {', '.join(failed_renames)}", "error")
    elif success_count == 0 and total_images > 0:
         flash("No se necesitaron cambios de nombre (ya estaban en el orden especificado).", "info")
    elif total_images == 0:
         flash("No hay imágenes en este grupo para reorganizar.", "info")


    return redirect(redirect_url_on_fail) # Redirect back to the group page to see new order

# --- FEATURE: Clean Empty Folders ---
@app.route('/cleanup_empty_folders_root', methods=['POST'])
def cleanup_empty_folders_root():
    """Cleans empty folders within the ROOT_GALLERY_DIR."""
    if not ROOT_GALLERY_DIR.is_dir():
        flash(f"Directorio raíz '{ROOT_GALLERY_DIR}' no encontrado.", "error")
        return redirect(url_for('index')) # Redirect to selector

    # Need to resolve ROOT_GALLERY_DIR once for safe path comparison
    try:
         root_resolved = ROOT_GALLERY_DIR.resolve(strict=True)
    except (FileNotFoundError, Exception) as e:
         print(f"ERROR: cleanup_empty_folders_root - Invalid ROOT_GALLERY_DIR: {ROOT_GALLERY_DIR}, {e}");
         flash(f"Error al validar el directorio raíz: {e}", "error")
         return redirect(url_for('index'))


    empty_dirs_to_delete = find_empty_dirs(ROOT_GALLERY_DIR)
    deleted_count = 0
    failed_count = 0
    failed_list = []

    # Sort by path depth ascending so parents are attempted last (safer with rmdir)
    # Although find_empty_dirs returns deepest first, attempting rmdir on parents last is still good
    empty_dirs_to_delete.sort(key=lambda p: len(p.parts))

    for empty_dir_path in empty_dirs_to_delete:
        # Double check safety although find_empty_dirs should filter
        if not is_safe_path(root_resolved, empty_dir_path) or not empty_dir_path.is_dir() or list(empty_dir_path.iterdir()):
             print(f"SECURITY WARNING: Skipping potentially unsafe or non-empty dir during cleanup: {empty_dir_path}")
             failed_count += 1
             failed_list.append(str(empty_dir_path))
             continue

        try:
            os.rmdir(empty_dir_path) # rmdir only removes truly empty directories
            print(f"INFO: Removed empty dir: {empty_dir_path}")
            deleted_count += 1
        except OSError as e:
            print(f"ERROR: Could not remove empty dir {empty_dir_path}: {e}")
            failed_count += 1
            failed_list.append(str(empty_dir_path))
        except Exception as e:
            print(f"ERROR: Unexpected error removing empty dir {empty_dir_path}: {e}")
            failed_count += 1
            failed_list.append(str(empty_dir_path))


    if deleted_count > 0:
        flash(f"Limpieza completada. Eliminadas {deleted_count} carpetas vacías bajo '{ROOT_GALLERY_DIR.name}'.", "success")
    else:
        flash("No se encontraron carpetas vacías para eliminar.", "info")

    if failed_count > 0:
        flash(f"No se pudieron eliminar {failed_count} carpetas: {', '.join(failed_list)} (pueden no estar vacías o haber un error).", "error")

    return redirect(url_for('index')) # Redirect back to selector

@app.route('/cleanup_empty_folders_creator', methods=['POST'])
def cleanup_empty_folders_creator():
    """Cleans empty folders within the current creator's directory."""
    if not current_selection["creator_dir"]:
        flash("Selecciona un creador primero para limpiar sus carpetas vacías.", "error")
        return redirect(url_for('index'))

    creator_dir = current_selection["creator_dir"]
    creator_name = current_selection["creator_name"] # Get name before potential reset

    # Re-validate creator_dir using ROOT_GALLERY_DIR as base
    creator_dir_path_obj = get_safe_path(ROOT_GALLERY_DIR, Path(creator_dir).name) # Get path obj from name, base is ROOT

    if not creator_dir_path_obj or not creator_dir_path_obj.is_dir():
         flash(f"Directorio del creador inválido para la limpieza.", "error")
         print(f"ERROR: cleanup_empty_folders_creator - Invalid creator_dir: {creator_dir}")
         current_selection.update({"creator_dir": None, "creator_name": None})
         return redirect(url_for('index'))

    # Resolve the creator path for safe comparison
    try:
         creator_resolved = creator_dir_path_obj.resolve(strict=True)
    except (FileNotFoundError, Exception) as e:
         print(f"ERROR: cleanup_empty_folders_creator - Cannot resolve creator_dir: {creator_dir_path_obj}, {e}");
         flash(f"Error al validar el directorio del creador: {e}", "error")
         current_selection.update({"creator_dir": None, "creator_name": None})
         return redirect(url_for('index'))


    empty_dirs_to_delete = find_empty_dirs(creator_dir_path_obj)
    deleted_count = 0
    failed_count = 0
    failed_list = []

    # Sort by path depth ascending
    empty_dirs_to_delete.sort(key=lambda p: len(p.parts))

    for empty_dir_path in empty_dirs_to_delete:
        # Double check safety - ensure dir is within the *resolved* creator dir and is empty
        if not is_safe_path(creator_resolved, empty_dir_path) or not empty_dir_path.is_dir() or list(empty_dir_path.iterdir()):
             print(f"SECURITY WARNING: Skipping potentially unsafe or non-empty dir during creator cleanup: {empty_dir_path}")
             failed_count += 1
             failed_list.append(str(empty_dir_path))
             continue
        try:
            os.rmdir(empty_dir_path)
            print(f"INFO: Removed empty dir: {empty_dir_path}")
            deleted_count += 1
        except OSError as e:
            print(f"ERROR: Could not remove empty dir {empty_dir_path}: {e}")
            failed_count += 1
            failed_list.append(str(empty_dir_path))
        except Exception as e:
            print(f"ERROR: Unexpected error removing empty dir {empty_dir_path}: {e}")
            failed_count += 1
            failed_list.append(str(empty_dir_path))


    if deleted_count > 0:
        flash(f"Limpieza completada. Eliminadas {deleted_count} carpetas vacías del creador '{creator_name}'.", "success")
    else:
        flash(f"No se encontraron carpetas vacías en el creador '{creator_name}'.", "info")

    if failed_count > 0:
        flash(f"No se pudieron eliminar {failed_count} carpetas: {', '.join(failed_list)}", "error")


    # Redirect back to the creator's index page
    return redirect(url_for('index'))


# --- FEATURE: Merge Groups ---
@app.route('/merge_groups', methods=['POST'])
def merge_groups():
    if not current_selection["creator_dir"]: flash("Operación no permitida.", "error"); return redirect(url_for('index'))

    creator_dir = current_selection["creator_dir"]
    creator_name = current_selection["creator_name"] # For flash messages
    selected_groups_encoded = request.form.getlist('selected_groups')
    new_group_name = request.form.get('new_group_name', '').strip()

    redirect_url = url_for('index') # Default redirect is creator index

    if not selected_groups_encoded or len(selected_groups_encoded) < 2:
        flash("Selecciona al menos dos grupos para fusionar.", "error"); return redirect(redirect_url)
    if not is_safe_name(new_group_name):
        flash("Nombre para el nuevo grupo fusionado inválido.", "error"); return redirect(redirect_url)

    # Decode and validate selected group names and get their paths
    selected_group_paths = []
    selected_group_names = []
    for encoded_name in selected_groups_encoded:
        group_name = unquote(encoded_name)
        if not is_safe_name(group_name):
            flash(f"Nombre de grupo seleccionado inválido: {group_name}", "error"); return redirect(redirect_url)

        # Get the safe path relative to the creator directory
        group_path = get_safe_path(creator_dir, group_name)

        if not group_path or not group_path.is_dir():
            flash(f"Grupo seleccionado no encontrado o inválido: {group_name}", "error"); return redirect(redirect_url)

        selected_group_paths.append(group_path)
        selected_group_names.append(group_name)

    # Check if the new group name is one of the selected groups (should not happen with a new name input, but safety)
    if new_group_name in selected_group_names:
        flash(f"El nombre del nuevo grupo '{new_group_name}' es uno de los grupos seleccionados para fusionar.", "error"); return redirect(redirect_url)


    # Determine the path for the new merged group
    # Get the safe path relative to the creator directory
    new_group_path = get_safe_path(creator_dir, new_group_name)
    if not new_group_path:
        flash(f"Ruta para el nuevo grupo '{new_group_name}' inválida/insegura.", "error"); return redirect(redirect_url)

    # Check if the target path already exists and is not one of the source groups
    if new_group_path.exists():
         # If it exists, it must be a directory and not one of the source directories
         if new_group_path.is_dir() and new_group_path not in selected_group_paths:
             # Require non-existence for simplicity initially.
             flash(f"El grupo de destino '{new_group_name}' ya existe.", "error"); return redirect(redirect_url)
         elif new_group_path.is_file():
             flash(f"Ya existe un archivo con el nombre '{new_group_name}'.", "error"); return redirect(redirect_url)


    # Create the new directory if it doesn't exist
    try:
        # Use parents=True to create any necessary parent directories within the creator_dir
        # Use exist_ok=False to ensure we aren't overwriting an existing folder
        new_group_path.mkdir(parents=True, exist_ok=False)
        print(f"INFO: Creado nuevo grupo para fusión: {new_group_path}")
    except FileExistsError:
        # This case should be caught by the check above, but good to have
        flash(f"Error: El grupo de destino '{new_group_name}' ya existía inesperadamente.", "error"); return redirect(redirect_url)
    except OSError as e:
        print(f"ERROR: Creando directorio para fusión {new_group_path}: {e}"); flash(f"Error al crear el nuevo grupo '{new_group_name}': {e}", "error"); return redirect(redirect_url)
    except Exception as e:
        print(f"ERROR: Creando directorio para fusión {new_group_path}: {e}"); flash("Error inesperado al crear el nuevo grupo.", "error"); return redirect(redirect_url)


    moved_count = 0
    skipped_count = 0
    skipped_files = [] # Store names of skipped files
    deleted_groups_count = 0
    failed_delete_groups = [] # Store names of groups not deleted

    # Iterate through source groups and move files
    for source_group_path in selected_group_paths:
        try:
            # Check if source group still exists and is a directory and is within the creator_dir
            if not source_group_path.is_dir() or not is_safe_path(creator_dir, source_group_path):
                 print(f"WARN: Source group disappeared or became invalid during merge: {source_group_path}");
                 flash(f"Advertencia: El grupo de origen '{source_group_path.name}' ya no es válido. Saltando.", "warning")
                 continue

            # Get image files in the source group
            source_image_files = [f for f in source_group_path.iterdir() if f.is_file() and f.suffix.lower() in ALLOWED_IMAGE_EXTENSIONS]

            for source_file_path in source_image_files:
                # Ensure source file is safe (redundant with group_path safety, but harmless)
                if not is_safe_path(source_group_path, source_file_path):
                     print(f"SECURITY WARNING: Skipping potentially unsafe source file during merge: {source_file_path}");
                     skipped_count += 1
                     skipped_files.append(source_file_path.name)
                     continue

                target_file_name = source_file_path.name
                target_file_path = new_group_path / target_file_name

                # Conflict resolution: If target file exists, rename the incoming file
                conflict_counter = 1
                original_stem = source_file_path.stem
                original_suffix = source_file_path.suffix

                # Loop to find a unique name if conflict exists
                while target_file_path.exists():
                    target_file_name = f"{original_stem}_{conflict_counter}{original_suffix}"
                    target_file_path = new_group_path / target_file_name
                    conflict_counter += 1
                    if conflict_counter > 10000: # Safety break for excessive conflicts
                        print(f"ERROR: Too many conflicts for {source_file_path.name}, skipping.");
                        skipped_count += 1
                        skipped_files.append(source_file_path.name)
                        target_file_path = None # Mark as not to move
                        break # Exit while loop

                if target_file_path: # If not skipped due to too many conflicts
                     # Re-validate the target path is still within the new group dir
                     if not is_safe_path(new_group_path, target_file_path):
                          print(f"SECURITY ERROR: merge_groups - Attempted to create file outside target group dir: {target_file_path}");
                          skipped_count += 1
                          skipped_files.append(source_file_path.name)
                          continue

                     try:
                         shutil.move(source_file_path, target_file_path)
                         moved_count += 1
                         # print(f"INFO: Moved: {source_file_path.name} -> {target_file_path.name}") # Debug
                     except OSError as e:
                         print(f"ERROR: Moving {source_file_path} to {target_file_path}: {e}")
                         skipped_count += 1
                         skipped_files.append(source_file_path.name)
                     except Exception as e:
                         print(f"ERROR: Moving {source_file_path} to {target_file_path}: {e}")
                         skipped_count += 1
                         skipped_files.append(source_file_path.name)


            # After moving files, attempt to remove the source group directory if it's empty
            try:
                 # Check if the directory is empty before attempting rmdir
                 if not list(source_group_path.iterdir()):
                     os.rmdir(source_group_path)
                     print(f"INFO: Removed empty source group after merge: {source_group_path}")
                     deleted_groups_count += 1
                 else:
                     print(f"WARN: Source group not empty after moving files: {source_group_path}")
                     failed_delete_groups.append(source_group_path.name) # Didn't delete, maybe log as failed or just warn
            except OSError as e:
                 print(f"ERROR: Could not remove source group {source_group_path}: {e}")
                 failed_delete_groups.append(source_group_path.name)
            except Exception as e:
                 print(f"ERROR: Could not remove source group {source_group_path}: {e}")
                 failed_delete_groups.append(source_group_path.name)


        except OSError as e:
            print(f"ERROR: Processing source group {source_group_path} during merge: {e}")
            # Continue with other groups even if one fails
            flash(f"Error procesando grupo '{source_group_path.name}'.", "error")
            continue
        except Exception as e:
            print(f"ERROR: Processing source group {source_group_path} during merge: {e}")
            flash(f"Error inesperado procesando grupo '{source_group_path.name}'.", "error")
            continue


    # Provide summary feedback
    if moved_count > 0:
        flash(f"Fusión completada. Movidas {moved_count} imágenes al grupo '{new_group_name}'.", "success")
        # Redirect to the newly merged group if successful moves occurred
        redirect_url = url_for('show_group', group_name_encoded=quote(new_group_name))
    else:
         flash(f"No se movieron imágenes durante la fusión de grupos del creador '{creator_name}' (puede que los grupos estuvieran vacíos o hubiera errores).", "info")


    if skipped_count > 0:
        flash(f"Saltadas {skipped_count} imágenes debido a errores o conflictos de nombre.", "error")
        # Optionally log or show the skipped files list: print(f"Skipped files: {skipped_files}")
    if deleted_groups_count > 0:
        flash(f"Eliminadas {deleted_groups_count} carpetas de origen vacías.", "success")
    # Only show failed deletions if they actually happened and there were groups to delete
    if failed_delete_groups and (deleted_groups_count > 0 or skipped_count > 0 or moved_count > 0):
         flash(f"No se pudieron eliminar las siguientes carpetas de origen (puede que no estuvieran vacías): {', '.join(failed_delete_groups)}", "warning")


    # Redirect to the final destination (new group page if successful, otherwise creator index)
    return redirect(redirect_url)


# --- Manejo de Errores ---
@app.errorhandler(400)
def bad_request(error):
    return Response(f"{HTML_STYLE_BLOCK}<body><div class='container'><p class='error'>Solicitud Inválida: {error.description}</p><p><a href='{build_absolute_url('index')}'>Volver al inicio</a></p></div></body>", status=400, mimetype='text/html')

@app.errorhandler(404)
def not_found(error):
    return Response(f"{HTML_STYLE_BLOCK}<body><div class='container'><p class='error'>No Encontrado: {error.description}</p><p><a href='{build_absolute_url('index')}'>Volver al inicio</a></p></div></body>", status=404, mimetype='text/html')

@app.errorhandler(500)
def internal_error(error):
    return Response(f"{HTML_STYLE_BLOCK}<body><div class='container'><p class='error'>Error Interno del Servidor: {error.description or ''}</p><p><a href='{build_absolute_url('index')}'>Volver al inicio</a></p></div></body>", status=500, mimetype='text/html')


# --- Inicio del Servidor ---
def run_server(port):
    print(f" * Directorio base de la galería: {ROOT_GALLERY_DIR}")
    ip = get_local_ip()
    print(f" * Intentando iniciar servidor en http://{ip}:{port}/")
    try:
        # Check if ROOT_GALLERY_DIR exists and is a directory early
        if not ROOT_GALLERY_DIR.is_dir():
             print(f"ERROR FATAL: El directorio ROOT_GALLERY_DIR '{ROOT_GALLERY_DIR}' no existe o no es un directorio.")
             # Do not proceed with app.run
             sys.exit(1) # Exit the program

        # Use a background thread to open the browser window after a small delay
        threading.Timer(1.5, lambda: webbrowser.open_new(f'http://{ip}:{port}/')).start()
        # Use debug=False and threaded=True for better stability in development/basic use
        # For production, use a production-ready WSGI server like Gunicorn or uWSGI
        app.run(host='0.0.0.0', port=port, debug=False, threaded=True) # host='0.0.0.0' allows access from other machines
    except socket.gaierror:
        print(f"ERROR: No se pudo resolver el host. Asegúrate de que tu red está configurada correctamente.")
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"ERROR: El puerto {port} ya está en uso. Intenta con otro puerto.")
        else:
            print(f"ERROR: Error del sistema operativo: {e}")
    except Exception as e:
        print(f"ERROR: Error inesperado al iniciar el servidor: {e}")


if __name__ == '__main__':
    # Allow port to be specified as a command-line argument
    port = DEFAULT_PORT
    if len(sys.argv) > 1:
        try: port = int(sys.argv[1])
        except ValueError: print(f"WARN: Puerto inválido '{sys.argv[1]}'. Usando el puerto por defecto {DEFAULT_PORT}."); port = DEFAULT_PORT

    run_server(port) # Call run_server which includes the ROOT_GALLERY_DIR check
