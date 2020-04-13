# -*- coding: utf-8 -*-
import os
import requests
import traceback
from frontend.management.commands.process_data import Command as ProcessCommand
from django.core.management.base import BaseCommand
from ctconvert import create_instance


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


def convert_data():
    # This blocks until the compute instance stops running, and raises
    # an exception if its startup script finished in an error or
    # unknown state
    create_instance.main(
        "ebmdatalab", "europe-west2-a", "ctgov-converter", wait=True)


def process_data():
    cmd = ProcessCommand()
    cmd.handle(
        input_csv=('https://storage.googleapis.com/ebmdatalab/clinicaltrials/'
                   'clinical_trials.csv'))


class Command(BaseCommand):
    help = ''' Generate a CSV that can be consumed by the `process_data` command,
    and run that command '''

    def handle(self, *args, **options):
        try:
            convert_data()
            process_data()
            notify_slack("Successful FDAAA import")
        except:
            notify_slack("Error in FDAAA import: {}".format(traceback.format_exc()))
            raise
