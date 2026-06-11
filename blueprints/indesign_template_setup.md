# Blueprint: InDesign Template Opzetten

## Doel

Een herbruikbaar `.indt` template maken dat door `systems/fill_template.jsx` automatisch
gevuld kan worden met een titel en foto.

## Stappen voor de designer

1. Ontwerp de social media afbeelding in InDesign zoals gewenst (1 vast formaat, bijv.
   1080x1080px voor Instagram - exacte afmetingen nog te bepalen).
2. Maak een tekstkader voor de titel:
   - Selecteer het tekstkader.
   - Open **Venster > Hulpprogramma's > Scripts** (of gebruik het Scripts-paneel) en geef het
     object een **script label**: ga naar **Venster > Hulpprogramma's > Scriptlabel**, en geef
     het kader het label `TITLE_TEXT`.
3. Maak een afbeeldingskader (frame) voor de foto:
   - Plaats hierin alvast een placeholder-afbeelding (het systeem vervangt deze later via
     `relink`, niet via een lege `place()`).
   - Geef het **frame** (de Rectangle, niet de geplaatste afbeelding zelf) het script label
     `PHOTO_FRAME`. In het Scriptlabel-paneel kun je dit object selecteren door op de rand van
     het frame te klikken (niet op de afbeelding erin).
4. Sla het bestand op als **InDesign Template (.indt)** in de map `templates/`, bijv.
   `templates/social_post.indt`.

## Vereisten voor het systeem

- Het `.jsx`-script zoekt objecten op basis van `pageItem.label`, dus de labels moeten exact
  `TITLE_TEXT` en `PHOTO_FRAME` zijn (hoofdlettergevoelig).
- Het tekstkader moet voldoende ruimte hebben voor titels tot een nog te bepalen maximale lengte.
  Test met de langste verwachte titel en controleer op overflow.
- Het foto-frame moet "Fill Frame Proportionally" gebruiken zodat foto's met verschillende
  verhoudingen netjes passen.

## Testen

1. Plaats een testfoto in `assets/photos/` en vul een testtitel in.
2. Run `systems/generate_social_image.py` met deze testdata.
3. Controleer het resultaat in `output/`.
4. Test met een extra lange titel om het overflow-gedrag te checken.

## Geleerde lessen

- Eerste werkende template: `templates/social_post_artena.indd` (klant Artena), gebaseerd op een
  bestaand .indd-ontwerp. Werkt prima als `.indd` (geen `.indt` nodig) zolang
  `fill_template.jsx` na het vullen sluit zonder op te slaan (`SaveOptions.NO`).
- Zie `blueprints/social_image_generation.md` voor de technische details rondom `relink` en
  script labels.
