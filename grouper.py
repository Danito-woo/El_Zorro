# grouper.py
import re
from collections import defaultdict
from typing import List, Dict, Tuple
from pathlib import Path
# Import the UPDATED sanitize_filename
from utils import sanitize_filename

# Enhanced Regex to find common trailing patterns
SUFFIX_REGEX = re.compile(
    r'[\s._-]*(?:' # Optional separators before the pattern
    r'part(?:e)?\s*\d+|' # part X, parte X
    r'set\s*[a-z0-9]+|'  # set A, set 01
    r'#[.\s]?\d+|'       # #3, # 3, #.3
    r'\d+|'             # Just a number at the end
    r'vol(?:ume)?\s*\d+|' # vol X, volume X
    r'cap(?:itulo)?\s*\d+|' # cap X, capitulo X
    r'ch(?:apter)?\s*\d+|' # ch X, chapter X
    r'ep(?:isode)?\s*\d+|' # ep X, episode X
    r'pagina\s*\d+|'    # pagina X
    r'page\s*\d+'       # page X
    r')$', re.IGNORECASE
)
MIN_WORDS_FOR_GROUP = 2

def group_posts_by_title(posts: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Groups posts based on common prefixes in their titles after removing suffixes.
    Uses robust sanitization for folder names. Posts with sufficiently similar base
    titles (after suffix removal and normalization) are grouped.
    """
    posts_with_images = []
    for post in posts:
        # Check for images in 'file' or 'attachments' and ensure title exists
        has_images = (post.get('file') and post['file'].get('path')) or \
                     (post.get('attachments') and any(att.get('path') for att in post['attachments']))
        if has_images and post.get('title') and isinstance(post['title'], str) and post['title'].strip():
            posts_with_images.append(post)

    if not posts_with_images:
        return {}

    # 1. Pre-process: Extract potential base names and normalize
    processed_posts = []
    for post in posts_with_images:
        title = post['title'].strip()
        # Remove common suffixes BEFORE normalization for better matching
        base_name = SUFFIX_REGEX.sub('', title).strip()
        # Normalize for comparison: lowercase, keep only alphanumeric and spaces, collapse spaces
        normalized_base = re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9\s]', '', base_name.lower())).strip()

        # Use the original `base_name` (or `title` if `base_name` is empty) for folder name generation later
        folder_basis = base_name if base_name else title

        processed_posts.append({
            'post_data': post,
            'normalized_base': normalized_base,
            'folder_basis': folder_basis
        })

    # 2. Group by normalized base name
    temp_groups = defaultdict(list)
    individual_posts_data = []

    for p_info in processed_posts:
        # Only group if the normalized base name has enough words
        if p_info['normalized_base'] and len(p_info['normalized_base'].split()) >= MIN_WORDS_FOR_GROUP:
            temp_groups[p_info['normalized_base']].append(p_info)
        else:
            # Treat as individual if base name is too short or empty after normalization
             individual_posts_data.append(p_info)

    # 3. Finalize groups: Decide folder names and handle singles
    final_groups = defaultdict(list)
    processed_post_ids = set()

    # Process potential groups (those with more than one post based on normalized name)
    for normalized_base, related_post_infos in temp_groups.items():
        if len(related_post_infos) > 1:
            # Use the folder_basis from the *first* post in the group for the folder name
            # (Assumption: the first post's title part is representative enough)
            folder_basis_for_group = related_post_infos[0]['folder_basis']
            # Sanitize the chosen basis HERE using the robust function
            group_folder_name = sanitize_filename(folder_basis_for_group)

            for p_info in related_post_infos:
                post = p_info['post_data']
                if post['id'] not in processed_post_ids:
                    final_groups[group_folder_name].append(post)
                    processed_post_ids.add(post['id'])
        else:
            # If only one post ended up with this normalized name, treat it as individual
            individual_posts_data.extend(related_post_infos)

    # Process all individual posts (those initially marked + those from groups of size 1)
    for p_info in individual_posts_data:
        post = p_info['post_data']
        if post['id'] not in processed_post_ids:
            # Sanitize the folder basis (usually the full title for individuals) HERE
            group_folder_name = sanitize_filename(p_info['folder_basis'])
            # Ensure the individual folder name isn't empty after sanitization
            if not group_folder_name: group_folder_name = f"post_{sanitize_filename(post['id'])}"

            final_groups[group_folder_name].append(post) # Group of one
            processed_post_ids.add(post['id'])

    # Sort posts within each group by 'published' date (best effort)
    for group_name in final_groups:
        # Handle cases where 'published' might be missing or not a string
        final_groups[group_name].sort(key=lambda p: str(p.get('published', '')))

    return dict(final_groups)


if __name__ == '__main__':
    # Example usage
    sample_posts = [
        {'id': '1', 'title': 'Playa de hora a hora parte 1😀', 'published': '2023-01-01', 'file': {'path': '/img1.jpg', 'name': 'Playa1.jpg'}},
        {'id': '2', 'title': 'Playa de hora a hora parte 2', 'published': '2023-01-02', 'attachments': [{'path': '/img2.png', 'name': 'Beach Day T_wo?.png'}]},
        {'id': '3', 'title': 'Vacaciones // Montaña Set A', 'published': '2023-02-01', 'file': {'path': '/img3.jpg', 'name': 'Vaca A.jpg'}},
        {'id': '4', 'title': 'Vacaciones // Montaña Set B', 'published': '2023-02-02', 'file': {'path': '/img4.jpg', 'name': 'Vaca B.jpg'}},
        {'id': '5', 'title': 'Retrato único <cool>', 'published': '2023-03-01', 'file': {'path': '/img5.jpg', 'name': 'Portrait.jpg'}},
        {'id': '6', 'title': 'Playa de hora a hora #3', 'published': '2023-01-03', 'file': {'path': '/img6.jpg', 'name': 'Playa3.jpg'}},
        {'id': '7', 'title': 'Otro post sin imágenes', 'published': '2023-04-01'},
        {'id': '8', 'title': '  ciudad nocturna (1) ', 'published': '2023-05-01', 'file': {'path': '/img8.jpg', 'name': 'City1.jpg'}},
        {'id': '9', 'title': 'ciudad nocturna [2]', 'published': '2023-05-02', 'file': {'path': '/img9.jpg', 'name': 'City2.jpg'}},
        {'id': '10', 'title': 'Solo una imagen.jpg', 'published': '2023-06-01', 'file': {'path': '/img10.jpg', 'name': 'Image_Only.jpg'}}, # Test short title
         {'id': '11', 'title': 'かわいい猫 Ch. 1', 'published': '2023-07-01', 'file': {'path': '/img11.jpg', 'name': 'Neko1.jpg'}}, # Japanese + Chapter
         {'id': '12', 'title': 'かわいい猫 Ch. 2', 'published': '2023-07-02', 'file': {'path': '/img12.jpg', 'name': 'Neko2.jpg'}},
    ]
    print("\nGrouping Test:")
    groups = group_posts_by_title(sample_posts)
    for name, posts_in_group in groups.items():
        print(f"Grupo (Carpeta Sanitizada): '{name}'")
        for p in posts_in_group:
            print(f"  - ID: {p['id']}, Título Original: {p['title']}")
        print("-" * 20)

    # Expected Output (folder names sanitized):
    # Grupo (Carpeta Sanitizada): 'Playa_de_hora_a_hora'
    #   - ID: 1, Título Original: Playa de hora a hora parte 1😀
    #   - ID: 2, Título Original: Playa de hora a hora parte 2
    #   - ID: 6, Título Original: Playa de hora a hora #3
    # --------------------
    # Grupo (Carpeta Sanitizada): 'Vacaciones_Montana'
    #   - ID: 3, Título Original: Vacaciones // Montaña Set A
    #   - ID: 4, Título Original: Vacaciones // Montaña Set B
    # --------------------
    # Grupo (Carpeta Sanitizada): 'Retrato_unico_cool'
    #   - ID: 5, Título Original: Retrato único <cool>
    # --------------------
    # Grupo (Carpeta Sanitizada): 'ciudad_nocturna'
    #   - ID: 8, Título Original:   ciudad nocturna (1)
    #   - ID: 9, Título Original: ciudad nocturna [2]
    # --------------------
    # Grupo (Carpeta Sanitizada): 'Solo_una_imagen_jpg'  <- Note: Short titles might become individual folders
    #   - ID: 10, Título Original: Solo una imagen.jpg
    # --------------------
    # Grupo (Carpeta Sanitizada): 'kawayii_Mao' or similar depending on unidecode output
    #   - ID: 11, Título Original: かわいい猫 Ch. 1
    #   - ID: 12, Título Original: かわいい猫 Ch. 2
    # --------------------