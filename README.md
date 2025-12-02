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
