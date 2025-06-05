# utils.py
import re
import os
from unidecode import unidecode # ¡Importante! Asegúrate de instalar: pip install Unidecode
from urllib.parse import urlparse

def sanitize_filename(name: str, replace_space_with='_') -> str:
    """
    Sanitizes a string to be used as a safe filename or directory name.

    - Transliterates Unicode characters (accents, emojis, symbols) to ASCII approximations.
    - Removes OS-invalid characters: \\ / : * ? " < > |
    - Removes control characters (ASCII 0-31, 127).
    - Replaces sequences of whitespace with a single specified character (default '_').
    - Removes leading/trailing spaces, dots, and the replacement character.
    - Ensures the name is not empty or just dots, returning 'untitled' if so.
    - Limits filename length (optional, uncomment if needed).
    """
    if not isinstance(name, str):
        name = str(name) # Ensure input is a string

    # 1. Transliterate Unicode to ASCII approximation using unidecode
    try:
        # Handle potential TypeError if input is unexpected after str() conversion
        sanitized = unidecode(name)
    except Exception as e:
        print(f"Warning: unidecode failed for input '{name}'. Error: {e}. Falling back to basic ASCII filtering.")
        # Fallback: Keep only basic printable ASCII
        sanitized = "".join(c for c in name if 32 <= ord(c) < 127)


    # 2. Remove invalid filename characters and control characters
    #    Includes \ / : * ? " < > | and ASCII control chars 0-31, 127
    sanitized = re.sub(r'[\\/*?:"<>|\x00-\x1f\x7f]', '', sanitized)

    # 3. Replace whitespace sequences (space, tab, newline etc.) with the replacement character
    if replace_space_with is not None: # Allow empty string to just remove spaces
        sanitized = re.sub(r'\s+', replace_space_with, sanitized)
    # If replace_space_with is None, spaces remain as is (unless removed by other rules)

    # 4. Remove leading/trailing unwanted characters (dots, spaces, and the replacement char itself)
    #    This prevents names like "__folder__" or ".folder."
    strip_chars = ". " + (replace_space_with if replace_space_with else '')
    sanitized = sanitized.strip(strip_chars)

    # 5. Prevent names that are just dots (Windows compatibility) or empty
    if not sanitized or all(c == '.' for c in sanitized):
        return "untitled"

    # 6. Limit length (Optional - uncomment and adjust max_len if needed)
    # max_len = 150 # Example max length for a filename component
    # if len(sanitized) > max_len:
    #     sanitized = sanitized[:max_len]
    #     # Re-strip after cutting to ensure it doesn't end with a partial sequence or unwanted char
    #     sanitized = sanitized.strip(strip_chars)
    #     # Check again if it became empty after stripping
    #     if not sanitized or all(c == '.' for c in sanitized):
    #         return "untitled"

    return sanitized

def ensure_dir(path: str):
    """Ensures a directory exists, creating it if necessary."""
    # Use pathlib for better path handling
    from pathlib import Path
    Path(path).mkdir(parents=True, exist_ok=True)

def get_base_url(api_url="https://kemono.su/api/v1/"):
    """Extracts the base domain URL from the API URL."""
    parsed = urlparse(api_url)
    return f"{parsed.scheme}://{parsed.netloc}"

if __name__ == '__main__':
    # Test sanitization
    test_cases = [
        "Test / File * Name ?.png",
        "  Año Nuevo en Japón  😀.jpg", # Accents, emoji, spaces
        "ファイル名 example.gif",       # Japanese chars
        "Folder: Subfolder",           # Invalid char ":"
        "Post con \t tab \n newline.txt", # Control/whitespace chars
        "...",                         # Just dots
        "",                            # Empty
        " Leading and trailing spaces ",
        "My_File.....",                # Trailing dots
        "----MyFile----",              # Leading/trailing replacement char (if _)
        None,                          # Test non-string input
        12345,                         # Test numeric input
        "Keep Spaces Okay .png"        # Test keeping spaces
    ]
    print("Sanitization Tests (replace space with '_'):")
    for case in test_cases:
        print(f"Original: {repr(case)} -> Sanitized: '{sanitize_filename(case)}'")

    print("\nSanitization Tests (replace space with ''):")
    for case in test_cases:
        print(f"Original: {repr(case)} -> Sanitized: '{sanitize_filename(case, replace_space_with='')}'")

    print("\nSanitization Tests (replace space with None - keep spaces):")
    for case in test_cases:
        print(f"Original: {repr(case)} -> Sanitized: '{sanitize_filename(case, replace_space_with=None)}'")


    print(f"\nBase URL: {get_base_url()}")
    print("\nEnsuring directory './test_dir/sub_dir'")
    ensure_dir('./test_dir/sub_dir')
    print("Directory should exist now.")
    # Clean up test directory
    try:
        os.rmdir('./test_dir/sub_dir')
        os.rmdir('./test_dir')
    except OSError:
        pass # Ignore if already removed or not empty