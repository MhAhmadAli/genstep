#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="pigpiod-genstep.service"
SOURCE_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/${SERVICE_NAME}"
TARGET_FILE="/etc/systemd/system/${SERVICE_NAME}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Please run as root: sudo ./scripts/install_pigpiod_service.sh"
  exit 1
fi

if ! command -v pigpiod >/dev/null 2>&1; then
  echo "pigpiod binary was not found in PATH."
  echo "Install pigpio first (for example: sudo apt install pigpio)."
  exit 1
fi

if [[ ! -f "${SOURCE_FILE}" ]]; then
  echo "Service template not found: ${SOURCE_FILE}"
  exit 1
fi

cp "${SOURCE_FILE}" "${TARGET_FILE}"
chmod 644 "${TARGET_FILE}"

systemctl daemon-reload
systemctl reset-failed "${SERVICE_NAME}" || true

# If pigpiod was started manually before installing the service,
# it can hold /var/run/pigpio.pid and block service startup.
if pgrep -x pigpiod >/dev/null 2>&1; then
  echo "Stopping existing pigpiod process to avoid PID lock conflict..."
  pkill -x pigpiod || true
  sleep 1
fi

systemctl enable --now "${SERVICE_NAME}"

echo "Installed and enabled ${SERVICE_NAME}."
echo "Status:"
systemctl --no-pager --full status "${SERVICE_NAME}" || true
