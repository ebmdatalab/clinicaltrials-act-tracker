# -*- coding: utf-8 -*-
import logging
import sys
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


logger = logging.getLogger(__name__)


def raw_json_name():
    date = datetime.datetime.now().strftime('%Y-%m-%d')
    return "raw_clincialtrials_json_{}.csv".format(date)


def postprocessor(path, key, value):
    """Convert key names to something bigquery compatible
    """
    if key.startswith('#') or key.startswith('@'):
        key = key[1:]
    if key == 'clinical_results':
        # Arbitrarily long field that we don't need, see #179
        value = {'truncated_by_postprocessor': True}
    return key, value


def wget_file(target, url):
    subprocess.check_call(["wget", "-q", "-O", target, url])


def download_and_extract():
    """Clean up from past runs, then download into a temp location and move the
    result into place.
    """
    logger.info("Downloading. This takes at least 30 mins on a fast connection!")
    url = 'https://clinicaltrials.gov/AllPublicXML.zip'

    # download and extract
    container = tempfile.mkdtemp(
        prefix=settings.STORAGE_PREFIX, dir=settings.WORKING_VOLUME)
    try:
        data_file = os.path.join(container, "data.zip")
        wget_file(data_file, url)
        # Can't "wget|unzip" in a pipe because zipfiles have index at end of file.
        with contextlib.suppress(OSError):
            shutil.rmtree(settings.WORKING_DIR)
        subprocess.check_call(["unzip", "-q", "-o", "-d", settings.WORKING_DIR, data_file])
    finally:
        shutil.rmtree(container)


def upload_to_cloud():
    # XXX we should periodically delete old ones of these
    logger.info("Uploading to cloud")
    client = StorageClient()
    bucket = client.get_bucket()
    blob = bucket.blob(
        "{}/{}".format(settings.STORAGE_PREFIX, raw_json_name()),
        chunk_size=1024*1024
    )
    with open(os.path.join(settings.WORKING_DIR, raw_json_name()), 'rb') as f:
        blob.upload_from_file(f)


def notify_slack(message):
    """Posts the message to #general
    """
    # Set the webhook_url to the one provided by Slack when you create
    # the webhook at
    # https://my.slack.com/services/new/incoming-webhook/
    webhook_url = settings.SLACK_GENERAL_POST_KEY

    if webhook_url is None:
        return

    slack_data = {'text': message}

    response = requests.post(webhook_url, json=slack_data)
    if response.status_code != 200:
        raise ValueError(
            'Request to slack returned an error %s, the response is:\n%s'
            % (response.status_code, response.text)
        )


def convert_to_json():
    logger.info("Converting to JSON...")
    dpath = os.path.join(settings.WORKING_DIR, 'NCT*/')
    files = [x for x in sorted(glob.glob(dpath + '*.xml'))]
    start = datetime.datetime.now()
    completed = 0
    with open(os.path.join(settings.WORKING_DIR, raw_json_name()), 'w') as f2:
        for source in files:
            logger.info("Converting %s", source)
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
                    logger.warn("Unable to parse %s", source)

        completed += 1
        if completed % 100 == 0:
            elapsed = datetime.datetime.now() - start
            per_file = elapsed.seconds / completed
            remaining = int(per_file * (len(files) - completed) / 60.0)
            logger.info("%s minutes remaining", remaining)



def convert_and_download():
    logger.info("Executing SQL in cloud and downloading results...")
    storage_path = os.path.join(settings.STORAGE_PREFIX, raw_json_name())
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
        job = table.gcbq_client.run_async_query(
            gen_job_name(), sql_file.read().format(table_name=table_name))
        job.destination = tmp_table
        job.use_legacy_sql = False
        job.write_disposition = 'WRITE_TRUNCATE'
        job.begin()

        # The call to .run_async_query() might return before results are actually ready.
        # See https://cloud.google.com/bigquery/docs/reference/rest/v2/jobs/query#timeoutMs
        wait_for_job(job)


    t1_exporter = TableExporter(tmp_table, settings.STORAGE_PREFIX + '/' + 'test_table-')
    t1_exporter.export_to_storage()

    with open(settings.INTERMEDIATE_CSV_PATH, 'w') as f:
        t1_exporter.download_from_storage_and_unzip(f)


def get_env(path):
    """Terrible hack to bridge using env vars to having settings files."""
    if not path: return {}
    env = os.environ.copy()
    with open(path) as e:
        for k, v in re.findall(r"^export ([A-Z][A-Z0-9_]*)=(\S*)", e.read(), re.MULTILINE):
            env[k] = v
    return env


def process_data():
    # TODO no need to call via shell any more (now we are also a command)
    try:
        subprocess.check_output(
            [
                shutil.which("python"),
                "{}/manage.py".format(settings.BASE_DIR),
                "process_data",
                "--input-csv={}".format(settings.INTERMEDIATE_CSV_PATH),
                "--settings=frontend.settings"
            ],
            stderr=subprocess.STDOUT,
            env=get_env(settings.PROCESSING_ENV_PATH))
        notify_slack("Today's data uploaded to FDAAA staging: "
                     "https://staging-fdaaa.ebmdatalab.net.  "
                     "If this looks good, tell ebmbot to "
                     "'@ebmbot fdaaa deploy'""")
    except subprocess.CalledProcessError as e:
        notify_slack("Error in FDAAA import: command `{}` "
                     "failed with error code {} "
                     "and output {}".format(
                         e.cmd, e.returncode, e.output))
        sys.exit(1)


class Command(BaseCommand):
    help = '''Generate a CSV that can be consumed by the `process_data` command, and run that command
    '''

    def handle(self, *args, **options):
        with contextlib.suppress(OSError):
            os.remove(settings.INTERMEDIATE_CSV_PATH)
        try:
            download_and_extract()
            convert_to_json()
            upload_to_cloud()
            convert_and_download()
            process_data()
        except:
            notify_slack("Error in FDAAA import: {}".format(traceback.format_exc()))
            raise
