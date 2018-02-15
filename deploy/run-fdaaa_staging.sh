#!/usr/bin/env bash

cd /var/www/fdaaa_staging/clinicaltrials-act-tracker/clinicaltrials

. /etc/profile.d/fdaaa_staging.sh && exec ../../venv/bin/gunicorn clinicaltrials.wsgi -c ../deploy/gunicorn-fdaaa_staging.conf.py
