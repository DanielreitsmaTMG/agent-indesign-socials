"""
Lokale worker voor de Social Afbeelding Agent.

Handmatig uit te voeren wanneer nodig (geen achtergronddienst):

    python systems/run_worker.py

Doet twee dingen:
1. Werkt de "Foto_Index"-tab bij: scant per klant de geconfigureerde
   `foto_map` (Beeld_Config) en publiceert de gevonden bestandsnamen, zodat
   het cloud-dashboard een foto-keuzelijst kan tonen.
2. Verwerkt openstaande taken uit "Genereer_Taken" (status "wachtend"):
   genereert de afbeelding via InDesign, uploadt naar Drive en koppelt het
   resultaat terug naar de Posts_*-tab (kolom M/N).

Vereist in .env:
    GOOGLE_SHEETS_SPREADSHEET_ID
    GOOGLE_SERVICE_ACCOUNT_JSON
    INDESIGN_APP_NAME
"""

import json
import os

from dotenv import load_dotenv

from systems import client_settings, drive_upload, generate_social_image, list_client_photos, sheet_queue, task_queue

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_DIR, "output")


def _credentials():
    spreadsheet_id = os.environ["GOOGLE_SHEETS_SPREADSHEET_ID"]
    sa_json = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    json.loads(sa_json)  # validatie
    return spreadsheet_id, sa_json


def update_photo_index(spreadsheet_id, sa_json):
    settings = client_settings.load_client_settings(spreadsheet_id, sa_json)

    index = {}
    for klant_id, values in settings.items():
        foto_map = values.get("foto_map", "")
        if not foto_map:
            continue
        photos = list_client_photos.list_photos(foto_map)
        index[klant_id] = [os.path.basename(p) for p in photos]

    task_queue.write_photo_index(spreadsheet_id, sa_json, index)

    totaal = sum(len(v) for v in index.values())
    print(f"Foto_Index bijgewerkt: {totaal} foto('s) over {len(index)} klant(en).")
    return settings


def process_tasks(spreadsheet_id, sa_json, settings):
    tasks = task_queue.load_tasks(spreadsheet_id, sa_json)
    wachtend = [t for t in tasks if str(t.get("status", "")).strip() == task_queue.STATUS_WACHTEND]

    if not wachtend:
        print("Geen openstaande taken.")
        return

    verwerkt = 0
    gefaald = 0

    for task in wachtend:
        task_row = task["_row_index"]
        tab_name = task.get("tab_name", "")
        row_index = task.get("row_index")
        klant_id = task.get("klant_id", "")
        beeldtitel = task.get("beeldtitel", "")
        gekozen_foto = task.get("gekozen_foto", "")

        print(f"Verwerk taak: {tab_name} rij {row_index} ({klant_id}) — {gekozen_foto}")
        task_queue.update_task_status(spreadsheet_id, sa_json, task_row, task_queue.STATUS_BEZIG)

        try:
            client_config = settings.get(klant_id, {})
            foto_map = client_config.get("foto_map", "")
            template_pad = client_config.get("template_pad", "")

            if not foto_map or not template_pad:
                raise RuntimeError(f"foto_map/template_pad niet ingesteld voor klant {klant_id}")

            foto_path = os.path.join(foto_map, gekozen_foto)
            if not os.path.exists(foto_path):
                raise RuntimeError(f"Foto niet gevonden: {foto_path}")
            if not os.path.exists(template_pad):
                raise RuntimeError(f"Template niet gevonden: {template_pad}")

            os.makedirs(OUTPUT_DIR, exist_ok=True)
            output_path = os.path.join(OUTPUT_DIR, f"{tab_name}_{row_index}.jpg")

            result = generate_social_image.generate(template_pad, foto_path, beeldtitel, output_path)
            if not result.get("success"):
                raise RuntimeError(f"InDesign-generatie mislukt: {result.get('error')}")

            log = "overflow: titel past niet volledig" if result.get("overflow") else ""

            clients_basic = sheet_queue.load_clients_basic(spreadsheet_id, sa_json)
            folder_id = clients_basic.get(klant_id, {}).get("google_doc_folder_id", "")
            if not folder_id:
                raise RuntimeError(f"Geen google_doc_folder_id voor klant {klant_id}")

            sa_info = json.loads(sa_json)
            upload_result = drive_upload.upload_image_file(sa_info, folder_id, output_path)
            sheet_queue.write_image_link(
                tab_name, row_index, upload_result["url"], upload_result["id"],
                spreadsheet_id, sa_json,
            )

            task_queue.update_task_status(spreadsheet_id, sa_json, task_row, task_queue.STATUS_KLAAR, log)
            verwerkt += 1
            print(f"  -> klaar{' (' + log + ')' if log else ''}")

        except Exception as e:
            task_queue.update_task_status(spreadsheet_id, sa_json, task_row, task_queue.STATUS_FOUT, str(e))
            gefaald += 1
            print(f"  -> fout: {e}")

    print(f"Taken verwerkt: {verwerkt}, gefaald: {gefaald}.")


def main():
    load_dotenv()
    spreadsheet_id, sa_json = _credentials()

    settings = update_photo_index(spreadsheet_id, sa_json)
    process_tasks(spreadsheet_id, sa_json, settings)


if __name__ == "__main__":
    main()
