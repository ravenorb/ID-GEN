from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

import idcard_tool

APP_NAME = "id-gen-backend"
OUTPUT_ROOT = Path(os.getenv("OUTPUT_ROOT", "output")).resolve()
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="ID-GEN API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _save_upload(upload: UploadFile | None) -> str | None:
    if not upload:
        return None
    suffix = Path(upload.filename or "").suffix or ""
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as tmp:
        shutil.copyfileobj(upload.file, tmp)
    return path


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/generate")
async def generate(
    varDLN: Annotated[str, Form(...)],
    varFIRST: Annotated[str, Form(...)],
    varMID: Annotated[str, Form(...)],
    varLAST: Annotated[str, Form(...)],
    varDOB: Annotated[str, Form(...)],
    varADD: Annotated[str, Form(...)],
    varCITY: Annotated[str, Form(...)],
    varZIP: Annotated[str, Form(...)],
    varFOUR: Annotated[str, Form(...)],
    varFISS: Annotated[str, Form(...)],
    varISS: Annotated[str, Form(...)],
    varEXP: Annotated[str, Form(...)],
    varRACE: Annotated[str, Form(...)],
    varSEX: Annotated[str, Form(...)],
    varFEET: Annotated[str, Form(...)],
    varINCH: Annotated[str, Form(...)],
    varWGHT: Annotated[str, Form(...)],
    varEYES: Annotated[str, Form(...)],
    varHAIR: Annotated[str, Form(...)],
    varDD: Annotated[str, Form(...)],
    varINV: Annotated[str, Form(...)],
    varREST: Annotated[str, Form("NONE")],
    varEND: Annotated[str, Form("NONE")],
    photo: UploadFile | None = File(None),
    signature: UploadFile | None = File(None),
):
    payload = {
        "varDLN": varDLN,
        "varFIRST": varFIRST,
        "varMID": varMID,
        "varLAST": varLAST,
        "varDOB": varDOB,
        "varADD": varADD,
        "varCITY": varCITY,
        "varZIP": varZIP,
        "varFOUR": varFOUR,
        "varFISS": varFISS,
        "varISS": varISS,
        "varEXP": varEXP,
        "varRACE": varRACE,
        "varSEX": varSEX,
        "varFEET": varFEET,
        "varINCH": varINCH,
        "varWGHT": varWGHT,
        "varEYES": varEYES,
        "varHAIR": varHAIR,
        "varDD": varDD,
        "varINV": varINV,
        "varREST": varREST,
        "varEND": varEND,
    }

    tmp_photo = await _save_upload(photo)
    tmp_signature = await _save_upload(signature)

    try:
        result = idcard_tool.generate_outputs(
            payload,
            output_root=str(OUTPUT_ROOT),
            photo_path=tmp_photo,
            signature_path=tmp_signature,
            create_images=True,
        )
    except ValueError as exc:  # surface validation issues cleanly
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        # Clean up temp uploads
        for path in (tmp_photo, tmp_signature):
            if path and Path(path).exists():
                Path(path).unlink()

    return {
        "message": "Generated",
        "outdir": result["outdir"],
        "csv": result["csv"],
        "pdf417": result["pdf417"],
        "code128": result["code128"],
        "front": result.get("front"),
        "back": result.get("back"),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
