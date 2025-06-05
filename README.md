# 🦊 El_Zorro

*The only downloader that wears a mask (and sometimes a cape).*

## What is this?
El_Zorro is an automatic, full user library downloader for [kemono.su](https://kemono.su/). It slices! It dices! It downloads entire creator libraries with the elegance of a fox and the efficiency of a caffeinated squirrel. It even comes with a GUI, a web gallery, and more tools than a Swiss Army knife at a camping convention.

## Quickstart
1. Clone this repo. (No, really, it's safe. We checked for secrets. Twice.)
2. Install the requirements (see below).
3. Run `main.py` for the GUI, or explore the other scripts for bonus features.
4. Download, organize, and enjoy your content like a true digital vigilante.

## File-by-File Breakdown (with 100% more jokes)

### `main.py`
The main entry point. Launches the PyQt6 GUI. If this file were a fox, it would be the one opening the henhouse door.

### `gui.py`
The PyQt6 GUI logic. Handles windows, buttons, and all the shiny things you click. Home of the `MainWindow` class. If you like clicking things, this is your jam.

### `worker.py`
The download engine. Runs in a separate thread so your GUI doesn't freeze like a deer in headlights. Handles concurrent downloads, progress updates, and manifest writing. Main class: `DownloadWorker` (not to be confused with actual foxes working).

### `api_client.py`
Talks to the kemono.su API. Fetches posts, downloads images, and retries like a stubborn fox. Main class: `KemonoAPI`.

### `grouper.py`
Groups posts by title, so your downloads are organized and not just a pile of digital spaghetti. Main function: `group_posts_by_title`.

### `fusionar.py`
Merges multiple groups into one, with a summary at the end. Think of it as the fox's way of tidying up the henhouse after a wild night.

### `folder_to_video.py`
Turns a folder of images into a video, complete with intros, outros, and music. Because sometimes you want your downloads to move.

### `censurador_manual.py`
A Tkinter tool for manually pixelating images. For when you need to hide the evidence (or just some pixels).

### `web_gallery.py`
A Flask-powered web gallery for browsing your downloaded content. Features group management, merging, reordering, and more. It's like a fox's den, but with more HTML.

### `utils.py`
Helper functions for filename sanitization, directory creation, and more. The unsung heroes of the codebase.

### `styles.py`
Dark mode CSS for the PyQt6 GUI. Because even foxes prefer to work at night.

### `.gitignore`
Keeps your secrets (and your `__pycache__`) out of git. Also ignores downloads, temp files, and IDE configs. Foxes are tidy.

### `LICENSE`
Unlicense. Do whatever you want. Seriously. The fox doesn't care.

## FAQ
**Q: Is it safe to upload this to GitHub?**
A: Yes! We checked for API keys, secrets, and embarrassing diary entries. All clear.

**Q: Why "El Zorro"?**
A: Because "Downloader McDownloadface" was taken.

## Contributing
Pull requests welcome! Bonus points for fox puns.

## Disclaimer
This project is for educational purposes only. Use responsibly, and don't blame the fox if you get in trouble.

---

🦊 *Happy downloading!*
