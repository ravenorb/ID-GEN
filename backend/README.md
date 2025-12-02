# ID-GEN backend (FastAPI)

This backend exposes the existing generator logic over HTTP so you can drive it from the updated web form or another client.

## Quick start

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
```

By default outputs are written to `../output/`. Override with `OUTPUT_ROOT=/path/to/out uvicorn ...`.

## Endpoints
- `GET /health` → `{ "status": "ok" }` for uptime checks.
- `POST /generate` → multipart form matching the existing field names plus optional `photo` and `signature` files. Returns JSON paths for `csv`, `pdf417`, `code128`, `front`, and `back`.

## Example request (with uploads)

```bash
curl -X POST "http://localhost:8000/generate" \
  -F "varDLN=12345678" -F "varFIRST=JANE" -F "varMID=Q" -F "varLAST=PUBLIC" \
  -F "varDOB=01/01/1988" -F "varADD=123 MAIN ST" -F "varCITY=AUSTIN" \
  -F "varZIP=78701" -F "varFOUR=0001" -F "varFISS=01/01/2006" \
  -F "varISS=01/01/2024" -F "varEXP=01/01/2032" -F "varRACE=WHITE" \
  -F "varSEX=F" -F "varFEET=5" -F "varINCH=7" -F "varWGHT=140" \
  -F "varEYES=BLU" -F "varHAIR=BRO" -F "varDD=12345678901234567890" \
  -F "varINV=1234567890" -F "varREST=NONE" -F "varEND=NONE" \
  -F "photo=@/path/photo.jpg" -F "signature=@/path/signature.png"
```

## Frontend hookup
Point the `Backend API base URL` field in `www/index.html` to your running service (e.g., `http://localhost:8000`) and use **Send to Backend API** to generate assets with uploads.
