import os
import re
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
# Importamos afx junto con los demás módulos de moviepy.editor
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, VideoFileClip, afx

class ImageVideoGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Image to Video Converter")
        self.configure(bg="#2e2e2e")  # Dark background
        self.geometry("1000x600")

        self.image_list = []
        self.durations = {}
        self.audio_file = None
        self.intro_file = None
        self.outro_file = None
        self.preview_label = None

        self._build_widgets()

    def _build_widgets(self):
        # Paned window to split tree and preview
        paned = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # Left frame: controls + treeview
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)

        # Folder selection
        btn_frame = tk.Frame(left_frame, bg="#2e2e2e")
        btn_frame.pack(pady=10, fill=tk.X)

        tk.Button(btn_frame, text="Seleccionar Carpeta", command=self.select_folder).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Seleccionar Música", command=self.select_audio).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Intro/Outro", command=self.select_intro_outro).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Exportar Video", command=self.export_video).pack(side=tk.LEFT, padx=5)

        # Treeview for images and durations
        cols = ("imagen", "duración(s)")
        self.tree = ttk.Treeview(left_frame, columns=cols, show="headings", height=25)
        self.tree.heading("imagen", text="Imagen")
        self.tree.heading("duración(s)", text="Duración (s)")
        self.tree.column("duración(s)", width=100)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Bindings
        self.tree.bind('<Double-1>', self._edit_duration)
        self.tree.bind('<<TreeviewSelect>>', self._preview_media)

        # Right frame: preview
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=1)
        self.preview_label = tk.Label(right_frame, bg="black")
        self.preview_label.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def select_folder(self):
        folder = filedialog.askdirectory(initialdir=r"E:\El_Zorro\downloads")
        if not folder:
            return
        files = os.listdir(folder)
        # Find numbered images, prefer censored
        pattern = re.compile(r"^(\d+)(?:_pixelado)?\.(png|jpg|jpeg|bmp|gif)$", re.IGNORECASE)
        matches = {}
        for f in files:
            m = pattern.match(f)
            if m:
                num = int(m.group(1))
                is_censored = '_pixelado' in f.lower()
                if num not in matches or is_censored:
                    matches[num] = f
        ordered = [os.path.join(folder, matches[num]) for num in sorted(matches)] # Join path here
        # make sure intro/outro files are not included in image_list if they match pattern
        # This is a potential bug if intro/outro are in the selected folder AND match the pattern.
        # A more robust way would be to explicitly filter them out or only select based on the list derived from pattern matches.
        # For now, assuming intro/outro are typically not in the same folder selected for images.

        self.image_list = ordered
        # default duration 10s for images
        self.durations = {img: 10.0 for img in self.image_list}
        self._refresh_tree()

    def _refresh_tree(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for img in self.image_list:
            fname = os.path.basename(img)
            self.tree.insert("", tk.END, values=(fname, self.durations[img]))

    def _edit_duration(self, event):
        rowid = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if col != '#2':
            return
        x, y, width, height = self.tree.bbox(rowid, col)
        val = self.tree.set(rowid, "duración(s)")
        entry = tk.Entry(self.tree)
        entry.place(x=x, y=y, width=width, height=height)
        entry.insert(0, val)
        entry.focus()

        def save_edit(event):
            new_val = entry.get()
            try:
                d = float(new_val)
                # Find the actual image path corresponding to the treeview row
                # The treeview values are just display, we need the path from self.image_list
                item_values = self.tree.item(rowid, 'values')
                if item_values:
                    fname_in_tree = item_values[0]
                    # Find the corresponding path in self.image_list
                    img_path = next((img for img in self.image_list if os.path.basename(img) == fname_in_tree), None)
                    if img_path:
                        self.durations[img_path] = d
                        self.tree.set(rowid, "duración(s)", d)
                    else:
                        # This case should ideally not happen if self.image_list and tree are in sync
                        print(f"Warning: Could not find image path for item in tree: {fname_in_tree}")
                else:
                    print(f"Warning: Could not get item values for row: {rowid}")


            except ValueError:
                messagebox.showerror("Error", "Introduce un número válido.")
            entry.destroy()

        entry.bind('<Return>', save_edit)
        # Use a small delay for focus out to allow Return binding to fire first
        entry.bind('<FocusOut>', lambda e: self.after(10, entry.destroy))


    def _preview_media(self, event):
        sel = self.tree.selection()
        if not sel:
            # Clear preview if nothing is selected
            self.preview_label.config(image='')
            self.preview_label.image = None
            return
        rowid = sel[0]
        # Find the actual image path corresponding to the treeview row
        item_values = self.tree.item(rowid, 'values')
        if not item_values:
            return # Should not happen if something is selected
        fname_in_tree = item_values[0]
        path = next((img for img in self.image_list if os.path.basename(img) == fname_in_tree), None)

        if not path:
            # Clear preview if path not found (e.g., after deleting an item, not implemented here)
            self.preview_label.config(image='')
            self.preview_label.image = None
            return

        ext = os.path.splitext(path)[1].lower()
        # Clear previous image to prevent flickering or mixing previews
        self.preview_label.config(image='')
        self.preview_label.image = None

        try:
            if ext in ['.png', '.jpg', '.jpeg', '.bmp', '.gif']:
                img = Image.open(path)
                # Resize image to fit within preview_label dimensions while maintaining aspect ratio
                img.thumbnail((self.preview_label.winfo_width(), self.preview_label.winfo_height()))
                photo = ImageTk.PhotoImage(img)
                self.preview_label.config(image=photo)
                self.preview_label.image = photo # Keep a reference!
                img.close() # Close the PIL image file
            elif ext in ['.mp4', '.mov']:
                # Note: Previewing video frames like this is basic and might not be smooth
                # Real video preview requires more complex handling (e.g., using OpenCV or a dedicated video player widget)
                clip = VideoFileClip(path)
                if clip.duration > 0: # Ensure clip has duration before getting a frame
                     frame_time = min(1.0, clip.duration / 2.0) # Get a frame from the middle or 1s mark
                     frame = clip.get_frame(frame_time)
                     img = Image.fromarray(frame)
                     # Resize image
                     img.thumbnail((self.preview_label.winfo_width(), self.preview_label.winfo_height()))
                     photo = ImageTk.PhotoImage(img)
                     self.preview_label.config(image=photo)
                     self.preview_label.image = photo # Keep a reference!
                     img.close() # Close the PIL image
                clip.close() # Close the moviepy clip to release resources
            else:
                 # Clear preview if the file type is not supported for preview
                 self.preview_label.config(image='')
                 self.preview_label.image = None


        except Exception as e:
            # Clear preview on error
            self.preview_label.config(image='')
            self.preview_label.image = None
            # Use after to show messagebox on main thread
            self.after(0, lambda: messagebox.showerror("Error Preview", str(e)))


    def select_audio(self):
        file = filedialog.askopenfilename(filetypes=[("Audio files", "*.mp3 *.wav *.aac")])
        if file:
            self.audio_file = file
            messagebox.showinfo("Audio seleccionado", os.path.basename(file))

    def select_intro_outro(self):
        win = tk.Toplevel(self)
        win.title("Intro/Outro")
        win.configure(bg="#2e2e2e")
        win.transient(self) # Keep dialog on top of main window
        win.grab_set() # Modal behavior
        win.protocol("WM_DELETE_WINDOW", win.destroy) # Handle window closing

        def pick_intro():
            f = filedialog.askopenfilename(filetypes=[("Media files", "*.mp4 *.mov *.png *.jpg")])
            if f:
                self.intro_file = f
                lbl_intro.config(text=os.path.basename(f))

        def pick_outro():
            f = filedialog.askopenfilename(filetypes=[("Media files", "*.mp4 *.mov *.png *.jpg")])
            if f:
                self.outro_file = f
                lbl_outro.config(text=os.path.basename(f))

        frame_intro = ttk.Frame(win, padding="10")
        frame_intro.pack(fill=tk.X)
        tk.Button(frame_intro, text="Seleccionar Intro", command=pick_intro).pack(side=tk.LEFT, padx=5)
        lbl_intro = tk.Label(frame_intro, text=os.path.basename(self.intro_file) if self.intro_file else "Ninguno", fg="white", bg="#2e2e2e")
        lbl_intro.pack(side=tk.LEFT, expand=True, fill=tk.X)

        frame_outro = ttk.Frame(win, padding="10")
        frame_outro.pack(fill=tk.X)
        tk.Button(frame_outro, text="Seleccionar Outro", command=pick_outro).pack(side=tk.LEFT, padx=5)
        lbl_outro = tk.Label(frame_outro, text=os.path.basename(self.outro_file) if self.outro_file else "Ninguno", fg="white", bg="#2e2e2e")
        lbl_outro.pack(side=tk.LEFT, expand=True, fill=tk.X)

        # Optional: Add an OK/Close button
        ttk.Button(win, text="Cerrar", command=win.destroy).pack(pady=10)


    def export_video(self):
        if not self.image_list and not self.intro_file and not self.outro_file:
            messagebox.showerror("Error", "No hay contenido (imágenes, intro o outro) para crear el video.")
            return

        out_file = filedialog.asksaveasfilename(defaultextension='.mp4', filetypes=[("MP4 Video", "*.mp4")])
        if not out_file:
            return

        # Disable export button while processing (basic example)
        # self.btn_export.config(state=tk.DISABLED) # You'd need to store the button reference

        # Use a progress bar (more advanced, requires updating from thread)
        # For now, just indicate it's running (e.g., label)
        # self.status_label.config(text="Exportando...") # You'd need a status label

        # Launch the video creation in a separate thread
        threading.Thread(target=self._make_video, args=(out_file,), daemon=True).start() # daemon=True lets app exit even if thread is running

    def _make_video(self, out_file):
        clips = []
        video = None # Initialize video to None

        try:
            # Intro
            if self.intro_file:
                ext = os.path.splitext(self.intro_file)[1].lower()
                if ext in ['.mp4', '.mov']:
                    clips.append(VideoFileClip(self.intro_file))
                elif ext in ['.png', '.jpg', '.jpeg', '.bmp', '.gif']:
                    clips.append(ImageClip(self.intro_file).set_duration(3))
                # else: unsupported type is ignored
            # Images
            for img in self.image_list:
                dur = self.durations.get(img, 10)  # default 10s
                clips.append(ImageClip(img).set_duration(dur))
            # Outro
            if self.outro_file:
                ext = os.path.splitext(self.outro_file)[1].lower()
                if ext in ['.mp4', '.mov']:
                    clips.append(VideoFileClip(self.outro_file))
                elif ext in ['.png', '.jpg', '.jpeg', '.bmp', '.gif']:
                     clips.append(ImageClip(self.outro_file).set_duration(3))
                # else: unsupported type is ignored

            if not clips:
                 # This check is also done before threading, but good defensive programming
                 self.after(0, lambda: messagebox.showerror("Error", "No hay contenido para crear el video."))
                 return

            # Concatenate clips
            # Using method="chain" can be slightly faster/more memory efficient for simple concatenations
            video = concatenate_videoclips(clips, method="chain")

            # Audio
            if self.audio_file:
                audio = AudioFileClip(self.audio_file)
                # Corrected: using afx.audio_loop
                looped_audio = audio.fx(afx.audio_loop, duration=video.duration)
                video = video.set_audio(looped_audio)
                audio.close() # Close original audio clip
                looped_audio.close() # Close the looped audio clip

            # Write video file
            # Adding a progress callback is possible with write_videofile but requires more setup
            video.write_videofile(out_file, fps=24, codec='libx264')

            # Show success message on the main thread
            self.after(0, lambda: messagebox.showinfo("Listo", f"Video exportado en {out_file}"))

        except Exception as e:
             # Show error message on the main thread
             self.after(0, lambda: messagebox.showerror("Error de Exportación", str(e)))
        finally:
             # Ensure resources are released whether successful or not
             if video:
                try:
                   video.close()
                except Exception as e:
                   print(f"Error closing video clip: {e}")

             for clip in clips:
                 try:
                    # Check if clip is not already closed (e.g., intro/outro videos)
                    if hasattr(clip, 'reader') and clip.reader is not None:
                        clip.close()
                    # Note: ImageClip.close() is less critical but good practice
                    elif isinstance(clip, ImageClip):
                         pass # ImageClip doesn't have a formal close method releasing resources like VideoFileClip/AudioFileClip


                 except Exception as e:
                    print(f"Error closing clip: {e}")

             # Re-enable export button and clear status label (if implemented)
             # self.after(0, lambda: self.btn_export.config(state=tk.NORMAL))
             # self.after(0, lambda: self.status_label.config(text=""))


if __name__ == '__main__':
    # Add a basic exception hook for threads for easier debugging
    def show_thread_exception(exc_type, exc_value, exc_traceback):
        import traceback
        error_message = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        print("Unhandled exception in thread:", error_message)
        # Optionally show a messagebox on the main thread
        # root = tk.Tk() # This is just an example, you need the actual root window instance
        # root.after(0, lambda: messagebox.showerror("Error en Hilo", "Ha ocurrido un error inesperado en un hilo:\n" + error_message))
        # root.destroy()

    # This requires customizing if you want it to show in the Tkinter GUI
    # threading.excepthook = show_thread_exception # Not directly supported like sys.excepthook

    app = ImageVideoGUI()
    app.mainloop()
