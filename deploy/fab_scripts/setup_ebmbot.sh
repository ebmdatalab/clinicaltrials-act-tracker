#!/bin/bash

set -e

supervisorconf=/var/www/$1/clinicaltrials-act-tracker/deploy/supervisor-ebmbot.conf

if [ ! -f $supervisorconf ] ; then
    echo "Unable to find $supervisorconf!"
    exit 1
fi

test=$(sudo -u ebmbot ssh localhost sudo /var/www/$1/clinicaltrials-act-tracker/deploy/fab_scripts/hello.sh)

if [ $? -gt 0 ]; then
    echo "User `ebmbot` should be set up to ssh to localhost without a prompt, and should have nopasswd sudo rights to execute scripts in /var/www/fdaaa/clinicaltrials-act-tracker/deploy/fab_scripts/"
    exit 1
fi

ln -sf $supervisorconf /etc/supervisor/conf.d/ebmbot.conf
supervisorctl restart ebmbot
