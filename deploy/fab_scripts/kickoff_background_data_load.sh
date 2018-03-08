#!/bin/bash

# This invocation uses `dtach` to run the load process. The
# indirection via bash is to capture any errors

set -e

. /etc/profile.d/$1.sh
rm -f /mnt/volume-lon1-01/$1_data_load.stderr
dtach -n `mktemp -u /tmp/dtach.XXXX` /bin/bash -c "/var/www/$1/venv/bin/python /var/www/$1/clinicaltrials-act-tracker/load_data.py > /mnt/volume-lon1-01/$1_data_load.out 2>&1"
