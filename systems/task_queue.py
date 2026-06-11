"""
Beheert de "Foto_Index"- en "Genereer_Taken"-tabbladen in de gedeelde Google
Sheet. Dit is de communicatielaag tussen het cloud-dashboard (`dashboard.py`)
en de lokale worker (`systems/run_worker.py`):

- "Foto_Index": door de lokale worker geschreven, lijst van beschikbare
  foto-bestandsnamen per klant (gescand uit de geconfigureerde `foto_map`).
  Het cloud-dashboard heeft geen toegang tot de lokale schijf en gebruikt deze
  tab om een foto-keuzelijst te tonen.
- "Genereer_Taken": takenlijst. Het cloud-dashboard zet rijen op `wachtend`
  wanneer een gebruiker een afbeelding aanvraagt; de lokale worker verwerkt
  deze (`bezig` → `klaar`/`fout`) en koppelt het resultaat terug naar de
  Posts_*-tab via `sheet_queue.write_image_link()`.

Beide tabbladen worden automatisch aangemaakt (met header-rij) als ze nog niet
bestaan, zelfde patroon als `client_settings.py`.
"""

import json
from datetime import datetime, timezone

import gspread
from google.oauth2.service_account import Credentials

READ_SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
WRITE_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

FOTO_INDEX_TAB_NAME = "Foto_Index"
FOTO_INDEX_HEADERS = ["klant_id", "bestandsnaam"]

TASK_TAB_NAME = "Genereer_Taken"
TASK_HEADERS = [
    "tab_name", "row_index", "klant_id", "beeldtitel", "gekozen_foto",
    "status", "log", "aangemaakt_op", "bijgewerkt_op",
]

STATUS_WACHTEND = "wachtend"
STATUS_BEZIG = "bezig"
STATUS_KLAAR = "klaar"
STATUS_FOUT = "fout"


def _read_client(sa_info_json):
    sa_info = json.loads(sa_info_json)
    creds = Credentials.from_service_account_info(sa_info, scopes=READ_SCOPES)
    return gspread.authorize(creds)


def _write_client(sa_info_json):
    sa_info = json.loads(sa_info_json)
    creds = Credentials.from_service_account_info(sa_info, scopes=WRITE_SCOPES)
    return gspread.authorize(creds)


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── Foto_Index ──────────────────────────────────────────────────────────────

def load_photo_index(spreadsheet_id, sa_info_json):
    """Geeft {klant_id: [bestandsnaam, ...]} terug."""
    gc = _read_client(sa_info_json)
    spreadsheet = gc.open_by_key(spreadsheet_id)
    try:
        worksheet = spreadsheet.worksheet(FOTO_INDEX_TAB_NAME)
    except gspread.WorksheetNotFound:
        return {}

    rows = worksheet.get_all_records(default_blank="")
    index = {}
    for row in rows:
        klant_id = str(row.get("klant_id", "")).strip()
        bestandsnaam = str(row.get("bestandsnaam", "")).strip()
        if not klant_id or not bestandsnaam:
            continue
        index.setdefault(klant_id, []).append(bestandsnaam)
    return index


def write_photo_index(spreadsheet_id, sa_info_json, index_dict):
    """Schrijft {klant_id: [bestandsnaam, ...]} naar de Foto_Index-tab (clear + herschrijven)."""
    gc = _write_client(sa_info_json)
    spreadsheet = gc.open_by_key(spreadsheet_id)
    try:
        worksheet = spreadsheet.worksheet(FOTO_INDEX_TAB_NAME)
        worksheet.clear()
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(
            title=FOTO_INDEX_TAB_NAME, rows=1000, cols=len(FOTO_INDEX_HEADERS),
        )

    rows = [FOTO_INDEX_HEADERS]
    for klant_id, bestandsnamen in index_dict.items():
        for naam in bestandsnamen:
            rows.append([klant_id, naam])

    worksheet.update(rows, value_input_option="RAW")
    worksheet.format("A1:B1", {"textFormat": {"bold": True}})


# ── Genereer_Taken ────────────────────────────────────────────────────────────

def _ensure_task_worksheet(spreadsheet):
    try:
        worksheet = spreadsheet.worksheet(TASK_TAB_NAME)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(
            title=TASK_TAB_NAME, rows=1000, cols=len(TASK_HEADERS),
        )
        worksheet.update([TASK_HEADERS], value_input_option="RAW")
        worksheet.format("A1:I1", {"textFormat": {"bold": True}})
    return worksheet


def load_tasks(spreadsheet_id, sa_info_json):
    """Geeft alle taken terug als list of dicts, elk met "_row_index" (1-based, incl. header)."""
    gc = _read_client(sa_info_json)
    spreadsheet = gc.open_by_key(spreadsheet_id)
    try:
        worksheet = spreadsheet.worksheet(TASK_TAB_NAME)
    except gspread.WorksheetNotFound:
        return []

    records = worksheet.get_all_records(default_blank="")
    tasks = []
    for i, record in enumerate(records):
        record["_row_index"] = i + 2  # rij 1 = header
        tasks.append(record)
    return tasks


def upsert_task(spreadsheet_id, sa_info_json, tab_name, row_index, klant_id, beeldtitel, gekozen_foto):
    """Maakt een nieuwe taak met status "wachtend" aan, of overschrijft een
    bestaande taak voor dezelfde tab_name+row_index (bv. om opnieuw te proberen
    na een "fout")."""
    gc = _write_client(sa_info_json)
    spreadsheet = gc.open_by_key(spreadsheet_id)
    worksheet = _ensure_task_worksheet(spreadsheet)

    records = worksheet.get_all_records(default_blank="")
    now = _now_iso()
    new_row = [
        tab_name, row_index, klant_id, beeldtitel, gekozen_foto,
        STATUS_WACHTEND, "", now, now,
    ]

    for i, record in enumerate(records):
        if str(record.get("tab_name", "")) == str(tab_name) and str(record.get("row_index", "")) == str(row_index):
            sheet_row = i + 2
            worksheet.update(
                range_name=f"A{sheet_row}:I{sheet_row}",
                values=[new_row],
                value_input_option="RAW",
            )
            return

    worksheet.append_row(new_row, value_input_option="RAW")


def update_task_status(spreadsheet_id, sa_info_json, task_row_index, status, log=""):
    """Schrijft status (F), log (G) en bijgewerkt_op (I) voor een specifieke taakrij."""
    gc = _write_client(sa_info_json)
    spreadsheet = gc.open_by_key(spreadsheet_id)
    worksheet = _ensure_task_worksheet(spreadsheet)
    worksheet.batch_update(
        [
            {"range": f"F{task_row_index}", "values": [[status]]},
            {"range": f"G{task_row_index}", "values": [[log]]},
            {"range": f"I{task_row_index}", "values": [[_now_iso()]]},
        ],
        value_input_option="RAW",
    )
