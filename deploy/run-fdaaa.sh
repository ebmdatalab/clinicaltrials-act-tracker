#!/usr/bin/env bash

cd /var/www/fdaaa/clinicaltrials-act-tracker/clinicaltrials

. /etc/profile.d/fdaaa.sh && exec ../../venv/bin/gunicorn frontend.wsgi -c ../deploy/gunicorn-fdaaa.conf.py
