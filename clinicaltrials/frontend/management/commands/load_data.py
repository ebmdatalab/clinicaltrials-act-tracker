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
import gzip
import datetime
import tempfile
import shutil
import requests
import contextlib
import os
from bs4 import BeautifulSoup
import xmltodict
import json
from datetime import date
from datetime import datetime
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import csv
import re
from google.cloud.exceptions import NotFound
from xml.parsers.expat import ExpatError

from django.core.management.base import BaseCommand
from django.conf import settings


logger = logging.getLogger(__name__)

def raw_json_name():
    date = datetime.now().strftime('%Y-%m-%d')
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
        prefix=settings.STORAGE_PREFIX.rstrip(os.sep), dir=settings.WORKING_VOLUME)
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
        "{}{}".format(settings.STORAGE_PREFIX, raw_json_name()),
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
    webhook_url = os.environ['SLACK_GENERAL_POST_KEY']
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
    start = datetime.now()
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
            elapsed = datetime.now() - start
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


    t1_exporter = TableExporter(tmp_table, settings.STORAGE_PREFIX + 'test_table-')
    t1_exporter.export_to_storage()

    with open(settings.INTERMEDIATE_CSV_PATH, 'w') as f:
        t1_exporter.download_from_storage_and_unzip(f)


def get_env(path):
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
                "{}python".format(settings.PROCESSING_VENV_BIN),
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


###################################
# Helper functions for CSV assenbly
###################################

def is_covered_phase(phase):
    return phase in [
        "Phase 1/Phase 2",
        "Phase 2",
        "Phase 2/Phase 3",
        "Phase 3",
        "Phase 4",
        "N/A",
    ]


def is_not_withdrawn(study_status):
    return study_status != "Withdrawn"


def is_interventional(study_type):
    return study_type == "Interventional"


def is_covered_intervention(intervention_type_list):
    covered_intervention_type = [
        "Drug",
        "Device",
        "Biological",
        "Genetic",
        "Radiation",
        "Combination Prodcut",
        "Diagnostic Test",
    ]
    a_set = set(covered_intervention_type)
    b_set = set(intervention_type_list)
    if a_set & b_set:
        return True
    else:
        return False


def is_not_device_feasibility(primary_purpose):
    return primary_purpose != "Device Feasibility"


def is_fda_reg(fda_reg_drug, fda_reg_device):
    if fda_reg_drug == "Yes" or fda_reg_device == "Yes":
        return True
    else:
        return False


def is_old_fda_regulated(is_fda_regulated, fda_reg_drug, fda_reg_device):
    if (
        fda_reg_drug is None and fda_reg_device is None
    ) and is_fda_regulated is not False:
        return True
    else:
        return False


def has_us_loc(locs):
    us_locs = [
        "United States",
        "American Samoa",
        "Guam",
        "Northern Mariana Islands",
        "Puerto Rico",
        "Virgin Islands (U.S.)",
    ]
    for us_loc in us_locs:
        if us_loc in locs:
            return True
    return False


def dict_or_none(data, keys):
    for k in keys:
        try:
            data = data[k]
        except KeyError:
            return None
    return json.dumps(data, separators=(',', ':'))


# Some dates on clinicaltrials.gov are only Month-Year not
# Day-Month-Year.  When this happens, we assign them to the last day
# of the month so our "results due" assessments are conservative
def str_to_date(datestr):
    is_defaulted_date = False
    if datestr is not None:
        try:
            parsed_date = datetime.strptime(datestr.text, "%B %d, %Y").date()
        except ValueError:
            parsed_date = (
                datetime.strptime(datestr.text, "%B %Y").date()
                + relativedelta(months=+1)
                - timedelta(days=1)
            )
            is_defaulted_date = True
    else:
        parsed_date = None
    return (parsed_date, is_defaulted_date)


def t(textish):
    if textish is None:
        return None
    return textish.text


def does_it_exist(dataloc):
    if dataloc is None:
        return False
    else:
        return True


def convert_bools_to_ints(row):
    for k, v in row.items():
        if v is True:
            v = 1
            row[k] = v
        elif v is False:
            v = 0
            row[k] = v
    return row


