#!/usr/bin/env bash
# add_collector_cron_job.sh

# Check that the URL argument was provided.
if [ -z "$1" ]; then
    echo "Error: Missing URL argument."
    echo "Usage: $0 <URL>"
    exit 1
fi

URL="$1"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# Download the collector alongside this script.
FILE="$SCRIPT_DIR/collectors"
if ! wget -O "$FILE" "https://github.com/nickolasddiaz/COP-3604-Linux-Infrastructure-Observability-Dashboard-Project/releases/download/Distrabution/collectors"; then
    echo "collectors could not be downloaded" >&2
    exit 1
fi
chmod +x "$FILE"

WRAPPER_FILE="$SCRIPT_DIR/collector_wrapper.sh"
{
    printf '#!/usr/bin/env bash\nexec %q %q\n' "$FILE" --ip "$URL"
} > "$WRAPPER_FILE"
chmod +x "$WRAPPER_FILE"

# Run the collector every 5 minutes.
printf -v CRON_WRAPPER '%q' "$WRAPPER_FILE"
CRON_JOB="*/5 * * * * $CRON_WRAPPER"

# Check whether this exact job already exists.
if crontab -l 2>/dev/null | grep -Fqx -- "$CRON_JOB"; then
    echo "Cron job already exists. Skipping."
else
    (crontab -l 2>/dev/null || true; printf '%s\n' "$CRON_JOB") | crontab -
    echo "Cron job added successfully."
fi
