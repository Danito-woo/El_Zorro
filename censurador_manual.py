import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk, ImageDraw, ImageFilter
import os

# Tamaño máximo para mostrar la imagen en la interfaz (para evitar ventanas enormes)
MAX_DISPLAY_WIDTH = 800
MAX_DISPLAY_HEIGHT = 600

class SuperCensuradorMagico:
    def __init__(self, master):
        self.master = master
        self.master.title("SUPER CENSURADOR MÁGICO ✨")
        self.master.geometry("900x750") # Tamaño inicial ventana

        self.folder_path = ""
        self.image_files = []
        self.current_image_index = -1
        self.original_image = None # Imagen original cargada con Pillow
        self.display_image_tk = None # Imagen formateada para Tkinter
        self.scale_factor = 1.0 # Factor de escala entre original y mostrada
        self.rectangles_coords = [] # Coordenadas de los rectángulos dibujados (en coords de display)
        self.drawn_rectangles = [] # IDs de los rectángulos en el canvas

        # --- Widgets ---
        # Frame superior para controles de carpeta
        self.top_frame = ttk.Frame(master)
        self.top_frame.pack(pady=10, padx=10, fill=tk.X)

        self.btn_select_folder = ttk.Button(self.top_frame, text="Seleccionar Carpeta", command=self.select_folder)
        self.btn_select_folder.pack(side=tk.LEFT, padx=5)

        self.lbl_folder_path = ttk.Label(self.top_frame, text="Ninguna carpeta seleccionada")
        self.lbl_folder_path.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # Canvas para mostrar la imagen y dibujar
        self.canvas = tk.Canvas(master, bg="gray", cursor="cross")
        self.canvas.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.start_x = None
        self.start_y = None
        self.current_rect_id = None

        # Frame inferior para navegación y controles de pixelación
        self.bottom_frame = ttk.Frame(master)
        self.bottom_frame.pack(pady=10, padx=10, fill=tk.X)

        self.btn_prev = ttk.Button(self.bottom_frame, text="<< Anterior", command=self.prev_image, state=tk.DISABLED)
        self.btn_prev.pack(side=tk.LEFT, padx=5)

        self.lbl_image_name = ttk.Label(self.bottom_frame, text="Imagen: N/A")
        self.lbl_image_name.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)

        self.btn_next = ttk.Button(self.bottom_frame, text="Siguiente >>", command=self.next_image, state=tk.DISABLED)
        self.btn_next.pack(side=tk.LEFT, padx=5)

        # Controles de pixelación
        self.pixel_frame = ttk.Frame(master)
        self.pixel_frame.pack(pady=5, padx=10, fill=tk.X)

        self.lbl_pixel_level = ttk.Label(self.pixel_frame, text="Nivel de Pixelación:")
        self.lbl_pixel_level.pack(side=tk.LEFT, padx=5)

        # Slider para nivel de pixelación (valores más bajos = más pixelado/bloques más grandes)
        self.pixel_level = tk.IntVar(value=10) # Valor inicial (10-50 parece razonable)
        self.scale_pixel = ttk.Scale(self.pixel_frame, from_=2, to=50, orient=tk.HORIZONTAL, variable=self.pixel_level)
        self.scale_pixel.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        self.btn_clear_rects = ttk.Button(self.pixel_frame, text="Borrar Marcas", command=self.clear_rectangles)
        self.btn_clear_rects.pack(side=tk.LEFT, padx=5)

        self.btn_pixelate = ttk.Button(self.pixel_frame, text="Pixelar y Guardar", command=self.pixelate_and_save, state=tk.DISABLED)
        self.btn_pixelate.pack(side=tk.LEFT, padx=5)


    def select_folder(self):
        """Abre el diálogo para seleccionar una carpeta."""
        path = filedialog.askdirectory()
        if path:
            self.folder_path = path
            self.lbl_folder_path.config(text=self.folder_path)
            self.load_image_list()
            if self.image_files:
                self.current_image_index = 0
                self.load_image()
                self.update_navigation_buttons()
                self.btn_pixelate.config(state=tk.NORMAL)
            else:
                messagebox.showinfo("Info", "No se encontraron imágenes soportadas (.png, .jpg, .jpeg, .bmp, .gif) en la carpeta.")
                self.reset_interface()

    def load_image_list(self):
        """Carga la lista de archivos de imagen de la carpeta seleccionada."""
        self.image_files = []
        valid_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif')
        try:
            for fname in os.listdir(self.folder_path):
                if fname.lower().endswith(valid_extensions):
                    self.image_files.append(os.path.join(self.folder_path, fname))
            self.image_files.sort() # Ordenar alfabéticamente
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer la carpeta: {e}")
            self.reset_interface()

    def reset_interface(self):
        """Resetea la interfaz cuando no hay imágenes o hay error."""
        self.canvas.delete("all")
        self.lbl_image_name.config(text="Imagen: N/A")
        self.btn_prev.config(state=tk.DISABLED)
        self.btn_next.config(state=tk.DISABLED)
        self.btn_pixelate.config(state=tk.DISABLED)
        self.original_image = None
        self.display_image_tk = None
        self.clear_rectangles_data()


    def load_image(self):
        """Carga y muestra la imagen actual en el canvas."""
        if not self.image_files or self.current_image_index < 0:
            return

        image_path = self.image_files[self.current_image_index]
        try:
            self.original_image = Image.open(image_path)
            # Copia para mostrar (evita modificar la original al redimensionar para display)
            img_display = self.original_image.copy()

            # Calcular factor de escala y redimensionar si es necesario
            img_w, img_h = img_display.size
            self.scale_factor = 1.0
            if img_w > MAX_DISPLAY_WIDTH or img_h > MAX_DISPLAY_HEIGHT:
                ratio_w = MAX_DISPLAY_WIDTH / img_w
                ratio_h = MAX_DISPLAY_HEIGHT / img_h
                self.scale_factor = min(ratio_w, ratio_h)
                new_w = int(img_w * self.scale_factor)
                new_h = int(img_h * self.scale_factor)
                img_display = img_display.resize((new_w, new_h), Image.Resampling.LANCZOS)

            # Convertir a formato Tkinter
            self.display_image_tk = ImageTk.PhotoImage(img_display)

            # Mostrar en canvas
            self.canvas.delete("all") # Borrar contenido anterior
            self.canvas.config(width=img_display.width, height=img_display.height)
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.display_image_tk)

            # Actualizar etiqueta nombre
            self.lbl_image_name.config(text=f"Imagen: {os.path.basename(image_path)} ({self.current_image_index + 1}/{len(self.image_files)})")

            # Limpiar rectángulos anteriores
            self.clear_rectangles_data()

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar la imagen {os.path.basename(image_path)}:\n{e}")
            # Intentar pasar a la siguiente imagen si es posible
            self.image_files.pop(self.current_image_index)
            if self.current_image_index >= len(self.image_files):
                 self.current_image_index = len(self.image_files) -1
            if self.image_files:
                self.load_image()
            else:
                self.reset_interface()

    def update_navigation_buttons(self):
        """Habilita o deshabilita los botones de navegación."""
        if not self.image_files:
            self.btn_prev.config(state=tk.DISABLED)
            self.btn_next.config(state=tk.DISABLED)
            return

        self.btn_prev.config(state=tk.NORMAL if self.current_image_index > 0 else tk.DISABLED)
        self.btn_next.config(state=tk.NORMAL if self.current_image_index < len(self.image_files) - 1 else tk.DISABLED)

    def prev_image(self):
        """Va a la imagen anterior."""
        if self.current_image_index > 0:
            self.current_image_index -= 1
            self.load_image()
            self.update_navigation_buttons()

    def next_image(self):
        """Va a la imagen siguiente."""
        if self.current_image_index < len(self.image_files) - 1:
            self.current_image_index += 1
            self.load_image()
            self.update_navigation_buttons()

    # --- Manejo de Dibujo de Rectángulos ---
    def on_press(self, event):
        """Inicio de arrastre para dibujar rectángulo."""
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        # Crear rectángulo inicial (muy pequeño)
        self.current_rect_id = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x + 1, self.start_y + 1, outline="red", width=2)

    def on_drag(self, event):
        """Actualiza el rectángulo mientras se arrastra."""
        if self.current_rect_id:
            cur_x = self.canvas.canvasx(event.x)
            cur_y = self.canvas.canvasy(event.y)
            self.canvas.coords(self.current_rect_id, self.start_x, self.start_y, cur_x, cur_y)

    def on_release(self, event):
        """Finaliza el dibujo del rectángulo."""
        if self.current_rect_id:
            end_x = self.canvas.canvasx(event.x)
            end_y = self.canvas.canvasy(event.y)

            # Asegurar coordenadas válidas (x1 < x2, y1 < y2)
            x1 = min(self.start_x, end_x)
            y1 = min(self.start_y, end_y)
            x2 = max(self.start_x, end_x)
            y2 = max(self.start_y, end_y)

            # No guardar rectángulos demasiado pequeños
            if abs(x1 - x2) > 3 and abs(y1 - y2) > 3:
                self.rectangles_coords.append((x1, y1, x2, y2))
                self.drawn_rectangles.append(self.current_rect_id) # Guardar ID para borrarlo si es necesario
                # print(f"Rectángulo añadido (display coords): {x1, y1, x2, y2}")
            else:
                 self.canvas.delete(self.current_rect_id) # Borrar el rectángulo pequeño

            self.current_rect_id = None # Resetear para el próximo rectángulo
            self.start_x = None
            self.start_y = None

    def clear_rectangles(self):
        """Borra los rectángulos dibujados en el canvas."""
        for rect_id in self.drawn_rectangles:
            self.canvas.delete(rect_id)
        self.clear_rectangles_data()

    def clear_rectangles_data(self):
         """Limpia la lista de coordenadas y IDs de rectángulos."""
         self.rectangles_coords = []
         self.drawn_rectangles = []
         self.current_rect_id = None
         self.start_x = None
         self.start_y = None


    # --- Pixelación ---
    def pixelate_and_save(self):
        """Aplica la pixelación a las áreas seleccionadas y guarda la imagen."""
        if not self.original_image:
            messagebox.showwarning("Advertencia", "No hay ninguna imagen cargada.")
            return
        if not self.rectangles_coords:
            messagebox.showwarning("Advertencia", "No has marcado ninguna zona para pixelar.\n(Haz clic y arrastra sobre la imagen)")
            return

        try:
            # Crear una copia de la imagen original para modificarla
            pixelated_img = self.original_image.copy()
            # Convertir a RGBA si es necesario para asegurar canal alfa si se usa en el futuro
            if pixelated_img.mode != 'RGBA':
                 pixelated_img = pixelated_img.convert('RGBA')

            level = self.pixel_level.get() # Obtener nivel del slider

            for rect_coords_display in self.rectangles_coords:
                # Convertir coordenadas del display a coordenadas de la imagen original
                x1_disp, y1_disp, x2_disp, y2_disp = rect_coords_display
                # Aplicar el inverso del factor de escala
                x1_orig = int(x1_disp / self.scale_factor)
                y1_orig = int(y1_disp / self.scale_factor)
                x2_orig = int(x2_disp / self.scale_factor)
                y2_orig = int(y2_disp / self.scale_factor)

                # Asegurar que las coordenadas estén dentro de los límites de la imagen original
                img_w, img_h = self.original_image.size
                x1_orig = max(0, min(x1_orig, img_w - 1))
                y1_orig = max(0, min(y1_orig, img_h - 1))
                x2_orig = max(0, min(x2_orig, img_w)) # El límite superior es exclusivo en crop
                y2_orig = max(0, min(y2_orig, img_h)) # El límite superior es exclusivo en crop

                # Validar que el área tenga tamaño > 0
                if x2_orig <= x1_orig or y2_orig <= y1_orig:
                    continue

                # 1. Recortar la región
                region = pixelated_img.crop((x1_orig, y1_orig, x2_orig, y2_orig))

                # 2. Calcular el tamaño del bloque de pixelación
                region_w, region_h = region.size
                # Tamaño de la imagen reducida (más pequeño = bloques más grandes)
                # Aseguramos un mínimo de 1 pixel
                pixel_w = max(1, region_w // level)
                pixel_h = max(1, region_h // level)

                # 3. Reducir la imagen
                small_region = region.resize((pixel_w, pixel_h), Image.Resampling.BILINEAR)

                # 4. Agrandar la imagen pequeña al tamaño original de la región usando NEAREST para crear los bloques
                pixelated_region = small_region.resize(region.size, Image.Resampling.NEAREST)

                # 5. Pegar la región pixelada de vuelta en la imagen
                pixelated_img.paste(pixelated_region, (x1_orig, y1_orig), pixelated_region.split()[-1] if pixelated_region.mode == 'RGBA' else None) # Usar máscara alfa si existe

            # Construir el nuevo nombre de archivo
            current_path = self.image_files[self.current_image_index]
            base, ext = os.path.splitext(current_path)
            new_path = f"{base}_pixelado{ext}"

            # Guardar la imagen pixelada
            # Si la original era JPG, convertir a RGB antes de guardar para evitar problemas
            save_img = pixelated_img
            if ext.lower() in ['.jpg', '.jpeg'] and save_img.mode == 'RGBA':
                 save_img = save_img.convert('RGB')

            save_img.save(new_path)

            messagebox.showinfo("Éxito", f"Imagen guardada como:\n{os.path.basename(new_path)}")
            # Opcional: Limpiar las marcas después de guardar
            self.clear_rectangles()
            # Opcional: Actualizar la lista de imágenes por si el usuario quiere ver la recién guardada
            # self.load_image_list() # Puede ser confuso, mejor dejar que el usuario reabra la carpeta si quiere.

        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error al pixelar o guardar:\n{e}")


# --- Ejecución ---
if __name__ == "__main__":
    root = tk.Tk()
    app = SuperCensuradorMagico(root)
    root.mainloop()