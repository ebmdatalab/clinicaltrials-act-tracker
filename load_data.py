# -*- coding: utf-8 -*-
from bigquery import Client
from bigquery import TableExporter
from bigquery import wait_for_job
from bigquery import gen_job_name
import xmltodict
import os
import json
import glob
import datetime
from google.cloud.exceptions import NotFound

STORAGE_PREFIX = 'clinicaltrials/'
WORKING_VOLUME = '/mnt/volume-lon1-01/'   # location with at least 10GB space

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
    print("Downloading. This takes at least 30 mins on a fast connection!")
    url = 'https://clinicaltrials.gov/AllPublicXML.zip'
    # download and extract
    wget_command = "wget -O {}clinicaltrials/data.zip {}".format(WORKING_VOLUME, url)
    os.system("rm -rf {}clinicaltrials/".format(WORKING_VOLUME))
    os.system("%s %s" % (wget_command, url))
    os.system("unzip -o -d {}clinicaltrials/ {}clinicaltrials/data.zip".format(WORKING_VOLUME, WORKING_VOLUME))


def upload_to_cloud():
    # XXX we should periodically delete old ones of these
    os.system("gsutil cp {}  gs://ebmdatalab/{}".format(raw_json_name(), STORAGE_PREFIX))


def convert_to_json():
    dpath = WORKING_VOLUME + 'clinicaltrials/NCT*/'
    files = [x for x in sorted(glob.glob(dpath + '*.xml'))]
    start = datetime.datetime.now()
    completed = 0
    with open(raw_json_name(), 'a') as f2:
        for source in files:
            print("Converting", source)
            with open(source, 'rb') as f:
                f2.write(
                    json.dumps(
                        xmltodict.parse(
                            f,
                            item_depth=0,
                            postprocessor=postprocessor)
                    ) + "\n")

        completed += 1
        if completed % 100 == 0:
            elapsed = datetime.datetime.now() - start
            per_file = elapsed.seconds / completed
            remaining = int(per_file * (len(files) - completed) / 60.0)
            print(remaining, "minutes remaining")



def convert_and_download():
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
    with open('view.sql', 'r') as sql_file:
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
    with open('outfile.csv', 'w') as f:
        t1_exporter.download_from_storage_and_unzip(f)


if __name__ == '__main__':
    try:
        os.remove("data.json")
    except OSError:
        pass
    download_and_extract()
    convert_to_json()
    upload_to_cloud()
    convert_and_download()
    print("""
    Run:
        . /etc/profile.d/fdaaa.sh && ../../venv/bin/python manage.py process_data --input-csv=/tmp/launch.csv --settings=clinicaltrials.settings

    Finally, update NEXT_PLANNED_UPDATE in settings.py and restart the server
    """)
