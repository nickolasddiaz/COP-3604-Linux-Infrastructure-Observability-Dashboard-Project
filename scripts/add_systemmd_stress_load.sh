#!/usr/bin/env bash
# add_systemmd_stress_load.sh

# check if sudo
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as sudo" 1>&2
   exit 1
fi

# current working directory
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# Download the stress_load alongside this script.
FILE="$SCRIPT_DIR/stress_load.sh"
if ! wget -O "$FILE" "https://raw.githubusercontent.com/nickolasddiaz/COP-3604-Linux-Infrastructure-Observability-Dashboard-Project/refs/heads/main/scripts/stress_load.sh"; then
    echo "stress_load could not be downloaded" >&2
    exit 1
fi
chmod +x "$FILE"


SERVICE_NAME="stress_load"
SCRIPT_PATH="$SCRIPT_DIR/stress_load.sh"

# Ensure the target script exists and is executable
if [ ! -f "$SCRIPT_PATH" ]; then
  echo "Error: Target script '$SCRIPT_PATH' does not exist."
  exit 1
fi

SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

echo "Creating systemd service file at: $SERVICE_FILE"

# Generate the systemd service file content
cat <<EOF > "$SERVICE_FILE"
[Unit]
Description=Stress load generator
After=network.target

[Service]
Type=simple
ExecStart=/bin/bash ${SCRIPT_PATH}
Restart=always
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
EOF

# Set secure permissions on the service file
chmod 644 "$SERVICE_FILE"

# Reload systemd to recognize the new service configuration
echo "Reloading systemd daemon..."
systemctl daemon-reload

# Enable the service to start automatically on system boot
echo "Enabling ${SERVICE_NAME}.service to start on boot..."
systemctl enable "${SERVICE_NAME}.service"

# Start the service immediately
echo "Starting ${SERVICE_NAME}.service..."
systemctl restart "${SERVICE_NAME}.service" || systemctl start "${SERVICE_NAME}.service"

echo "Service ${SERVICE_NAME}.service is installed and running."
systemctl status "${SERVICE_NAME}.service" --no-pager | head -n 20