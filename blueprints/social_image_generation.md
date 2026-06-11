# Blueprint: Social Afbeelding Genereren

## Doel

Voor elke goedgekeurde post in de Google Sheet van de Social Media Agent
(`Posts_YYYY_WNN`-tabbladen) een social media afbeelding genereren via
InDesign, met de aangeleverde `beeldtitel` en een door de gebruiker gekozen
foto — en deze afbeelding automatisch koppelen aan diezelfde rij, zodat het
hoofddashboard (Marketing Agent Social Media) hem direct in de
"📅 Planning"-tab toont.

Dit project past zich aan op de **bestaande** Sheet/Drive-structuur van de
Social Media Agent (`/Users/danielreitsma/Desktop/Marketing Agent Social Media`)
en wijzigt die codebase niet.

## Architectuur: cloud-dashboard + lokale worker

`dashboard.py` draait op Streamlit Community Cloud (toegankelijk voor het hele
team) en kan **geen** InDesign aansturen — Streamlit Cloud heeft geen toegang
tot lokale software of bestanden. De daadwerkelijke afbeeldingsgeneratie wordt
daarom uitgevoerd door `systems/run_worker.py`, **handmatig** gestart op een
Mac met Adobe InDesign:

```
python systems/run_worker.py
```

Cloud-dashboard en lokale worker communiceren uitsluitend via twee extra
tabbladen in de gedeelde Sheet (`Foto_Index` en `Genereer_Taken`) — geen
directe verbinding nodig.

## Trigger

- **Cloud-dashboard**: team opent de gedeployde Streamlit-app, kiest een week,
  selecteert per post een foto en klikt op "🪄 Vraag generatie aan" — dit
  schrijft een rij naar `Genereer_Taken`.
- **Lokale worker**: iemand met InDesign draait handmatig
  `python systems/run_worker.py` wanneer er nieuwe aanvragen zijn. Dit
  ververst ook `Foto_Index`.

## Gedeelde Google Sheet

Zelfde Sheet als de Social Media Agent (`GOOGLE_SHEETS_SPREADSHEET_ID` +
`GOOGLE_SERVICE_ACCOUNT_JSON` in `.env`, gekopieerd uit
`Marketing Agent Social Media/.env`).

### `Posts_YYYY_WNN`-tabbladen (kolommen A-J, door Social Media Agent gevuld)

Relevante kolommen: `klant_id`, `bedrijfsnaam`, `platform`, `dag`,
`publicatiedatum`, `caption`, `hashtags`, `status`, `beeldtitel`.

Een rij is **klaar voor afbeeldingsgeneratie** als `status = goedgekeurd` en
kolom M (`afbeelding_url`) leeg is.

### Kolommen K-Q (planning, door beide dashboards gedeeld)

| Kolom | Naam | Wie schrijft |
|---|---|---|
| K | `geplande_datum` | Hoofddashboard (Planning-tab) |
| L | `geplande_tijd` | Hoofddashboard (Planning-tab) |
| M | `afbeelding_url` | **Dit project**, na upload naar Drive |
| N | `afbeelding_drive_id` | **Dit project**, na upload naar Drive |
| O-Q | publicatie-status/-log | Hoofddashboard (`publish_scheduled_posts.py`) |

`systems/sheet_queue._ensure_planning_columns()` vult deze kolommen aan op
oudere tabbladen, identiek aan de logica in het hoofddashboard.

### `Sheet1` (klantprofielen)

Gebruikt voor `bedrijfsnaam` en `google_doc_folder_id` (Drive-doelmap voor
upload), via `systems/sheet_queue.load_clients_basic()`.

### `Beeld_Config`-tab (nieuw, door dit project beheerd)

Kolommen: `klant_id`, `foto_map`, `template_pad`. Per klant:
- `foto_map`: lokaal pad naar een map met bronfoto's
- `template_pad`: lokaal pad naar het `.indd`/`.indt`-template

Wordt automatisch aangemaakt door `systems/client_settings.py` zodra er voor
het eerst in opgeslagen wordt (zelfde patroon als de "Medewerkers"-tab in het
hoofddashboard).

### `Foto_Index`-tab (nieuw, door de lokale worker geschreven)

Kolommen: `klant_id`, `bestandsnaam`. Bevat per klant de bestandsnamen die de
worker heeft aangetroffen in de geconfigureerde `foto_map`. Het
cloud-dashboard gebruikt dit als foto-keuzelijst (heeft zelf geen toegang tot
de lokale schijf).

### `Genereer_Taken`-tab (nieuw, takenlijst)

Eén rij per generatie-aanvraag. Kolommen: `tab_name`, `row_index`, `klant_id`,
`beeldtitel`, `gekozen_foto`, `status` (`wachtend`/`bezig`/`klaar`/`fout`),
`log`, `aangemaakt_op`, `bijgewerkt_op`. Het cloud-dashboard schrijft
`wachtend`-rijen (of overschrijft een `fout`-rij om opnieuw te proberen); de
lokale worker zet `bezig` → `klaar`/`fout`.

