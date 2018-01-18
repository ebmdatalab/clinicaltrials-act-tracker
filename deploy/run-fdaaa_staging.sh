#!/usr/bin/env bash

cd /var/www/fdaaa_staging/clinicaltrials-act-tracker/clinicaltrials

. /etc/profile.d/fdaaa_staging.sh && exec ../../venv/bin/gunicorn fdaaa_staging.wsgi -c ../deploy/gunicorn-fdaaa.conf.py
