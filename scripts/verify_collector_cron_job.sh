#!/usr/bin/env bash
# verify_collector_cron_job.sh

# check if sudo
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as sudo" 1>&2
   exit 1
fi

USERNAME="collectoruser"
HOME_DIR="/home/$USERNAME"

# print home directory
echo "Home directory of $USERNAME"
ls -la $HOME_DIR

# print iptable of user
echo "iptables of $USERNAME"
sudo iptables -L -v -n --line-numbers | grep -i "$USERNAME"


# print cronjob of user
echo "cronjob of $USERNAME"
crontab -u "$USERNAME" -l