#!/usr/bin/env bash
set -euo pipefail

# Generic Debian 12 setup for running ID-GEN with Docker Compose.
# - Installs Docker Engine + Compose plugin
# - Enables Docker service
# - Adds selected user to docker group
# - Starts ID-GEN stack from this repository

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this script as root (for example: sudo bash scripts/setup_debian12_docker.sh)"
  exit 1
fi

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "${SCRIPT_DIR}/.." && pwd)
TARGET_USER="${SUDO_USER:-${USER}}"

if [[ ! -f "${REPO_ROOT}/docker-compose.yml" ]]; then
  echo "Could not find docker-compose.yml in ${REPO_ROOT}."
  exit 1
fi

echo "[1/6] Installing prerequisites"
apt-get update
apt-get install -y ca-certificates curl gnupg lsb-release

install -m 0755 -d /etc/apt/keyrings
if [[ ! -f /etc/apt/keyrings/docker.gpg ]]; then
  echo "[2/6] Adding Docker apt repository key"
  curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
fi
chmod a+r /etc/apt/keyrings/docker.gpg

ARCH=$(dpkg --print-architecture)
CODENAME=$(. /etc/os-release && echo "${VERSION_CODENAME}")

echo "[3/6] Configuring Docker apt repository"
echo \
  "deb [arch=${ARCH} signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian ${CODENAME} stable" \
  > /etc/apt/sources.list.d/docker.list

echo "[4/6] Installing Docker Engine + Compose plugin"
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo "[5/6] Enabling Docker service"
systemctl enable --now docker

if id -u "${TARGET_USER}" >/dev/null 2>&1; then
  usermod -aG docker "${TARGET_USER}" || true
fi

mkdir -p "${REPO_ROOT}/output"
cd "${REPO_ROOT}"

echo "[6/6] Building and starting ID-GEN with Docker Compose"
docker compose up --build -d

echo
cat <<SUMMARY
ID-GEN is now running with Docker Compose.

Useful commands:
- docker compose ps
- docker compose logs -f
- docker compose down

Backend endpoint:
- http://<server-ip>:8000/health

Note:
- If you were added to the docker group, re-login (or run: newgrp docker) for non-root docker usage.
SUMMARY
