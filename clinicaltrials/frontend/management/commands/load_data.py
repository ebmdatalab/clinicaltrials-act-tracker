# -*- coding: utf-8 -*-
import logging
import traceback

from bigquery import Client
from bigquery import StorageClient
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

from django.core.management.base import BaseCommand
from django.conf import settings


STORAGE_PREFIX = 'clinicaltrials/'
WORKING_VOLUME = '/mnt/volume-lon1-01/'   # location with at least 10GB space
WORKING_DIR = WORKING_VOLUME + STORAGE_PREFIX

def raw_json_name():
    date = datetime.datetime.now().strftime('%Y-%m-%d')
    return "raw_clincialtrials_json_{}.csv".format(date)


def postprocessor(path, key, value):
    """Convert key names to something bigquery compatible
    """
    if key.startswith('#') or key.startswith('@'):
        key = key[1:]
    return key, value

def wget_file(target, url):
    subprocess.check_call(["wget", "-q", "-O", target, url])

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
        wget_file(data_file, url)
        # Can't "wget|unzip" in a pipe because zipfiles have index at end of file.
        with contextlib.suppress(OSError):
            shutil.rmtree(WORKING_DIR)
        subprocess.check_call(["unzip", "-q", "-o", "-d", WORKING_DIR, data_file])
        print("unzip -q -o -d {} {}".format(WORKING_DIR, data_file))
    finally:
        shutil.rmtree(container)


def upload_to_cloud():
    # XXX we should periodically delete old ones of these
    logging.info("Uploading to cloud")
    client = StorageClient()
    bucket = client.get_bucket()
    blob = bucket.blob("{}{}".format(STORAGE_PREFIX, raw_json_name()))
    with open(os.path.join(WORKING_DIR, raw_json_name()), 'rb') as f:
        blob.upload_from_file(f)


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
    table_name = settings.PROCESSING_STORAGE_TABLE_NAME
    tmp_table = tmp_client.dataset.table("clincialtrials_tmp_{}".format(gen_job_name()))
    with contextlib.suppress(NotFound):
        table = client.get_table(table_name)
        table.gcbq_table.delete()

    table = client.create_storage_backed_table(
        table_name,
        schema,
        storage_path
    )
    sql_path = os.path.join(
        settings.BASE_DIR, 'frontend/view.sql')
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


def get_env(path):
    env = os.environ.copy()
    with open(path) as e:
        for k, v in re.findall(r"^export ([A-Z][A-Z0-9_]*)=(\S*)", e.read(), re.MULTILINE):
            env[k] = v
    return env

def process_data():
    # XXX no need to do this: we can call the command via python
    # rather than the shell, now we are a command too.
    subprocess.check_call(
        [
            "{}python".format(settings.PROCESSING_VENV_BIN),
            "{}/manage.py".format(settings.BASE_DIR),
            "process_data",
            "--input-csv=/tmp/clinical_trials.csv",
            "--settings=frontend.settings"
        ],
        env=get_env(settings.PROCESSING_ENV_PATH))
    notify_slack("""Today's data uploaded to FDAAA staging: https://staging-fdaaa.ebmdatalab.net.  If this looks good, tell ebmbot to 'update fdaaa staging'""")


class Command(BaseCommand):
    help = '''Generate a CSV that can be consumed by the `process_data` command, and run that command
    '''

    def handle(self, *args, **options):
        with contextlib.suppress(OSError):
            os.remove("/tmp/clinical_trials.csv")
        try:
            download_and_extract()
            convert_to_json()
            upload_to_cloud()
            convert_and_download()
            process_data()
        except:
            notify_slack("Error in FDAAA import: {}".format(traceback.format_exc()))
            raise
