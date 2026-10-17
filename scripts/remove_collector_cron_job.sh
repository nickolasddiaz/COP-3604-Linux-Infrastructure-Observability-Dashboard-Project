#!/bin/bash
# remove_collector_cron_job.sh

# check if sudo
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as sudo" 1>&2
   exit 1
fi

USERNAME="collectoruser"
SCRIPT_DIR="/home/$USERNAME"
WRAPPER_FILE="$SCRIPT_DIR/collector_wrapper.sh"

# Deleteing the iptables where the comment contains USERNAME
sudo iptables -L OUTPUT --line-numbers -n | grep "$USERNAME" | awk '{print $1}' | sort -r | xargs -I {} sudo iptables -D OUTPUT {}
echo "Deleting iptables associated with the $USERNAME"

# Match the exact cron entry created by add_collector_cron_job.sh.
printf -v CRON_WRAPPER '%q' "$WRAPPER_FILE"
CRON_JOB="*/5 * * * * $CRON_WRAPPER"

# Read the current crontab once, preserving all unrelated entries.
CURRENT_CRONTAB="$(crontab -l -u "$USERNAME" 2>/dev/null || true)"
if printf '%s\n' "$CURRENT_CRONTAB" | grep -Fqx -- "$CRON_JOB"; then
    if ! { printf '%s\n' "$CURRENT_CRONTAB" | grep -Fvx -- "$CRON_JOB" || true; } | crontab -u "$USERNAME" -; then
        echo "Error: Could not update crontab." >&2
        exit 1
    fi
    echo "Successfully removed the cron job."
else
    echo "Cron job not found. Nothing to remove."
fi

# Delete the collector user and its home directory, including its wrapper and collector.
if ! userdel -r "$USERNAME"; then
    echo "Error: Could not delete user $USERNAME." >&2
    exit 1
fi
