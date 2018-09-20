"""Integration test for load_data.py script
"""
import csv
import os
import shutil
import tempfile
from datetime import date
from unittest import mock
from django.conf import settings
from django.core.management import call_command
from django.test import TestCase
from django.test.utils import override_settings
from unittest.mock import patch
import pathlib


CMD_ROOT = 'frontend.management.commands.load_data'


def wget_copy_fixture(data_file, url):
    test_zip = os.path.join(
        settings.BASE_DIR, 'frontend/tests/fixtures/data.zip')
    shutil.copy(test_zip, data_file)


class LoadTestCase(TestCase):
    @patch(CMD_ROOT + '.wget_file', side_effect=wget_copy_fixture)
    @patch(CMD_ROOT + '.notify_slack')
    @patch(CMD_ROOT + '.process_data')
    @override_settings(
        STORAGE_PREFIX='clinicaltrials_test/',
        PROCESSING_ENV_PATH=os.path.join(
            settings.BASE_DIR, '../environment-example'),
        PROCESSING_VENV_BIN='',
        PROCESSING_STORAGE_TABLE_NAME='current_raw_json_test',
        WORKING_VOLUME=os.path.join(tempfile.gettempdir(), 'fdaaa_data'),
        WORKING_DIR=os.path.join(tempfile.gettempdir(), 'fdaaa_data', 'work'),
        INTERMEDIATE_CSV_PATH=os.path.join(tempfile.gettempdir(), 'clinical_trials.csv')
    )
    def test_produces_csv(self, process_mock, slack_mock, wget_file_mock):
        fdaaa_web_data = os.path.join(tempfile.gettempdir(), 'fdaaa_data')
        pathlib.Path(fdaaa_web_data).mkdir(exist_ok=True)

        args = []
        opts = {}
        call_command('load_data', *args, **opts)
        expected_csv = os.path.join(
            settings.BASE_DIR, 'frontend/tests/fixtures/expected_trials_data.csv')
        with open(settings.INTERMEDIATE_CSV_PATH) as output_file:
            with open(expected_csv) as expected_file:
                results = sorted(list(csv.reader(output_file)))
                expected = sorted(list(csv.reader(expected_file)))
                self.assertEqual(results, expected)