## Systems

| Script | Omschrijving |
|---|---|
| `systems/sheet_queue.py` | Leest `Posts_*`-tabs en `Sheet1`, schrijft `afbeelding_url`/`afbeelding_drive_id` terug |
| `systems/client_settings.py` | Leest/schrijft de `Beeld_Config`-tab |
| `systems/task_queue.py` | Leest/schrijft `Foto_Index` en `Genereer_Taken` (cloud ↔ worker) |
| `systems/list_client_photos.py` | Lijst afbeeldingen in een geconfigureerde foto-map (gebruikt door de worker) |
| `systems/generate_social_image.py` | Vult InDesign-template via `fill_template.jsx` en exporteert JPG (gebruikt door de worker) |
| `systems/fill_template.jsx` | ExtendScript dat `TITLE_TEXT`/`PHOTO_FRAME` vult |
| `systems/drive_upload.py` | Upload naar `Planning`-submap van de klant-Drive-map, publiek leesbaar (gebruikt door de worker) |
| `systems/run_worker.py` | Lokale worker: ververst `Foto_Index` en verwerkt `wachtend`-taken uit `Genereer_Taken` |

## Stappen (dashboard-flow)

1. Teamlid opent het cloud-dashboard, kiest een week (`Posts_YYYY_WNN`-tab).
2. Dashboard toont per klant de goedgekeurde posts zonder afbeelding
   (`_beeld_status = "nodig"`), met `beeldtitel` en caption-preview.
3. Teamlid kiest een foto uit `Foto_Index` (gevuld door de laatste worker-run)
   van die klant.
4. Klik op "🪄 Vraag generatie aan" → `task_queue.upsert_task()` schrijft een
   `wachtend`-rij naar `Genereer_Taken`. Rij toont daarna "⏳ Wordt verwerkt
   door de lokale agent".
5. Iemand met InDesign draait `python systems/run_worker.py`:
   - ververst `Foto_Index` voor alle klanten
   - pakt `wachtend`-taken op, zet ze op `bezig`
   - `generate_social_image.generate()` met `template_pad`, gekozen foto,
     `beeldtitel` → output naar `output/<tab>_<rij>.jpg`; bij
     `overflow: true` wordt dit in `log` vermeld maar de flow gaat door
   - `drive_upload.upload_image_file()` naar de `Planning`-submap van
     `google_doc_folder_id`, daarna `sheet_queue.write_image_link()` → kolom
     M/N van de `Posts_*`-rij gevuld
   - taak krijgt `status=klaar` (of `fout` met leesbare `log` bij een
     exceptie — andere taken worden gewoon afgehandeld)
6. Rij verdwijnt uit "nodig" en verschijnt als "✅ ... — al gekoppeld" zodra
   `afbeelding_url` gevuld is.

## Edge cases

- **Geen `foto_map`/`template_pad` ingesteld voor een klant**: waarschuwing
  bovenaan de klantsectie/per rij, met verwijzing naar het tabblad
  ⚙️ Instellingen. "Vraag generatie aan"-knop blijft uitgeschakeld.
- **Geen `beeldtitel` ingevuld** door de Social Media Agent: knop
  uitgeschakeld met duidelijke melding.
- **Titel te lang (overflow)**: `fill_template.jsx` geeft `overflow: true`
  terug; de worker plaatst de afbeelding alsnog en zet dit in de `log`-kolom
  van de taak ter info.
- **Geen `google_doc_folder_id`** voor de klant in `Sheet1`: de worker zet de
  taak op `fout` met deze melding; dashboard toont "🔁 Opnieuw proberen" zodra
  dit in `Sheet1` is aangevuld.
- **Taak op `fout`**: dashboard toont de `log`-foutmelding en een "🔁 Opnieuw
  proberen"-knop, die de bestaande taakrij overschrijft naar `wachtend`.
- **Geen foto's in `Foto_Index` voor een klant**: meestal betekent dit dat de
  worker nog niet (recent) gedraaid heeft, of dat `foto_map` niet (correct)
  is ingesteld — melding verwijst naar `python systems/run_worker.py`.
- **Dubbele klik / opnieuw aanvragen voor een rij die al `afbeelding_url`
  heeft**: rij valt dan in `_beeld_status = "klaar"` en wordt niet meer als
  "nodig" getoond — wil de gebruiker de afbeelding vervangen, dan moet dit
  voorlopig handmatig in de Sheet (kolom M leegmaken).

## Template-vereisten

Zie `blueprints/indesign_template_setup.md` voor hoe het `.indt`/`.indd`
template per klant wordt opgezet (script labels `TITLE_TEXT` en
`PHOTO_FRAME`).

## Geleerde lessen

