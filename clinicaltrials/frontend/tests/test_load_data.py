"""Integration test for load_data.py script
"""
import csv
import os
import shutil
from datetime import date
from unittest import mock
from django.conf import settings
from django.core.management import call_command
from django.test import TestCase
from django.test.utils import override_settings
from unittest.mock import patch
import pathlib


CMD_ROOT = 'frontend.management.commands.load_data'

class LoadTestCase(TestCase):

    @patch(CMD_ROOT + '.wget_file')
    @patch(CMD_ROOT + '.tempfile')
    @patch(CMD_ROOT + '.notify_slack')
    @patch('frontend.settings')
    @patch(CMD_ROOT + '.process_data')
    @patch(CMD_ROOT + '.WORKING_VOLUME', '/tmp/')
    @patch(CMD_ROOT + '.WORKING_DIR', '/tmp/clinicaltrials_test/')
    @patch(CMD_ROOT + '.STORAGE_PREFIX', 'clinicaltrials_test/')
    @override_settings(PROCESSING_ENV_PATH=os.path.join(
        settings.BASE_DIR, '../environment-example'))
    @override_settings(PROCESSING_VENV_BIN='')
    @override_settings(PROCESSING_STORAGE_TABLE_NAME='current_raw_json_test')
    def test_produces_csv(self, settings_mock, process_mock, slack_mock, tempfile_mock, wget_file_mock):
        test_zip = os.path.join(
            settings.BASE_DIR, 'frontend/tests/fixtures/data.zip')
        fdaaa_web_data = '/tmp/fdaaa_data/'
        pathlib.Path(fdaaa_web_data).mkdir(exist_ok=True)
        tempfile_mock.mkdtemp.return_value = fdaaa_web_data
        shutil.copy(test_zip, fdaaa_web_data)
        args = []
        opts = {}
        call_command('load_data', *args, **opts)
        with open('/tmp/clinical_trials.csv') as f:
            results = sorted(list(csv.reader(f)))
            self.assertEqual(len(results), 3)
            self.assertEqual(results[1][0], 'NCT03456076')
