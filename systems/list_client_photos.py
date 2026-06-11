"""
Geeft de beschikbare foto's in een geconfigureerde foto-map terug, zodat de
gebruiker er in het dashboard visueel een kan kiezen voor de social-afbeelding.
"""

import os

PHOTO_EXTENSIONS = (".jpg", ".jpeg", ".png")


def list_photos(folder_path):
    """Geeft een gesorteerde lijst van volledige paden naar afbeeldingen in folder_path.

    Geeft een lege lijst terug als het pad leeg is, niet bestaat of geen map is.
    """
    if not folder_path:
        return []
    if not os.path.isdir(folder_path):
        return []

    files = [
        f for f in os.listdir(folder_path)
        if f.lower().endswith(PHOTO_EXTENSIONS)
    ]
    return [os.path.join(folder_path, f) for f in sorted(files)]
