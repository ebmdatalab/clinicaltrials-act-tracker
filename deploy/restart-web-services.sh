#!/usr/bin/env bash

service supervisor restart

if nginx -t
then
    service nginx stop 
    # TODO clear correct cache if have multiple instances
    rm -fr /var/cache/nginx/eutrialstracker_live/* 
    # Remove stray orphaned phantomjs processes. XXX not sure why they happen
    killall -p phantomjs
    service nginx start
fi


