#!/usr/bin/env bash
set -euo pipefail

# ID-GEN backend setup script for Ubuntu 24.04
# Installs Python dependencies, configures a systemd service, and starts the API server.

if [[ ${EUID} -ne 0 ]]; then
  echo "This script must be run as root (use sudo)."
  exit 1
fi

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "${SCRIPT_DIR}/.." && pwd)
BACKEND_DIR="${REPO_ROOT}/backend"
VENV_DIR="${BACKEND_DIR}/.venv"
SERVICE_NAME="id-gen-backend"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
APP_USER=${SUDO_USER:-${USER}}
OUTPUT_DIR="${REPO_ROOT}/output"

# Install system packages required for Python and building dependencies.
apt-get update
apt-get install -y python3 python3-venv python3-pip python3-dev build-essential

# Create virtual environment and install Python dependencies.
python3 -m venv "${VENV_DIR}"
"${VENV_DIR}/bin/pip" install --upgrade pip
"${VENV_DIR}/bin/pip" install -r "${BACKEND_DIR}/requirements.txt"

# Ensure output directory exists and is writable by the app user.
mkdir -p "${OUTPUT_DIR}"
chown -R "${APP_USER}:${APP_USER}" "${OUTPUT_DIR}"

# Write systemd unit for the FastAPI/uvicorn service.
cat > "${SERVICE_FILE}" <<SERVICE
[Unit]
Description=ID-GEN FastAPI backend
After=network.target

[Service]
Type=simple
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${BACKEND_DIR}
Environment=OUTPUT_ROOT=${OUTPUT_DIR}
ExecStart=${VENV_DIR}/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000
Restart=on-failure

[Install]
WantedBy=multi-user.target
SERVICE

# Reload systemd, enable, and start the service.
systemctl daemon-reload
systemctl enable --now "${SERVICE_NAME}.service"

cat <<SUMMARY
ID-GEN backend setup complete.
- Service name: ${SERVICE_NAME}
- Status: $(systemctl is-active ${SERVICE_NAME})
- Logs: journalctl -u ${SERVICE_NAME} -f
- API: http://localhost:8000 (health at /health)
SUMMARY
