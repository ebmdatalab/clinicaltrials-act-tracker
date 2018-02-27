from datetime import date
from unittest.mock import patch
from unittest.mock import Mock

from django.test import TestCase

from rest_framework.test import APIClient

from frontend.tests.common import makeTrial
from frontend.management.commands.process_data import set_current
from frontend.models import Sponsor




class ApiResultsTestCase(TestCase):
    maxDiff = 6000
    @patch('frontend.trial_computer.date')
    def setUp(self, datetime_mock):
        datetime_mock.today = Mock(return_value=date(2017,1,31))
        self.sponsor = Sponsor.objects.create(name="Sponsor 1")
        self.due_trial = makeTrial(
            self.sponsor,
            results_due=True,
            has_results=False)
        self.reported_trial = makeTrial(
            self.sponsor,
            results_due=True,
            has_results=True,
            reported_date=date(2016,12,1))
        set_current()


    def test_trial_results(self):
        client = APIClient()
        response = client.get('/api/trials/', format='json').json()
        self.assertEqual(response['previous'], None)
        self.assertEqual(response['recordsTotal'], 2)
        self.assertEqual(response['next'], None)
        self.assertEqual(response['recordsFiltered'], 2)
        self.assertEqual(
            response['results'][0],
            {
                "has_results": False,
                "status": "overdue",
                "registry_id": "id_1",
                "has_exemption": False,
                "start_date": "2015-01-01",
                "sponsor_name": "Sponsor 1",
                "completion_date": "2016-01-01",
                "publication_url": "http://bar.com/1",
                "results_due": True,
                "sponsor_slug": "sponsor-1",
                "is_pact": False,
                "days_late": 31,
                "title": "Trial 1"
            })

    def test_trial_filter(self):
        client = APIClient()
        response = client.get('/api/trials/', {'has_results': True}, format='json').json()
        self.assertEqual(response['recordsFiltered'], 1)
        self.assertEqual(response['results'][0]['title'], self.reported_trial.title)

        response = client.get('/api/trials/', {'status': 'overdue'}, format='json').json()
        self.assertEqual(response['recordsFiltered'], 1)
        self.assertEqual(response['results'][0]['title'], self.due_trial.title)

        response = client.get('/api/trials/', {'status': 'xxx'}, format='json').json()
        self.assertEqual(response['recordsFiltered'], 0)

        response = client.get('/api/trials/', {'search[value]': 'xxx'}, format='json').json()
        self.assertEqual(response['recordsFiltered'], 0)

        response = client.get('/api/trials/', {'search[value]': 'Trial'}, format='json').json()
        self.assertEqual(response['recordsFiltered'], 2)

    def test_trial_ordering(self):
        client = APIClient()
        response = client.get('/api/trials/', {
            'order[0][column]': 3,
            'order[0][dir]': 'desc',
            'columns[3][data]': 'title',
            'columns[3][name]': 'title'
        }, format='json').json()
        self.assertEqual(response['results'][0]['title'], 'Trial 2')

    def test_sponsor_results(self):
        client = APIClient()
        response = client.get('/api/sponsors/', format='json').json()
        self.assertEqual(response['previous'], None)
        self.assertEqual(response['recordsTotal'], 1)
        self.assertEqual(response['next'], None)
        self.assertEqual(response['recordsFiltered'], 1)
        self.assertEqual(
            response['results'][0],
            {'name': 'Sponsor 1',
             'num_trials': 2,
             'slug': 'sponsor-1',
             'is_industry_sponsor': None,
             'updated_date': '2018-02-27'}
        )

    def test_sponsor_filter(self):
        client = APIClient()
        response = client.get('/api/sponsors/', {'num_trials_0': 0}, format='json').json()
        self.assertEqual(response['recordsFiltered'], 1)
        self.assertEqual(response['results'][0]['slug'], self.sponsor.slug)

        response = client.get('/api/sponsors/', {'num_trials_0': 3}, format='json').json()
        self.assertEqual(response['recordsFiltered'], 0)

    def test_ranking_results(self):
        client = APIClient()
        response = client.get('/api/rankings/', format='json').json()
        self.assertEqual(response['previous'], None)
        self.assertEqual(response['recordsTotal'], 1)
        self.assertEqual(response['next'], None)
        self.assertEqual(response['recordsFiltered'], 1)
        self.assertEqual(
            response['results'][0],
            {'date': '2018-02-27',
             'total': 2,
             'sponsor_name': 'Sponsor 1',
             'is_industry_sponsor': None,
             'sponsor_slug': 'sponsor-1',
             'due': 2,
             'rank': 1,
             'reported': 1,
             'percentage': 50})

    def test_ranking_filter(self):
        client = APIClient()
        response = client.get('/api/rankings/', {'percentage__gte': 50}, format='json').json()
        self.assertEqual(response['recordsFiltered'], 1)
        self.assertEqual(response['results'][0]['sponsor_slug'], self.sponsor.slug)

        response = client.get('/api/rankings/', {'percentage__lte': 49}, format='json').json()
        self.assertEqual(response['recordsFiltered'], 0)


    def test_performance_results(self):
        client = APIClient()
        response = client.get('/api/performance/', format='json').json()
        self.assertEqual(
            response,
            {
                'due': 2,
                'reported': 1,
                'days_late': 1,
                'fines_str': '$11,569'}
        )
