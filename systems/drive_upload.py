"""
Helper voor het uploaden van gegenereerde social-afbeeldingen naar Google Drive,
zodat ze direct in de "📅 Planning"-tab van het hoofddashboard
(Marketing Agent Social Media) verschijnen.

Afbeeldingen worden geplaatst in een submap "Planning" binnen de Drive-map van
de klant (`google_doc_folder_id`) en krijgen een publieke leesrechten-permissie,
zodat de Meta Graph API de afbeelding kan ophalen bij het publiceren.

Dit is een aangepaste kopie van
/Users/danielreitsma/Desktop/Marketing Agent Social Media/systems/drive_upload.py
(bewust gedupliceerd: elk BOS-project heeft zijn eigen systems/ zonder
cross-project import-afhankelijkheden).

Vereiste scope: https://www.googleapis.com/auth/drive
"""

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/drive"]

PLANNING_SUBFOLDER_NAME = "Planning"


def _drive_service(sa_info: dict):
    creds = Credentials.from_service_account_info(sa_info, scopes=SCOPES)
    return build("drive", "v3", credentials=creds)


def _find_or_create_subfolder(drive_service, parent_folder_id: str, name: str) -> str:
    """Geeft de map-ID van `name` binnen `parent_folder_id` terug, en maakt deze aan indien nodig."""
    query = (
        f"'{parent_folder_id}' in parents and name = '{name}' "
        "and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    )
    result = drive_service.files().list(q=query, fields="files(id, name)").execute()
    files = result.get("files", [])
    if files:
        return files[0]["id"]

    folder = drive_service.files().create(
        body={
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_folder_id],
        },
        fields="id",
    ).execute()
    return folder["id"]


def upload_image_file(sa_info: dict, parent_folder_id: str, file_path: str, mime_type: str = "image/jpeg") -> dict:
    """Uploadt een lokaal bestand naar de Planning-submap van de klant en maakt deze publiek leesbaar.

    Geeft {"id": <drive_file_id>, "url": <publieke directe URL>} terug.
    """
    drive_service = _drive_service(sa_info)
    folder_id = _find_or_create_subfolder(drive_service, parent_folder_id, PLANNING_SUBFOLDER_NAME)

    media = MediaFileUpload(file_path, mimetype=mime_type, resumable=False)
    file = drive_service.files().create(
        body={"name": file_path.split("/")[-1], "parents": [folder_id]},
        media_body=media,
        fields="id",
    ).execute()
    file_id = file["id"]

    drive_service.permissions().create(
        fileId=file_id,
        body={"role": "reader", "type": "anyone"},
        fields="id",
    ).execute()

    return {"id": file_id, "url": f"https://drive.google.com/uc?export=view&id={file_id}"}
