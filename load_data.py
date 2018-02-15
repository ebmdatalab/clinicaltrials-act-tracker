# -*- coding: utf-8 -*-
import xmltodict
import os
import json
import glob
import datetime

def handle_item(path, item):
    with open('data.json', 'a') as f2:
        import pdb; pdb.set_trace()

        f2.write(json.dumps(item) + "\n")
    return True

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
    wget_command = 'wget -O /mnt/database/clinicaltrials/data.zip'
    os.system('%s %s' % (wget_command, url))
    os.system('unzip -d /mnt/database/clinicaltrials/ /mnt/database/clinicaltrials/data.zip')


def upload_to_cloud():
    os.system("gsutil cp data.json  gs://ebmdatalab/clinicaltrials/")


def convert_to_json():
    dpath = '/mnt/database/clinicaltrials/NCT*/'
    files = [x for x in sorted(glob.glob(dpath + '*.xml'))]
    start = datetime.datetime.now()
    completed = 0
    with open('data.json', 'a') as f2:
        for source in files:
            print("Converting", source)
            with open(source, 'rb') as f:
                f2.write(
                    json.dumps(
                        xmltodict.parse(
                            f,
                            item_depth=0,
                            item_callback=handle_item,
                            postprocessor=postprocessor)
                    ) + "\n")

        completed += 1
        if completed % 100 == 0:
            elapsed = datetime.datetime.now() - start
            per_file = elapsed.seconds / completed
            remaining = int(per_file * (len(files) - completed) / 60.0)
            print(remaining, "minutes remaining")


if __name__ == '__main__':
    try:
        os.remove("data.json")
    except OSError:
        pass
    download_and_extract()
    convert_to_json()
    upload_to_cloud()
    print("""
    Now create a new table in CSV format in the BigQuery interface,
    with `gs://ebmdatalab/pubmed/data.json` as the `Location`, and
    somethingsomething wierd like `þ` as the delimiter.  This uses
    Cloud Storage as an "external table" which is slow, but allows us
    to update the source following the above steps more easily.  You
    have to redo this every time you load data, or you get wierd
    effects from BigQuery.""")
    print("""
    Then run `website_data_view` in BigQuery, save the results to a table, download as a CSV, and run

        . /etc/profile.d/fdaaa_staging.sh && ../../venv/bin/python python manage.py process_data --csv=/path/to/csv` --settings=clinicaltrials.settings

    Finally, update NEXT_PLANNED_UPDATE in settings.py and restart the server
    """)
