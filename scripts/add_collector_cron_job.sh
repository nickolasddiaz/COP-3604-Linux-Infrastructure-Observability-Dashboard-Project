#!/usr/bin/env bash
# add_collector_cron_job.sh

# check if sudo
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as sudo" 1>&2
   exit 1
fi

# Check that the IP and Port argument was provided.
while getopts "i:p:" opt; do
  case ${opt} in
    i ) IP_ADDRESS=$OPTARG ;;
    p ) PORT=$OPTARG ;;
    \? ) echo "Usage: $0 -i <IP> -p <PORT>" && exit 1 ;;
  esac
done

# Validate that both flags were provided
if [ -z "$IP_ADDRESS" ] || [ -z "$PORT" ]; then
    echo "Error: Both -i (IP) and -p (Port) are required."
    echo "Usage: $0 -i <IP> -p <PORT>"
    exit 1
fi

URL="http://$IP_ADDRESS:$PORT"

USERNAME="collectoruser"

if ! getent passwd "$USERNAME" >/dev/null 2>&1; then
    echo "User $USERNAME does not exist. Creating now..."
    # -s /bin/false prevent the user from logging in
    sudo useradd -m -s /bin/false "$USERNAME"
else
    echo "User $USERNAME already exists."
fi

# Allow access to the IP
sudo iptables -A OUTPUT -m owner --uid-owner "$USERNAME" -d "$IP_ADDRESS" -m comment --comment "$USERNAME" -j ACCEPT
# Block all other IPs
sudo iptables -A OUTPUT -m owner --uid-owner "$USERNAME" -m comment --comment "$USERNAME" -j REJECT



SCRIPT_DIR="/home/$USERNAME"

# Download the collector alongside this script.
FILE="$SCRIPT_DIR/collectors"
if ! wget -O "$FILE" "https://github.com/nickolasddiaz/COP-3604-Linux-Infrastructure-Observability-Dashboard-Project/releases/download/Distrabution/collectors"; then
    echo "collectors could not be downloaded" >&2
    exit 1
fi
chown "$USERNAME" "$FILE"
chmod +x "$FILE"

WRAPPER_FILE="$SCRIPT_DIR/collector_wrapper.sh"
{
    printf '#!/usr/bin/env bash\nexec %q %q\n' "$FILE" --ip "$URL"
} > "$WRAPPER_FILE"
chown "$USERNAME" "$WRAPPER_FILE"
chmod +x "$WRAPPER_FILE"

# Run the collector every 5 minutes.
printf -v CRON_WRAPPER '%q' "$WRAPPER_FILE"
CRON_JOB="*/5 * * * * $CRON_WRAPPER"

# Check whether this exact job already exists.
if crontab -l -u "$USERNAME" 2>/dev/null | grep -Fqx -- "$CRON_JOB"; then
    echo "Cron job already exists. Skipping."
else
    (crontab -l -u "$USERNAME" 2>/dev/null || true; printf '%s\n' "$CRON_JOB") | crontab -u "$USERNAME" -
    echo "Cron job added successfully."
fi
