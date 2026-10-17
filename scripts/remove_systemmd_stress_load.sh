#!/usr/bin/env bash
# remove_systemmd_stress_load.sh

# check if sudo
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as sudo" 1>&2
   exit 1
fi

SERVICE_NAME="stress_load"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# Stop and disable the service if it is installed.
systemctl stop "${SERVICE_NAME}.service" 2>/dev/null || true
systemctl disable "${SERVICE_NAME}.service" 2>/dev/null || true

# Remove the unit and its downloaded script, then refresh systemd's unit cache.
rm -f "$SERVICE_FILE" "$SCRIPT_DIR/stress_load.sh"
systemctl daemon-reload
systemctl reset-failed "${SERVICE_NAME}.service" 2>/dev/null || true

echo "Service ${SERVICE_NAME}.service has been removed."