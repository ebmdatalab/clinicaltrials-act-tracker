# -*- coding: utf-8 -*-
import logging
from bigquery import Client
from bigquery import TableExporter
from bigquery import wait_for_job
from bigquery import gen_job_name
import xmltodict
import os
import subprocess
import json
import glob
import datetime
import requests
from google.cloud.exceptions import NotFound
from xml.parsers.expat import ExpatError


STORAGE_PREFIX = 'clinicaltrials/'
WORKING_VOLUME = '/mnt/volume-lon1-01/'   # location with at least 10GB space
WORKING_DIR = WORKING_VOLUME + STORAGE_PREFIX

logging.basicConfig(filename='{}data_load.log'.format(WORKING_VOLUME), level=logging.DEBUG)

def raw_json_name():
    date = datetime.datetime.now().strftime('%Y-%m-%d')
    return "raw_clincialtrials_json_{}.csv".format(date)


def run(cmd):
    completed = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if completed.returncode > 0:
        raise RuntimeError(completed.stderr)


def postprocessor(path, key, value):
    """Convert key names to something bigquery compatible
    """
    if key.startswith('#') or key.startswith('@'):
        key = key[1:]
    return key, value


def download_and_extract():
    logging.info("Downloading. This takes at least 30 mins on a fast connection!")
    url = 'https://clinicaltrials.gov/AllPublicXML.zip'
    # download and extract
    wget_command = "wget -O {}data.zip {}".format(WORKING_DIR, url)
    run("rm -rf {}*".format(WORKING_DIR))
    run("%s %s" % (wget_command, url))
    run("unzip -o -d {} {}data.zip".format(WORKING_DIR, WORKING_DIR))


def upload_to_cloud():
    # XXX we should periodically delete old ones of these
    logging.info("Uploading to cloud")
    run("gsutil cp {}{}  gs://ebmdatalab/{}".format(WORKING_DIR, raw_json_name(), STORAGE_PREFIX))


def notify_slack(message):
    """Posts the message to #general
    """
    # Set the webhook_url to the one provided by Slack when you create
    # the webhook at
    # https://my.slack.com/services/new/incoming-webhook/
    webhook_url = os.environ['SLACK_GENERAL_POST_KEY']
    slack_data = {'text': message}

    response = requests.post(webhook_url, json=slack_data)
    if response.status_code != 200:
        raise ValueError(
            'Request to slack returned an error %s, the response is:\n%s'
            % (response.status_code, response.text)
        )


def convert_to_json():
    logging.info("Converting to JSON...")
    dpath = WORKING_DIR + 'NCT*/'
    files = [x for x in sorted(glob.glob(dpath + '*.xml'))]
    start = datetime.datetime.now()
    completed = 0
    with open(WORKING_DIR + raw_json_name(), 'a') as f2:
        for source in files:
            logging.info("Converting %s", source)
            with open(source, 'rb') as f:
                try:
                    f2.write(
                        json.dumps(
                            xmltodict.parse(
                                f,
                                item_depth=0,
                                postprocessor=postprocessor)
                        ) + "\n")
                except ExpatError:
                    logging.warn("Unable to parse %s", source)

        completed += 1
        if completed % 100 == 0:
            elapsed = datetime.datetime.now() - start
            per_file = elapsed.seconds / completed
            remaining = int(per_file * (len(files) - completed) / 60.0)
            logging.info("%s minutes remaining", remaining)



def convert_and_download():
    logging.info("Executing SQL in cloud and downloading results...")
    storage_path = STORAGE_PREFIX + raw_json_name()
    schema = [
        {'name': 'json', 'type': 'string'},
    ]
    client = Client('clinicaltrials')
    tmp_client = Client('tmp_eu')
    table_name = 'current_raw_json'
    tmp_table = tmp_client.dataset.table("clincialtrials_tmp_{}".format(gen_job_name()))
    try:
        table = client.get_table(table_name)
        table.gcbq_table.delete()
    except NotFound:
        pass

    table = client.create_storage_backed_table(
        table_name,
        schema,
        storage_path
    )
    sql_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'view.sql')
    with open(sql_path, 'r') as sql_file:
        job = table.gcbq_client.run_async_query(gen_job_name(), sql_file.read())
        job.destination = tmp_table
        job.use_legacy_sql = False
        job.write_disposition = 'WRITE_TRUNCATE'
        job.begin()

        # The call to .run() might return before results are actually ready.
        # See https://cloud.google.com/bigquery/docs/reference/rest/v2/jobs/query#timeoutMs
        wait_for_job(job)
    t1_exporter = TableExporter(tmp_table, STORAGE_PREFIX + 'test_table-')
    t1_exporter.export_to_storage()

    #with tempfile.NamedTemporaryFile(mode='r+') as f:
    with open('/tmp/clinical_trials.csv', 'w') as f:
        t1_exporter.download_from_storage_and_unzip(f)


if __name__ == '__main__':
    try:
        os.remove("/tmp/clinical_trials.csv")
    except OSError:
        pass
    download_and_extract()
    convert_to_json()
    upload_to_cloud()
    convert_and_download()
    run(". /etc/profile.d/fdaaa_staging.sh &&  /var/www/fdaaa_staging/venv/bin/python /var/www/fdaaa_staging/clinicaltrials-act-tracker/clinicaltrials/manage.py process_data --input-csv=/tmp/clinical_trials.csv --settings=frontend.settings")
    notify_slack("""Today's data uploaded to FDAAA staging: https://staging-fdaaa.ebmdatalab.net.

If this looks good, a dev should run the following on smallweb1:

```. /etc/profile.d/fdaaa.sh &&  /var/www/fdaaa/venv/bin/python /var/www/fdaaa/clinicaltrials-act-tracker/clinicaltrials/manage.py process_data --input-csv=/tmp/clinical_trials.csv --settings=frontend.settings
```
""")
