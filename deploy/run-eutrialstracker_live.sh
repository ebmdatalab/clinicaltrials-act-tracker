#!/usr/bin/env bash

cd /var/www/eutrialstracker_live/euctr-tracker-code/euctr

. /etc/profile.d/eutrialstracker_live.sh && exec ../../venv/bin/gunicorn euctr.wsgi -c ../deploy/gunicorn-eutrialstracker_live.conf.py  
