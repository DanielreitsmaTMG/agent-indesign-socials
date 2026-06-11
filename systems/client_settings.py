"""
Beheert de "Beeld_Config"-tab in de gedeelde Google Sheet: per klant het pad
naar de foto-map en het InDesign-template dat voor de Social Afbeelding Agent
gebruikt moet worden.

Tabblad "Beeld_Config" wordt automatisch aangemaakt als het nog niet bestaat
(zelfde patroon als de "Medewerkers"-tab in het hoofddashboard).

Kolommen: klant_id | foto_map | template_pad
"""

import json

import gspread
from google.oauth2.service_account import Credentials

WRITE_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

CONFIG_TAB_NAME = "Beeld_Config"
CONFIG_HEADERS = ["klant_id", "foto_map", "template_pad"]


def _write_client(sa_info_json):
    sa_info = json.loads(sa_info_json)
    creds = Credentials.from_service_account_info(sa_info, scopes=WRITE_SCOPES)
    return gspread.authorize(creds)


def load_client_settings(spreadsheet_id, sa_info_json):
    """Geeft {klant_id: {"foto_map": ..., "template_pad": ...}} terug."""
    gc = _write_client(sa_info_json)
    spreadsheet = gc.open_by_key(spreadsheet_id)
    try:
        worksheet = spreadsheet.worksheet(CONFIG_TAB_NAME)
    except gspread.WorksheetNotFound:
        return {}

    rows = worksheet.get_all_records(default_blank="")
    settings = {}
    for row in rows:
        klant_id = str(row.get("klant_id", "")).strip()
        if not klant_id:
            continue
        settings[klant_id] = {
            "foto_map": str(row.get("foto_map", "")).strip(),
            "template_pad": str(row.get("template_pad", "")).strip(),
        }
    return settings


def save_client_settings(spreadsheet_id, sa_info_json, settings_dict):
    """Schrijft {klant_id: {"foto_map": ..., "template_pad": ...}} naar de Beeld_Config-tab."""
    gc = _write_client(sa_info_json)
    spreadsheet = gc.open_by_key(spreadsheet_id)
    try:
        worksheet = spreadsheet.worksheet(CONFIG_TAB_NAME)
        worksheet.clear()
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=CONFIG_TAB_NAME, rows=100, cols=len(CONFIG_HEADERS))

    rows = [CONFIG_HEADERS]
    for klant_id, values in settings_dict.items():
        rows.append([klant_id, values.get("foto_map", ""), values.get("template_pad", "")])

    worksheet.update(rows, value_input_option="RAW")
    worksheet.format("A1:C1", {"textFormat": {"bold": True}})