- **InDesign-versie**: op dit systeem werkt InDesign 2026
  (`INDESIGN_APP_NAME="Adobe InDesign 2026"`). InDesign 2025 gaf
  foutmeldingen bij `do script via osascript`.
- **Foto vervangen via `relink`, niet `place()`**:
  `photoFrame.place(File(...))` op een frame dat al een afbeelding bevat geeft
  de fout *"Door deze waarde worden één of meer objecten van het plakbord
  verwijderd"*. Oplossing: `photoFrame.images[0].itemLink.relink(File(nieuwPad))`.
  Het `PHOTO_FRAME` in het template moet dus altijd al een
  placeholder-afbeelding bevatten.
- **`app.scriptPreferences.userInteractionLevel = UserInteractionLevels.NEVER_INTERACT`**
  zetten aan het begin van het script om popup-dialogen te voorkomen.
- **JPG-export**: `app.jpegExportPreferences.pageString = "1"` instellen,
  anders geeft `exportFile` de fout *"het opgegeven paginanummer is ongeldig"*.
- **Geen native JSON in ExtendScript**: `JSON.parse`/`JSON.stringify` bestaan
  niet. We gebruiken een eigen lichte serialisatie (regex-extractie voor
  input, handgeschreven stringify voor output) in `fill_template.jsx`.
- **Bestandsencoding**: zet `file.encoding = "UTF-8"` op zowel het job- als
  resultaatbestand, anders geeft Python `UnicodeDecodeError` bij het lezen van
  resultaten met speciale tekens (bijv. accenten in foutmeldingen).
- **Template-structuur Artena** (`templates/social_post_artena.indd`): de
  headline-tekst kreeg label `TITLE_TEXT`, en de Rectangle-frame rond de
  hoofdfoto kreeg label `PHOTO_FRAME`. Let op: in `allPageItems` is een
  geplaatste afbeelding een apart `Image`-object, los van de omringende
  `Rectangle`-frame — label altijd de **frame** (Rectangle), niet de Image,
  want `relink` gaat via `frame.images[0].itemLink`.
- **Titel centreren**: in `fill_template.jsx` na het invullen van
  `TITLE_TEXT` zowel `textFramePreferences.verticalJustification =
  VerticalJustification.CENTER_ALIGN` als `paragraphs[i].justification =
  Justification.CENTER_ALIGN` zetten, zodat de tekst altijd netjes
  gecentreerd in het oranje vlak staat, ongeacht de lengte.
- **Foto-fitting**: de foto wordt niet uitgevuld/bijgesneden
  (`FILL_PROPORTIONALLY`), maar volledig en proportioneel getoond binnen het
  `PHOTO_FRAME` (`fit(PROPORTIONALLY)` + `fit(CENTER_CONTENT)`). Hierdoor
  blijft altijd de complete foto zichtbaar; er kan witruimte ontstaan als de
  foto-verhouding afwijkt van de framerverhouding. Gezichtsdetectie
  (`systems/smart_crop_photo.py`, Apple Vision-framework) is hierdoor niet
  meer nodig in de actieve pipeline, maar blijft staan voor eventueel
  toekomstig gebruik.
- **Sheet/Drive-koppeling**: in plaats van een eigen "Social Image Queue"-Sheet
  haakt dit project aan op de bestaande `Posts_YYYY_WNN`-tabs en
  `google_doc_folder_id` van de Social Media Agent. Drive-upload gebruikt
  dezelfde "Planning"-submap en publieke leesrechten als
  `Marketing Agent Social Media/systems/drive_upload.py`, zodat de Meta Graph
  API de afbeelding later kan ophalen.
- **Cloud-dashboard kan geen InDesign aansturen**: Streamlit Community Cloud
  heeft geen toegang tot lokale software (`osascript`/InDesign) of de lokale
  schijf (foto-mappen, templates). Daarom is de app gesplitst: het
  cloud-dashboard (`dashboard.py`) toont status en laat het team een foto
  kiezen + generatie aanvragen, en een lokale worker
  (`systems/run_worker.py`, handmatig gestart) doet het echte werk. De twee
  delen communiceren uitsluitend via de `Foto_Index`- en
  `Genereer_Taken`-tabbladen — geen directe verbinding nodig, en de bestaande
  `systems/`-modules (`generate_social_image`, `drive_upload`,
  `list_client_photos`, `sheet_queue`, `client_settings`) zijn ongewijzigd
  hergebruikt door de worker.
- **Credentials lokaal vs. cloud**: `dashboard.py` leest credentials eerst uit
  `st.secrets` (voor de cloud-deploy: `GOOGLE_SHEETS_SPREADSHEET_ID` +
  `GOOGLE_SERVICE_ACCOUNT_JSON`, of base64 via `GOOGLE_SERVICE_ACCOUNT_B64` /
  `GOOGLE_SA_B64_1`+`GOOGLE_SA_B64_2` als het JSON-blob te groot is voor één
  secret), en valt anders terug op `.env` (lokaal). De worker leest alleen
  `.env`.
