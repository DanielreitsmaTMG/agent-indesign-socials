# Agent InDesign Socials

Dit project gebruikt het **BOS-framework** (Blueprints, Orchestrators, Systems) om workflows
rondom InDesign en social media content te automatiseren.

## Structuur

```
project/
├── blueprints/          # Markdown SOP's en instructies
│   ├── social_image_generation.md
│   └── indesign_template_setup.md
├── systems/              # Python-scripts en InDesign-scripts
│   ├── sheet_queue.py
│   ├── client_settings.py
│   ├── task_queue.py
│   ├── list_client_photos.py
│   ├── drive_upload.py
│   ├── generate_social_image.py
│   ├── run_worker.py
│   ├── fill_template.jsx
│   └── smart_crop_photo.py
├── dashboard.py          # Streamlit-dashboard (cloud, team-toegang)
├── templates/            # InDesign .indd/.indt templates
├── assets/photos/        # Voorraad-/huisstijlfoto's
├── output/               # Gegenereerde afbeeldingen (intermediates)
├── requirements.txt      # Python-dependencies
├── .env                  # API-sleutels en credentials (niet committen)
├── CLAUDE.md             # Agent-instructies en projectcontext
└── README.md             # Dit bestand
```

## Workflow

1. Beschrijf een taak.
2. De agent zoekt of leest de relevante blueprint in `blueprints/`.
3. De agent voert de bijbehorende scripts uit `systems/` uit.
4. Resultaten en deliverables gaan naar de afgesproken cloudservice.
5. Blueprints worden bijgewerkt op basis van geleerde lessen.

## Social Afbeelding Agent

Automatiseert het genereren van social media afbeeldingen via InDesign voor
goedgekeurde posts uit de Social Media Agent. Dit project haakt aan op de
**bestaande** Google Sheet (`Posts_YYYY_WNN`-tabbladen) van
`Marketing Agent Social Media`, zodat gegenereerde afbeeldingen direct in de
"📅 Planning"-tab van dat dashboard verschijnen — zonder die codebase te
wijzigen.

De app bestaat uit twee delen die via de gedeelde Sheet communiceren (zie
[`blueprints/social_image_generation.md`](blueprints/social_image_generation.md)
voor de volledige workflow):

- **`dashboard.py`** — Streamlit-app, gedeployed op Streamlit Community Cloud
  voor het hele team. Toont voortgang, laat een foto kiezen en een
  generatie aanvragen, en beheert per-klant instellingen (`foto_map`,
  `template_pad`).
- **`systems/run_worker.py`** — lokale worker, **handmatig** gestart op een
  Mac met Adobe InDesign. Indexeert beschikbare foto's en verwerkt
  aanvragen: genereert de afbeelding, uploadt naar Drive en koppelt terug
  naar de Planning-tab.

Zie [`blueprints/indesign_template_setup.md`](blueprints/indesign_template_setup.md)
voor het opzetten van een InDesign-template per klant.

### Cloud-dashboard (team)

```bash
pip install -r requirements.txt
streamlit run dashboard.py
```

Lokaal draait dit op `.env`-credentials. Voor de Streamlit Cloud-deploy
configureer je dezelfde waarden via Streamlit secrets
(`GOOGLE_SHEETS_SPREADSHEET_ID`, `GOOGLE_SERVICE_ACCOUNT_JSON` — of, als het
JSON-blob te groot is voor één secret, base64-encoded via
`GOOGLE_SERVICE_ACCOUNT_B64` of opgesplitst in `GOOGLE_SA_B64_1`+`GOOGLE_SA_B64_2`),
plus `APP_PASSWORD`.

De GitHub-repo is **publiek** (geen credentials erin, alleen code), dus het
dashboard zit achter een eenvoudig wachtwoordscherm
(`APP_PASSWORD` in `.env` resp. Streamlit secrets — kies hetzelfde wachtwoord
op beide plekken en deel het alleen met het team).

### Lokale worker (verwerkt taken)

```bash
python systems/run_worker.py
```

Vereist een lokaal geinstalleerde Adobe InDesign (de afbeelding wordt via
`osascript` aangestuurd) en een ingevulde `.env`. Draai dit handmatig wanneer
er nieuwe aanvragen klaarstaan in het cloud-dashboard, of wanneer de
foto-mappen gewijzigd zijn.

### Nog te doen voordat dit volledig werkt

- [ ] `.env` invullen: `GOOGLE_SHEETS_SPREADSHEET_ID` en
      `GOOGLE_SERVICE_ACCOUNT_JSON` kopiëren uit
      `Marketing Agent Social Media/.env` (zelfde Sheet/Drive-koppeling)
- [ ] In het dashboard, tabblad ⚙️ Instellingen: per klant `foto_map` en
      `template_pad` instellen (begin met Artena: `assets/photos/` en
      `templates/social_post_artena.indd`) — dit zijn lokale paden die de
      worker gebruikt
- [ ] Voor overige klanten: InDesign-template (`.indd`/`.indt`) maken met
      script labels `TITLE_TEXT` en `PHOTO_FRAME`, opslaan in `templates/`
- [ ] Project naar een git-repo + GitHub-remote brengen en deployen op
      Streamlit Community Cloud, met de Sheet-credentials als secrets

## Status

Eerste end-to-end test geslaagd voor klant Artena (titel gecentreerd in het
oranje vlak, volledige foto proportioneel zichtbaar zonder bijsnijden,
`output/test_artena.jpg` / `output/test_artena2.jpg`). De app is opgesplitst
in een cloud-dashboard (`dashboard.py`) en een lokale worker
(`systems/run_worker.py`) die via de `Foto_Index`- en `Genereer_Taken`-tabs
communiceren — nog niet getest met live Sheet-credentials, en nog niet
gedeployed op Streamlit Cloud.
