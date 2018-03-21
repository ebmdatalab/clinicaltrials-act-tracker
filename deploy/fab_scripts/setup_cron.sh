#!/bin/bash

set -e

cron=$1/clinicaltrials-act-tracker/deploy/crontab-fdaaa-update
chmod 644 $cron
chown root $cron
ln -sf $cron /etc/cron.d/crontab-fdaaa-update
