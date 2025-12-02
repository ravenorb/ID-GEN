#target photoshop

// ======================================================================
// FULLY AUTOMATED ID CARD PRODUCTION SYSTEM
// ======================================================================

var ROOT      = "C:/IDCARD_APP/";
var PSD_PATH  = ROOT + "texdl.psd";
var OUTPUTDIR = ROOT + "output/";
var LOG_FILE  = File(ROOT + "automation_log.txt");

// ----------------------------------------------------------------------
// LOGGING
// ----------------------------------------------------------------------
function log(msg) {
    LOG_FILE.open("a");
    LOG_FILE.writeln(new Date().toISOString() + " - " + msg);
    LOG_FILE.close();
}

// BEGIN MAIN WRAPPER  (THIS MUST MATCH WITH CLOSING BRACE)
(function () {

    app.displayDialogs = DialogModes.NO;  // Headless mode

    log("=== SCRIPT STARTED ===");

    // Check PSD
    if (!File(PSD_PATH).exists) {
        log("ERROR: PSD not found: " + PSD_PATH);
        return;
    }

    // Get ID subfolders
    var outputFolder = new Folder(OUTPUTDIR);
    var subfolders = outputFolder.getFiles(function(f){ return f instanceof Folder; });

    if (subfolders.length === 0) {
        log("ERROR: No ID folders found.");
        return;
    }

    // EXPORT PNG HELPERS ------------------------------------------------
    function exportPNG(doc, savePath) {
        var opts = new ExportOptionsSaveForWeb();
        opts.format = SaveDocumentType.PNG;
        opts.PNG8 = false;
        opts.transparency = true;
        opts.interlaced = false;
        opts.optimized = true;
        doc.exportDocument(File(savePath), ExportType.SAVEFORWEB, opts);
    }

    function toggleLayer(doc, name, vis) {
        try {
            doc.layerSets.getByName(name).visible = vis;
        } catch (e1) {
            try {
                doc.artLayers.getByName(name).visible = vis;
            } catch (e2) {
                log("ERROR: Cannot find layer or artboard: " + name);
            }
        }
    }

    // PROCESS EACH ID FOLDER --------------------------------------------
    for (var i = 0; i < subfolders.length; i++) {

        var id = subfolders[i].name;
        var folderPath = OUTPUTDIR + id + "/";
        var csvFile    = File(folderPath + "data.csv");
        var frontFile  = File(folderPath + "front.png");
        var backFile   = File(folderPath + "back.png");

        log("Processing ID: " + id);

        // Skip if already done
        if (frontFile.exists && backFile.exists) {
            log("   Skipped (already processed)");
            continue;
        }

        // Missing CSV
        if (!csvFile.exists) {
            log("   ERROR: Missing data.csv");
            continue;
        }

        // OPEN PSD
        var doc;
        try {
            doc = app.open(File(PSD_PATH));
        } catch (e) {
            log("   ERROR opening PSD: " + e);
            continue;
        }

        // Update linked files
        try {
            doc.updateLinkedFiles();
        } catch (e) {
            log("   Warning: Could not update linked files.");
        }

        // Import CSV
        try {
            doc.importVariables(csvFile);
        } catch (e) {
            log("   ERROR importing CSV: " + e);
            doc.close(SaveOptions.DONOTSAVECHANGES);
            continue;
        }

        // Apply dataset
        try {
            doc.dataSets[0].apply();
        } catch (e) {
            log("   ERROR applying dataset: " + e);
            doc.close(SaveOptions.DONOTSAVECHANGES);
            continue;
        }

        // FRONT
        toggleLayer(doc, "front", true);
        toggleLayer(doc, "back", false);
        exportPNG(doc, frontFile.fsName);
        log("   Exported front.png");

        // BACK
        toggleLayer(doc, "front", false);
        toggleLayer(doc, "back", true);
        exportPNG(doc, backFile.fsName);
        log("   Exported back.png");

        // CLOSE WITHOUT SAVING
        doc.close(SaveOptions.DONOTSAVECHANGES);
        log("   Completed ID: " + id);
    }

    log("=== SCRIPT FINISHED ===");

})(); // <-- THIS IS THE CLOSING BRACKET THAT WAS MISSING
