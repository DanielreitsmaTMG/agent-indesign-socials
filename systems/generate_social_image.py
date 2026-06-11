"""
Vult een InDesign template met een titel en foto en exporteert als JPG.

De foto wordt volledig (alle pixels) getoond, proportioneel geschaald binnen het
PHOTO_FRAME en gecentreerd - er wordt niet bijgesneden.

Roept systems/fill_template.jsx aan via osascript op een lokaal geinstalleerde InDesign-app.

Vereiste env-variabele (in .env):
- INDESIGN_APP_NAME: exacte naam van de InDesign-applicatie, bijv. "Adobe InDesign 2026"

Gebruik:
    python systems/generate_social_image.py <template_path> <photo_path> "<titel>" <output_path>
"""

import json
import os
import subprocess
import sys

from dotenv import load_dotenv

SYSTEMS_DIR = os.path.dirname(os.path.abspath(__file__))
JOB_PATH = os.path.join(SYSTEMS_DIR, "_job.json")
RESULT_PATH = os.path.join(SYSTEMS_DIR, "_job_result.json")
JSX_PATH = os.path.join(SYSTEMS_DIR, "fill_template.jsx")


def generate(template_path, photo_path, title, output_path):
    load_dotenv()
    app_name = os.environ["INDESIGN_APP_NAME"]

    job = {
        "template_path": os.path.abspath(template_path),
        "photo_path": os.path.abspath(photo_path),
        "title": title,
        "output_path": os.path.abspath(output_path),
    }

    if os.path.exists(RESULT_PATH):
        os.remove(RESULT_PATH)

    with open(JOB_PATH, "w") as f:
        json.dump(job, f)

    script = (
        f'tell application "{app_name}" to do script "{JSX_PATH}" '
        f'language javascript'
    )
    proc = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
    )

    if proc.returncode != 0:
        return {"success": False, "error": proc.stderr.strip() or proc.stdout.strip()}

    if not os.path.exists(RESULT_PATH):
        return {"success": False, "error": "Geen resultaatbestand geschreven door InDesign"}

    with open(RESULT_PATH) as f:
        result = json.load(f)

    return result


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print(__doc__)
        sys.exit(1)

    template_path, photo_path, title, output_path = sys.argv[1:5]
    result = generate(template_path, photo_path, title, output_path)
    print(json.dumps(result, indent=2))

    if not result.get("success"):
        sys.exit(1)
