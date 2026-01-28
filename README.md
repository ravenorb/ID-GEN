# ID-GEN

A server-focused workflow for generating driver-license style ID card assets. The repository now assumes a backend service will render the barcodes and composite images; the desktop/Windows executable build has been discontinued.

- `idcard_tool.py`: a Tkinter app that validates user input, builds CSV data, and produces barcode images (PDF417 and Code128). It remains available for local/desktop use, but we no longer package it as a Windows executable.
- `auto.jsx`: an Adobe Photoshop script that consumes the generated CSV data and exports layered front/back card images from a PSD template.
- `backend/`: FastAPI service that validates input and generates CSV, barcodes, and front/back PNGs. Use this for the hosted/web experience.

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
- **Adobe Photoshop** is optional and only needed if you continue to use `auto.jsx`.

Install dependencies locally:

```bash
pip install pdf417gen python-barcode Pillow
```

## Using the Tkinter generator (desktop)

The Tkinter app remains for local workflows. It is no longer bundled or distributed as a Windows executable; run it directly with Python:

```bash
python idcard_tool.py
```

- Date inputs must use `MM/DD/YYYY` format; name fields require 3–30 alphabetic characters; DLN must be exactly 8 digits.
- ISSUE auto-fills from FIRST ISSUE, and EXP auto-fills based on DOB/ISS.
- Outputs are written to `output/<DLN>/`:
  - `data.csv`: header + data row for Photoshop variables
  - `pdf417.png`: AAMVA-style barcode
  - `code128.png`: inventory barcode

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

## Rendering from layered PSD templates (no Photoshop)

For layered PSD workflows without running Photoshop, the generator can also render PNGs from PSD templates using `psd-tools`. This works by treating layer names as placeholders:

- **Text layers:** name layers after any of the variable keys (e.g., `varFIRST`, `varLAST`, `varDLN`, `vardDOB`, `vardISS`, `vardEXP`). The renderer hides the layer and draws the text into its bounding box.
- **Assets:** use layer names `PHOTO`, `SIGNATURE`, `PDF417`, and `CODE128` to place the uploaded photo/signature and generated barcodes into those regions.
- If only a front or back PSD is provided, the missing side falls back to the built-in Pillow layout.

Install the extra dependency first:

```bash
pip install psd-tools
```

When using the FastAPI backend, upload the PSD files as `template_front` and/or `template_back` in the same `/generate` request (see the backend README for an example).

## Server-first backend (Ubuntu friendly)

Deploy the FastAPI backend to handle all CSV/barcode/image generation for the paid web flow. The service runs cleanly on Ubuntu with system Python or a virtual environment.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

- `POST /generate` accepts multipart form data with the existing field names (`varDLN`, `varFIRST`, `varMID`, `varLAST`, etc.) plus optional `photo` and `signature` uploads. It returns JSON paths for `csv`, `pdf417`, `code128`, `front`, and `back`.
- `GET /health` reports `{ "status": "ok" }`.

For production hosting, point a reverse proxy (e.g., Nginx) at the `uvicorn` process or run `uvicorn` behind a process manager such as `systemd` or `supervisor`. All composition happens server-side so client pages never handle barcode logic directly.

## Docker (backend)

Build and run the backend with Docker:

```bash
docker build -t id-gen-backend .
docker run --rm -p 8000:8000 -v "$(pwd)/output:/data/output" id-gen-backend
```

Or use Docker Compose:

```bash
docker compose up --build
```

The container writes generated assets to `./output/` on the host via the mounted volume.

## Web frontend (server-rendered only)

The static form in `www/index.html` now functions strictly as a thin client that posts data and uploads to the backend. It no longer generates CSV or barcodes in the browser. Serve it from any static host (or with `python -m http.server 8080 --directory www`) while pointing `Backend API base URL` to your running FastAPI instance.

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