def convert_to_csv():
    headers = [
        "nct_id",
        "act_flag",
        "included_pact_flag",
        "has_results",
        "pending_results",
        "pending_data",
        "has_certificate",
        "results_due",
        "start_date",
        "available_completion_date",
        "used_primary_completion_date",
        "defaulted_pcd_flag",
        "defaulted_cd_flag",
        "results_submitted_date",
        "last_updated_date",
        "certificate_date",
        "phase",
        "enrollment",
        "location",
        "study_status",
        "study_type",
        "primary_purpose",
        "sponsor",
        "sponsor_type",
        "collaborators",
        "exported",
        "fda_reg_drug",
        "fda_reg_device",
        "is_fda_regulated",
        "url",
        "title",
        "official_title",
        "brief_title",
        "discrep_date_status",
        "late_cert",
        "defaulted_date",
        "condition",
        "condition_mesh",
        "intervention",
        "intervention_mesh",
        "keywords",
    ]

    cs = "clinical_study"
    effective_date = date(2017, 1, 18)

    # This is a snapshot of CT.gov at a time when it included FDA
    # regulation metadata
    fda_reg_dict = {}
    with gzip.open(
            os.path.join(settings.BASE_DIR,
                         'frontend', 'management', 'commands',
                         'fdaaa_regulatory_snapshot.csv.gz'), 'rt') as old_fda_reg:
        reader = csv.DictReader(old_fda_reg)
        for d in reader:
            fda_reg_dict[d["nct_id"]] = d["is_fda_regulated"]


    with open(settings.INTERMEDIATE_CSV_PATH, 'w', newline="", encoding="utf-8") as test_csv:
        writer = csv.DictWriter(test_csv, fieldnames=headers)
        writer.writeheader()
        dpath = os.path.join(settings.WORKING_DIR, 'NCT*/')
        files = [x for x in sorted(glob.glob(dpath + '*.xml'))]

        for xml_filename in files:
            with open(xml_filename) as raw_xml:
                soup = BeautifulSoup(raw_xml, "xml")
            with open(xml_filename) as xml_to_json:
                parsed_json = xmltodict.parse(xml_to_json.read())

            td = {}

            td["nct_id"] = t(soup.nct_id)

            td["study_type"] = t(soup.study_type)

            td["has_certificate"] = does_it_exist(soup.disposition_first_submitted)

            td["phase"] = t(soup.phase)

            td["fda_reg_drug"] = t(soup.is_fda_regulated_drug)

            td["fda_reg_device"] = t(soup.is_fda_regulated_device)

            td["primary_purpose"] = t(soup.find("primary_purpose"))

            try:
                if fda_reg_dict[td["nct_id"]] == "false":
                    td["is_fda_regulated"] = False
                elif fda_reg_dict[td["nct_id"]] == "true":
                    td["is_fda_regulated"] = True
                else:
                    td["is_fda_regulated"] = None
            except KeyError:
                td["is_fda_regulated"] = None
            td["study_status"] = t(soup.overall_status)

            td["start_date"] = (str_to_date(soup.start_date))[0]

            primary_completion_date, td["defaulted_pcd_flag"] = str_to_date(
                soup.primary_completion_date
            )

            completion_date, td["defaulted_cd_flag"] = str_to_date(
                soup.completion_date
            )

            if not primary_completion_date and not completion_date:
                td["available_completion_date"] = None
            elif completion_date and not primary_completion_date:
                td["available_completion_date"] = completion_date
                td["used_primary_completion_date"] = False
            else:
                td["available_completion_date"] = primary_completion_date
                td["used_primary_completion_date"] = True

            if (
                is_interventional(td["study_type"])
                and is_fda_reg(td["fda_reg_drug"], td["fda_reg_device"])
                and is_covered_phase(td["phase"])
                and is_not_device_feasibility(td["primary_purpose"])
                and td["start_date"] >= effective_date
                and is_not_withdrawn(td["study_status"])
            ):
                td["act_flag"] = True
            else:
                td["act_flag"] = False

            intervention_type_field = soup.find_all("intervention_type")
            trial_intervention_types = []
            for tag in intervention_type_field:
                trial_intervention_types.append(tag.get_text())

            locs = t(soup.location_countries)

            if (
                is_interventional(td["study_type"])
                and is_covered_intervention(trial_intervention_types)
                and is_covered_phase(td["phase"])
                and is_not_device_feasibility(td["primary_purpose"])
                and td["available_completion_date"] >= effective_date
                and td["start_date"] < effective_date
                and is_not_withdrawn(td["study_status"])
                and (
                    is_fda_reg(td["fda_reg_drug"], td["fda_reg_device"])
                    or is_old_fda_regulated(
                        td["is_fda_regulated"],
                        td["fda_reg_drug"],
                        td["fda_reg_device"],
                    )
                )
                and has_us_loc(locs)
            ):
                old_pact_flag = True
            else:
                old_pact_flag = False

            if (
                is_interventional(td["study_type"])
                and is_fda_reg(td["fda_reg_drug"], td["fda_reg_device"])
                and is_covered_phase(td["phase"])
                and is_not_device_feasibility(td["primary_purpose"])
                and td["start_date"] < effective_date
                and td["available_completion_date"] >= effective_date
                and is_not_withdrawn(td["study_status"])
            ):
                new_pact_flag = True
            else:
                new_pact_flag = False

            if old_pact_flag == True or new_pact_flag == True:
                td["included_pact_flag"] = True
            else:
                td["included_pact_flag"] = False

            td["location"] = dict_or_none(parsed_json, [cs, "location_countries"])

            td["has_results"] = does_it_exist(soup.results_first_submitted)

            td["pending_results"] = does_it_exist(soup.pending_results)

            td["pending_data"] = dict_or_none(parsed_json, [cs, "pending_results"])

            if (
                (td["act_flag"] == True or td["included_pact_flag"] == True)
                and date.today()
                > td["available_completion_date"]
                + relativedelta(years=1)
                + timedelta(days=30)
                and (
                    td["has_certificate"] == 0
                    or (
                        date.today()
                        > td["available_completion_date"]
                        + relativedelta(years=3)
                        + timedelta(days=30)
                    )
                )
            ):
                td["results_due"] = True
            else:
                td["results_due"] = False

            td["results_submitted_date"] = (
                str_to_date(soup.results_first_submitted)
            )[0]

            td["last_updated_date"] = (str_to_date(soup.last_update_submitted))[0]

            td["certificate_date"] = (
                str_to_date(soup.disposition_first_submitted)
            )[0]

            td["enrollment"] = t(soup.enrollment)

            td["sponsor"] = t(soup.sponsors.lead_sponsor.agency)

            td["sponsor_type"] = t(soup.sponsors.lead_sponsor.agency_class)

            td["collaborators"] = dict_or_none(
                parsed_json, [cs, "sponsors", "collaborator"]
            )

            td["exported"] = t(soup.oversight_info.is_us_export)

            td["url"] = t(soup.url)

            td["official_title"] = t(soup.official_title)

            td["brief_title"] = t(soup.brief_title)

            td["title"] = td["official_title"] or td["brief_title"]

            if td["official_title"] is not None:
                td["title"] = td["official_title"]
            elif td["official_title"] is None and td["brief_title"] is not None:
                td["title"] = td["brief_title"]
            else:
                td["title"] = None

            # add this to "if" statement after testing: 'and completion_date is not null')
            not_ongoing = [
                "Unknown status",
                "Active, not recruiting",
                "Not yet recruiting",
                "Enrolling by invitation",
                "Suspended",
                "Recruiting",
            ]
            if (
                (
                    primary_completion_date < date.today()
                    or primary_completion_date is None
                )
                and completion_date < date.today()
                and td["study_status"] in not_ongoing
            ):
                td["discrep_date_status"] = True
            else:
                td["discrep_date_status"] = False

            if td["certificate_date"] is not None:
                if td["certificate_date"] > (
                    td["available_completion_date"] + relativedelta(years=1)
                ):
                    td["late_cert"] = True
                else:
                    td["late_cert"] = False
            else:
                td["late_cert"] = False

            if (
                (
                    td["used_primary_completion_date"] == True
                    and td["defaulted_pcd_flag"] == True
                )
                or td["used_primary_completion_date"] == False
                and td["defaulted_cd_flag"] == True
            ):
                td["defaulted_date"] = True
            else:
                td["defaulted_date"] = False

            td["condition"] = dict_or_none(parsed_json, [cs, "condition"])

            td["condition_mesh"] = dict_or_none(
                parsed_json, [cs, "condition_browse"]
            )

            td["intervention"] = dict_or_none(parsed_json, [cs, "intervention"])

            td["intervention_mesh"] = dict_or_none(
                parsed_json, [cs, "intervention_browse"]
            )

            td["keywords"] = dict_or_none(parsed_json, [cs, "keyword"])

            writer.writerow(convert_bools_to_ints(td))


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
            convert_to_csv()
            process_data()
        except:
            notify_slack("Error in FDAAA import: {}".format(traceback.format_exc()))
            raise
