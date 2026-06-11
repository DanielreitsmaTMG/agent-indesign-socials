/*
 * Vult een InDesign .indt template met een titel en foto, en exporteert als JPG.
 *
 * Verwacht een job-bestand op een vast pad: systems/_job.json met de structuur:
 * {
 *   "template_path": "/.../templates/social_post.indt",
 *   "photo_path": "/.../assets/photos/foto.jpg",
 *   "title": "De titel van de afbeelding",
 *   "output_path": "/.../output/123.jpg"
 * }
 *
 * Resultaat wordt teruggeschreven naar systems/_job_result.json:
 * { "success": true } of { "success": false, "error": "...", "overflow": true/false }
 */

function jsonStringify(obj) {
    if (obj === null || obj === undefined) return "null";
    if (typeof obj === "string") {
        return '"' + obj.replace(/\\/g, "\\\\").replace(/"/g, '\\"').replace(/\n/g, "\\n").replace(/\r/g, "") + '"';
    }
    if (typeof obj === "number" || typeof obj === "boolean") return String(obj);
    var pairs = [];
    for (var key in obj) {
        if (obj.hasOwnProperty(key)) {
            pairs.push(jsonStringify(key) + ":" + jsonStringify(obj[key]));
        }
    }
    return "{" + pairs.join(",") + "}";
}

function extractJsonValue(text, key) {
    var re = new RegExp('"' + key + '"\\s*:\\s*"((?:[^"\\\\]|\\\\.)*)"');
    var m = text.match(re);
    if (!m) return null;
    return m[1].replace(/\\"/g, '"').replace(/\\\\/g, "\\");
}

(function () {
    var jobFile = File($.getenv("HOME") + "/Desktop/Agents/Agent Indesign socials/systems/_job.json");
    var resultFile = File($.getenv("HOME") + "/Desktop/Agents/Agent Indesign socials/systems/_job_result.json");

    function writeResult(obj) {
        resultFile.encoding = "UTF-8";
        resultFile.open("w");
        resultFile.write(jsonStringify(obj));
        resultFile.close();
    }

    if (!jobFile.exists) {
        writeResult({ success: false, error: "_job.json niet gevonden" });
        return;
    }

    jobFile.encoding = "UTF-8";
    jobFile.open("r");
    var jobText = jobFile.read();
    jobFile.close();
    var job = {
        template_path: extractJsonValue(jobText, "template_path"),
        photo_path: extractJsonValue(jobText, "photo_path"),
        title: extractJsonValue(jobText, "title"),
        output_path: extractJsonValue(jobText, "output_path")
    };

    var doc;
    try {
        app.scriptPreferences.userInteractionLevel = UserInteractionLevels.NEVER_INTERACT;

        doc = app.open(File(job.template_path));

        // Titel invullen via script label TITLE_TEXT
        var titleFrame = findByLabel(doc, "TITLE_TEXT");
        if (!titleFrame) {
            throw new Error("Geen object met script label TITLE_TEXT gevonden");
        }
        titleFrame.contents = job.title;

        // Tekst horizontaal en verticaal centreren in het frame
        titleFrame.textFramePreferences.verticalJustification = VerticalJustification.CENTER_ALIGN;
        for (var pi = 0; pi < titleFrame.paragraphs.length; pi++) {
            titleFrame.paragraphs[pi].justification = Justification.CENTER_ALIGN;
        }

        // Foto vervangen via script label PHOTO_FRAME (relink van bestaande afbeelding)
        var photoFrame = findByLabel(doc, "PHOTO_FRAME");
        if (!photoFrame) {
            throw new Error("Geen object met script label PHOTO_FRAME gevonden");
        }
        if (photoFrame.images.length === 0) {
            throw new Error("PHOTO_FRAME bevat geen afbeelding om te vervangen");
        }
        photoFrame.images[0].itemLink.relink(File(job.photo_path));

        // Hele foto zichtbaar tonen, geschaald binnen het frame, gecentreerd
        // (geen bijsnijden, dus geen gezichtspositionering nodig)
        photoFrame.fit(FitOptions.PROPORTIONALLY);
        photoFrame.fit(FitOptions.CENTER_CONTENT);

        // Controleer op tekst-overflow
        var overflow = false;
        if (titleFrame.hasOwnProperty("overflows")) {
            overflow = titleFrame.overflows;
        }

        // Exporteren als JPG
        app.jpegExportPreferences.exportResolution = 150;
        app.jpegExportPreferences.jpegQuality = JPEGOptionsQuality.HIGH;
        app.jpegExportPreferences.pageString = "1";
        doc.exportFile(ExportFormat.JPG, File(job.output_path));

        doc.close(SaveOptions.NO);

        writeResult({ success: true, overflow: overflow });
    } catch (e) {
        if (doc) {
            try { doc.close(SaveOptions.NO); } catch (e2) {}
        }
        writeResult({ success: false, error: e.toString() });
    }

    function findByLabel(document, label) {
        for (var p = 0; p < document.pages.length; p++) {
            var items = document.pages[p].allPageItems;
            for (var i = 0; i < items.length; i++) {
                if (items[i].label === label) {
                    return items[i];
                }
            }
        }
        return null;
    }
})();
