#!/bin/bash

set -e

cron=$1/clinicaltrials-act-tracker/deploy/crontab-fdaaa-update
ln -sf $cron /etc/cron.d/crontab-fdaaa-update
