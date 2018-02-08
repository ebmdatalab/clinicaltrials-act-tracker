from datetime import date
from unittest import mock
import os

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase

from frontend.models import Ranking
from frontend.models import Trial

class DummyResponse(object):
    def __init__(self, content):
        self.content = content
        self.text = str(content)

def dummy_ccgov_results(url):
    sample_results = os.path.join(
        settings.BASE_DIR, 'frontend/tests/fixtures/results_with_qa.html')
    if url.endswith('overdueinqa'):
        with open(sample_results, 'r') as dummy_response:
            return DummyResponse(dummy_response.read())
    return DummyResponse('<html></html>')


class CommandsTestCase(TestCase):
    @mock.patch('requests.get', mock.Mock(side_effect=dummy_ccgov_results))
    @mock.patch('frontend.models.date')
    def test_mycommand(self, datetime_mock):
        " Test my custom command."
        datetime_mock.today = mock.Mock(return_value=date(2018,1,1))

        args = []
        sample_csv = os.path.join(settings.BASE_DIR, 'frontend/tests/fixtures/sample_bq.csv')
        opts = {'input_csv': sample_csv}
        call_command('process_data', *args, **opts)

        reported = Trial.objects.get(registry_id='reported')
        self.assertEqual(reported.status, 'reported')
        self.assertEqual(reported.days_late, 0)

        ongoing = Trial.objects.get(registry_id='ongoing')
        self.assertEqual(ongoing.status, 'ongoing')
        self.assertEqual(ongoing.days_late, None)

        overdue = Trial.objects.get(registry_id='overdue')
        self.assertEqual(overdue.status, 'overdue')
        self.assertEqual(overdue.days_late, 61)

        overdueinqa = Trial.objects.get(registry_id='overdueinqa')
        self.assertEqual(overdueinqa.status, 'qa')
        self.assertEqual(overdueinqa.days_late, 12)
        self.assertEqual(overdueinqa.qa_start_date(), date(2017,11,13))

        overdueingrace = Trial.objects.get(registry_id='overdueingrace')
        self.assertEqual(overdueingrace.status, 'ongoing')
        self.assertEqual(overdueingrace.days_late, 0)


        self.assertEqual(Ranking.objects.first().sponsor, reported.sponsor)
        self.assertEqual(Ranking.objects.count(), 3)
