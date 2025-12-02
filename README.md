# ID-GEN

A desktop workflow for generating driver-license style ID card assets. The repository contains:

- `idcard_tool.py`: a Tkinter app that validates user input, builds CSV data, and produces barcode images (PDF417 and Code128).
- `auto.jsx`: an Adobe Photoshop script that consumes the generated CSV data and exports layered front/back card images from a PSD template.
- `idcard_tool.spec`: PyInstaller spec used to bundle the Tkinter app into an executable.

## Features

- **Strict validation**: Ensures driver license numbers, ZIP/FOUR, dates, height, and name lengths conform to configured rules before exporting data.
- **Automatic date logic**: Calculates expected expiration dates (DOB month/day with issue year + 8) and auto-fills ISSUE/EXPIRE based on provided First Issue dates.
- **Barcode generation**: Creates AAMVA-style PDF417 payloads (with control characters) and Code128 inventory labels, writing images alongside CSV output.
- **Debug mode**: Shows the computed dataset and file paths to verify the payload before production.
- **Photoshop automation**: Batch-renders layered PSDs into front/back PNGs for each generated ID folder, logging the process to `automation_log.txt`.
- **Built-in image composer**: Generates front/back PNGs with Pillow (no Photoshop) using the produced barcodes plus optional photo and signature assets.

## Requirements

- **Python 3.11+** with the following packages:
  - `pdf417gen`
  - `python-barcode`
  - `Pillow` (pulled in by dependencies)
- **Adobe Photoshop** for running `auto.jsx` against the `texdl.psd` template.

Install dependencies locally:

```bash
pip install pdf417gen python-barcode Pillow
```

For PyInstaller builds, install `pyinstaller` and (optionally) `upx` for better compression:

```bash
pip install pyinstaller
# macOS/Linux: install UPX via your package manager if desired
```

## Using the Tkinter generator

1. Run the desktop app:
   ```bash
   python idcard_tool.py
   ```
2. Enter required fields. Date inputs must use `MM/DD/YYYY` format; name fields require 3–30 alphabetic characters; DLN must be exactly 8 digits.
3. The form highlights invalid inputs in red and valid inputs in green. ISSUE auto-fills from FIRST ISSUE, and EXP auto-fills based on DOB/ISS.
4. Click **Generate** to create outputs under `output/<DLN>/`:
   - `data.csv`: header + data row for Photoshop variables
   - `pdf417.png`: AAMVA-style barcode
   - `code128.png`: inventory barcode
5. Use **Debug** to inspect the computed variables and file paths without leaving the app.

## Running the Photoshop automation

1. Place your PSD template at `C:/IDCARD_APP/texdl.psd` and the `output/` folder (produced by the Tkinter app) at `C:/IDCARD_APP/output/`.
2. Open Photoshop and run `auto.jsx`. The script will:
   - Iterate over each subfolder inside `output/`,
   - Import `data.csv` into the PSD dataset,
   - Export `front.png` and `back.png` per ID,
   - Write progress to `automation_log.txt` in the root directory.

## Generating front/back images without Photoshop

The Python generator can now compose simple front/back PNGs directly with Pillow. This is useful for server-side workflows or headless environments where Photoshop is unavailable.

```bash
python - <<'PY'
from pathlib import Path
import idcard_tool

data = {
    "varDLN": "12345678",
    "varFIRST": "JANE",
    "varMID": "Q",
    "varLAST": "PUBLIC",
    "varDOB": "01/01/1988",
    "varADD": "123 MAIN ST",
    "varCITY": "AUSTIN",
    "varZIP": "78701",
    "varFOUR": "0001",
    "varFISS": "01/01/2006",
    "varISS": "01/01/2024",
    "varEXP": "01/01/2032",
    "varRACE": "WHITE",
    "varSEX": "F",
    "varFEET": "5",
    "varINCH": "7",
    "varWGHT": "140",
    "varEYES": "BLU",
    "varHAIR": "BRO",
    "varDD": "12345678901234567890",
    "varINV": "1234567890",
    "varREST": "NONE",
    "varEND": "NONE",
}

out = idcard_tool.generate_outputs(
    data,
    output_root=Path(__file__).parent / "output",
    photo_path="/path/to/photo.jpg",        # optional
    signature_path="/path/to/signature.png",# optional
    create_images=True,
)

print(out["front"])
print(out["back"])
PY
```

If `photo_path` or `signature_path` are omitted, the composer will insert framed placeholders. Generated assets live alongside the CSV and barcode files in `output/<DLN>/`.

## Backend API starter

Spin up a FastAPI service that reuses the same validation and generation logic (including optional photo/signature overlays) by pointing it at the `backend/` folder:

```bash
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8000
```

- `POST /generate` accepts multipart form data with the existing field names (`varDLN`, `varFIRST`, `varMID`, `varLAST`, etc.) plus optional `photo` and `signature` uploads.
- The endpoint returns JSON containing the output directory and generated asset paths (`csv`, `pdf417`, `code128`, `front`, `back`).
- A simple `GET /health` returns `{ "status": "ok" }` for uptime probes.

## Frontend with upload + API wiring

The static web form (`www/index.html`) now includes file inputs for **Photo** and **Signature** plus a **Send to Backend API** button. Set the backend base URL (defaults to `http://localhost:8000`), fill the required fields, attach the images, and click the button to POST everything to `/generate`.

You can serve the static form locally while hitting the API with:

```bash
python -m http.server 8080 --directory www
```

Then open http://localhost:8080 in your browser.

## Building distributions

### Desktop executable (PyInstaller)

1. Install dependencies:
   ```bash
   pip install pdf417gen python-barcode Pillow pyinstaller
   # Optional but recommended for smaller binaries
   sudo apt-get install upx  # Linux example
   ```
2. Build the app:
   ```bash
   pyinstaller idcard_tool.spec --clean
   ```
3. Find the bundled app in `dist/idcard_tool/` (produced locally or by the GitHub Action). Zip that folder to distribute.

You can also trigger the **Build desktop executable** GitHub Action manually to produce an artifact without installing anything locally. Provide a `release_tag` input to have the workflow publish the zipped build as a GitHub Release asset (optionally set `release_name` or `prerelease`).
You can also trigger the **Build desktop executable** GitHub Action manually to produce an artifact without installing anything locally.

### Static web package

The HTML/JS version is self-contained in `www/index.html` and relies on CDN scripts. To package it:
1. Create a zip:
   ```bash
   zip -r id-gen-web.zip www
   ```
2. Host the contents of the `www/` folder on any static host (or open `index.html` locally). The **Build web package** GitHub Action can be run manually to produce the zip artifact for download.

## Project structure

```
ID-GEN/
├─ idcard_tool.py      # Tkinter app + data generation logic
├─ auto.jsx            # Photoshop automation script
├─ idcard_tool.spec    # PyInstaller build configuration
└─ output/             # Created at runtime for generated assets
```

## Next steps

- **Add automated tests** for the validation utilities (date math, length checks, and barcode payload construction) to reduce regression risk.
- **Parameterize paths** (especially `C:/IDCARD_APP/` in `auto.jsx`) so the Photoshop workflow can run on different machines without editing the script.
- **Document sample data** and include a demo PSD/template to help new users verify the pipeline end-to-end.
- **Package the app** with PyInstaller using `idcard_tool.spec` and publish installation instructions for non-developer users.
