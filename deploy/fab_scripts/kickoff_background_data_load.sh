#!/bin/bash

# This invocation uses `dtach` to run the load process. The
# indirection via bash is to capture any errors

set -e

if [ $# -eq 0 ]
then
    profile="fdaaa_staging"
else
    profile="$1"
fi

. /etc/profile.d/$profile.sh
rm -f /mnt/volume-lon1-01/$profile_data_load.stderr
dtach -n `mktemp -u /tmp/dtach.XXXX` /bin/bash -c "/var/www/$profile/venv/bin/python /var/www/$profile/clinicaltrials-act-tracker/clinicaltrials/manage.py load_data > /mnt/volume-lon1-01/$profile_data_load.out 2>&1"
