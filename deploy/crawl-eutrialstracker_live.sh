#!/bin/sh

. /etc/profile.d/eutrialstracker_live.sh

WHEN=`date -d "yesterday 13:00" '+%Y-%m-%d'`

LOG_DIR=/var/log/eutrialstracker_live
mkdir -p $LOG_DIR
LOG_FILE=$LOG_DIR/crawl-$WHEN.log

echo "Crawling up to $WHEN" >>$LOG_FILE 2>&1
echo "=========================" >>$LOG_FILE 2>&1
echo >>$LOG_FILE

cd /var/www/eutrialstracker_live/
. venv/bin/activate
cd euctr-tracker-code/euctr
./manage.py run_crawler 2004-01-01 $WHEN >>$LOG_FILE 2>&1
