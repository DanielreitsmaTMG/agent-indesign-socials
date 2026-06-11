"""
Leest en schrijft de gedeelde Google Sheet van de Social Media Agent
("Posts_YYYY_WNN"-tabbladen en "Sheet1" met klantprofielen).

Gebruikt dezelfde credentials en kolomstructuur als
/Users/danielreitsma/Desktop/Marketing Agent Social Media/dashboard.py, zodat
afbeeldingen die hier gegenereerd worden direct zichtbaar zijn in de
"📅 Planning"-tab van het hoofddashboard.

Vereiste env-variabelen (in .env):
- GOOGLE_SHEETS_SPREADSHEET_ID
- GOOGLE_SERVICE_ACCOUNT_JSON
"""

import json

import gspread
from google.oauth2.service_account import Credentials

READ_SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
WRITE_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Kolommen K-Q in Posts_YYYY_WNN, zelfde als in het hoofddashboard
PLANNING_HEADERS = [
    "geplande_datum", "geplande_tijd", "afbeelding_url", "afbeelding_drive_id",
    "publicatie_status", "meta_post_id", "publicatie_log",
]
PLANNING_COL_LETTERS = {
    "geplande_datum": "K", "geplande_tijd": "L", "afbeelding_url": "M",
    "afbeelding_drive_id": "N", "publicatie_status": "O",
    "meta_post_id": "P", "publicatie_log": "Q",
}


def _read_client(sa_info_json):
    sa_info = json.loads(sa_info_json)
    creds = Credentials.from_service_account_info(sa_info, scopes=READ_SCOPES)
    return gspread.authorize(creds)


def _write_client(sa_info_json):
    sa_info = json.loads(sa_info_json)
    creds = Credentials.from_service_account_info(sa_info, scopes=WRITE_SCOPES)
    return gspread.authorize(creds)


def load_post_tabs(spreadsheet_id, sa_info_json):
    """Geeft alle tabbladen terug die beginnen met 'Posts_', nieuwste eerst."""
    gc = _read_client(sa_info_json)
    spreadsheet = gc.open_by_key(spreadsheet_id)
    return sorted(
        [ws.title for ws in spreadsheet.worksheets() if ws.title.startswith("Posts_")],
        reverse=True,
    )


def load_rows(tab_name, spreadsheet_id, sa_info_json):
    """Laadt alle rijen van een Posts_*-tab met afgeleide afbeeld-status.

    Geeft een lijst dicts terug, elk met de oorspronkelijke kolommen plus:
    - "_row_index": 1-based rijnummer in de sheet (incl. header), voor schrijven
    - "_beeld_status": "nodig" | "klaar" | "niet_relevant"
    """
    gc = _read_client(sa_info_json)
    worksheet = gc.open_by_key(spreadsheet_id).worksheet(tab_name)
    records = worksheet.get_all_records(default_blank="")

    rows = []
    for i, record in enumerate(records):
        record["_row_index"] = i + 2  # rij 1 = header
        status = str(record.get("status", "")).strip().lower()
        afbeelding_url = str(record.get("afbeelding_url", "")).strip()
        if afbeelding_url:
            record["_beeld_status"] = "klaar"
        elif status == "goedgekeurd":
            record["_beeld_status"] = "nodig"
        else:
            record["_beeld_status"] = "niet_relevant"
        rows.append(record)
    return rows


def _ensure_planning_columns(worksheet):
    """Vult de header-rij aan met de planningskolommen (K-Q) als die nog ontbreken.
    Oudere Posts_*-tabbladen hebben alleen kolom A-J. Zelfde logica als in het
    hoofddashboard, zodat beide projecten dezelfde kolomindeling gebruiken."""
    headers = worksheet.row_values(1)
    if len(headers) >= 17 and headers[10:17] == PLANNING_HEADERS:
        return
    headers = headers[:10]
    while len(headers) < 10:
        headers.append("")
    headers = headers + PLANNING_HEADERS
    worksheet.update(range_name="A1", values=[headers], value_input_option="RAW")
    worksheet.format("A1:Q1", {"textFormat": {"bold": True}})


def write_image_link(tab_name, row_index, url, drive_id, spreadsheet_id, sa_info_json):
    """Schrijft afbeelding_url (kolom M) en afbeelding_drive_id (kolom N) voor een rij."""
    gc = _write_client(sa_info_json)
    worksheet = gc.open_by_key(spreadsheet_id).worksheet(tab_name)
    _ensure_planning_columns(worksheet)
    worksheet.batch_update(
        [
            {"range": f"M{row_index}", "values": [[url]]},
            {"range": f"N{row_index}", "values": [[drive_id]]},
        ],
        value_input_option="RAW",
    )


def load_clients_basic(spreadsheet_id, sa_info_json):
    """Leest Sheet1 (klantprofielen) en geeft {klant_id: {bedrijfsnaam, google_doc_folder_id}} terug."""
    gc = _read_client(sa_info_json)
    sheet = gc.open_by_key(spreadsheet_id).sheet1
    rows = sheet.get_all_records(default_blank="")

    clients = {}
    for row in rows:
        klant_id = str(row.get("klant_id", "")).strip()
        if not klant_id:
            continue
        clients[klant_id] = {
            "bedrijfsnaam": row.get("bedrijfsnaam", ""),
            "google_doc_folder_id": str(row.get("google_doc_folder_id", "")).strip(),
        }
    return clients
