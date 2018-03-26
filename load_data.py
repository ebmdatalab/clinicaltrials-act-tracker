# -*- coding: utf-8 -*-
import logging
import traceback

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
import tempfile
import shutil
import requests
import contextlib
import re
from google.cloud.exceptions import NotFound
from xml.parsers.expat import ExpatError


STORAGE_PREFIX = 'clinicaltrials/'
WORKING_VOLUME = '/mnt/volume-lon1-01/'   # location with at least 10GB space
WORKING_DIR = WORKING_VOLUME + STORAGE_PREFIX

logging.basicConfig(filename='{}data_load.log'.format(WORKING_VOLUME), level=logging.DEBUG)

def raw_json_name():
    date = datetime.datetime.now().strftime('%Y-%m-%d')
    return "raw_clincialtrials_json_{}.csv".format(date)


def postprocessor(path, key, value):
    """Convert key names to something bigquery compatible
    """
    if key.startswith('#') or key.startswith('@'):
        key = key[1:]
    return key, value


def download_and_extract():
    """Clean up from past runs, then download into a temp location and move the
    result into place.
    """
    logging.info("Downloading. This takes at least 30 mins on a fast connection!")
    url = 'https://clinicaltrials.gov/AllPublicXML.zip'

    # download and extract
    container = tempfile.mkdtemp(prefix=STORAGE_PREFIX.rstrip(os.sep), dir=WORKING_VOLUME)
    try:
        data_file = os.path.join(container, "data.zip")
        subprocess.check_call(["wget", "-q", "-O", data_file, url])
        # Can't "wget|unzip" in a pipe because zipfiles have index at end of file.
        with contextlib.suppress(OSError):
            shutil.rmtree(WORKING_DIR)
        subprocess.check_call(["unzip", "-q", "-o", "-d", WORKING_DIR, data_file])
    finally:
        shutil.rmtree(container)


def upload_to_cloud():
    # XXX we should periodically delete old ones of these
    logging.info("Uploading to cloud")
    subprocess.check_call(["gsutil", "cp", "{}{}".format(WORKING_DIR, raw_json_name()), "gs://ebmdatalab/{}".format(STORAGE_PREFIX)])


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
    with contextlib.suppress(NotFound):
        table = client.get_table(table_name)
        table.gcbq_table.delete()

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

        # The call to .run_async_query() might return before results are actually ready.
        # See https://cloud.google.com/bigquery/docs/reference/rest/v2/jobs/query#timeoutMs
        wait_for_job(job)
    t1_exporter = TableExporter(tmp_table, STORAGE_PREFIX + 'test_table-')
    t1_exporter.export_to_storage()

    #with tempfile.NamedTemporaryFile(mode='r+') as f:
    with open('/tmp/clinical_trials.csv', 'w') as f:
        t1_exporter.download_from_storage_and_unzip(f)


if __name__ == '__main__':
    with contextlib.suppress(OSError):
        os.remove("/tmp/clinical_trials.csv")
    try:
        download_and_extract()
        convert_to_json()
        upload_to_cloud()
        convert_and_download()
        env = os.environ.copy()
        with open("/etc/profile.d/fdaaa_staging.sh") as e:
            for k, v in re.findall(r"^export ([A-Z][A-Z0-9_]*)=(\S*)", e.read(), re.MULTILINE):
                env[k] = v
        subprocess.check_call(["/var/www/fdaaa_staging/venv/bin/python", "/var/www/fdaaa_staging/clinicaltrials-act-tracker/clinicaltrials/manage.py", "process_data", "--input-csv=/tmp/clinical_trials.csv", "--settings=frontend.settings"], env=env)
        notify_slack("""Today's data uploaded to FDAAA staging: https://staging-fdaaa.ebmdatalab.net.  Freshly overdue at https://staging-fdaaa.ebmdatalab.net/api/trials/?is_overdue_today=2&is_no_longer_overdue_today=1, freshly no-longer-overdue at https://staging-fdaaa.ebmdatalab.net/api/trials/?is_overdue_today=1&is_no_longer_overdue_today=2. If this looks good, tell ebmbot to 'update fdaaa staging'""")
    except:
        notify_slack("Error in FDAAA import: {}".format(traceback.format_exc()))
        raise
