# ID-GEN backend (FastAPI)

This backend hosts the generator logic for the paid, server-side web flow. All barcode and image generation happens here so the browser never performs composition.

## Quick start

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

By default outputs are written to `../output/`. Override with `OUTPUT_ROOT=/path/to/out uvicorn ...`.

For production on Ubuntu/Debian, keep the `uvicorn` process alive with `systemd` or `supervisor` and front it with Nginx/Apache as needed.

## Debian 12 Proxmox LXC note

Many Proxmox LXC containers do not run a full `systemd` init and may block nested Docker by default. In that case, skip Docker and run the backend directly:

```bash
sudo bash scripts/setup_backend.sh
cd backend
source .venv/bin/activate
OUTPUT_ROOT="$(pwd)/../output" uvicorn main:app --host 0.0.0.0 --port 8000
```

## Endpoints
- `GET /health` → `{ "status": "ok" }` for uptime checks.
- `POST /generate` → multipart form matching the existing field names plus optional `photo`, `signature`, `template_front`, and `template_back` files. Returns JSON paths for `csv`, `pdf417`, `code128`, `front`, and `back`.

## Docker

From the repo root:

```bash
docker build -t id-gen-backend .
docker run --rm -p 8000:8000 -v "$(pwd)/output:/data/output" id-gen-backend
```

Docker Compose option:

```bash
docker compose up --build -d
```

For a generic Debian 12 host/container, run the root-level installer script:

```bash
sudo bash scripts/setup_debian12_docker.sh
```

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
  -F "photo=@/path/photo.jpg" -F "signature=@/path/signature.png" \
  -F "template_front=@/path/front.psd" -F "template_back=@/path/back.psd"
```

## Frontend hookup
Point the `Backend API base URL` field in `www/index.html` to your running service (e.g., `http://localhost:8000`) and use **Send to Backend API** to generate assets with uploads.
