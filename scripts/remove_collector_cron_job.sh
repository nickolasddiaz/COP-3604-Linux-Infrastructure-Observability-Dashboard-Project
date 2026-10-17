#!/bin/bash
# remove_collector_cron_job.sh
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
WRAPPER_FILE="$SCRIPT_DIR/collector_wrapper.sh"

# Match the exact cron entry created by add_collector_cron_job.sh.
printf -v CRON_WRAPPER '%q' "$WRAPPER_FILE"
CRON_JOB="*/5 * * * * $CRON_WRAPPER"

# Read the current crontab once, preserving all unrelated entries.
CURRENT_CRONTAB="$(crontab -l 2>/dev/null || true)"
if printf '%s\n' "$CURRENT_CRONTAB" | grep -Fqx -- "$CRON_JOB"; then
    if ! { printf '%s\n' "$CURRENT_CRONTAB" | grep -Fvx -- "$CRON_JOB" || true; } | crontab -; then
        echo "Error: Could not update crontab." >&2
        exit 1
    fi
    echo "Successfully removed the cron job."
else
    echo "Cron job not found. Nothing to remove."
fi

# Remove the wrapper and downloaded collector created by the add script.
rm -f -- "$WRAPPER_FILE" "$SCRIPT_DIR/collectors"
