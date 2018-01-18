#!/usr/bin/env bash

cd /var/www/fdaaa/clinicaltrials-act-tracker/euctr

. /etc/profile.d/fdaaa.sh && exec ../../venv/bin/gunicorn euctr.wsgi -c ../deploy/gunicorn-fdaaa.conf.py  
