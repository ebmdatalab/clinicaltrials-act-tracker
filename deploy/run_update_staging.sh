#!/bin/bash

set -e
. /etc/profile.d/fdaaa_staging.sh

/var/www/fdaaa_staging/venv/bin/python /var/www/fdaaa_staging/clinicaltrials-act-tracker/clinicaltrials/manage.py load_data
