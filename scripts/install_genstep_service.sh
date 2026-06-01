#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="genstep-main.service"
SOURCE_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/${SERVICE_NAME}"
TARGET_FILE="/etc/systemd/system/${SERVICE_NAME}"
APP_DIR="/home/genstep/Desktop/genstep"
VENV_PYTHON="${APP_DIR}/.venv/bin/python"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Please run as root: sudo ./scripts/install_genstep_service.sh"
  exit 1
fi

if [[ ! -f "${SOURCE_FILE}" ]]; then
  echo "Service template not found: ${SOURCE_FILE}"
  exit 1
fi

if [[ ! -x "${VENV_PYTHON}" ]]; then
  echo "Virtualenv python not found/executable: ${VENV_PYTHON}"
  echo "Create the venv and install dependencies first."
  exit 1
fi

cp "${SOURCE_FILE}" "${TARGET_FILE}"
chmod 644 "${TARGET_FILE}"

systemctl daemon-reload
systemctl reset-failed "${SERVICE_NAME}" || true

systemctl enable --now "${SERVICE_NAME}"

echo "Installed and enabled ${SERVICE_NAME}."
echo "Status:"
systemctl --no-pager --full status "${SERVICE_NAME}" || true
