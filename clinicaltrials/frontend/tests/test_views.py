import csv
import io
import os
from datetime import date
from unittest.mock import patch
from unittest.mock import Mock

from django.conf import settings
from django.test import TestCase
from django.test import Client

from rest_framework.test import APIClient

from frontend.tests.common import makeTrial
from frontend.management.commands.process_data import set_current_rankings
from frontend.models import Sponsor
from frontend.models import Trial


class FrontendTestCase(TestCase):
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
        set_current_rankings()

    def test_index(self):
        client = Client()
        response = client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_rankings(self):
        client = Client()
        response = client.get('/rankings/')
        self.assertEqual(response.status_code, 200)

    def test_sponsor(self):
        client = Client()
        response = client.get('/sponsor/sponsor-1/')
        self.assertEqual(response.status_code, 200)
        context = response.context
        self.assertEqual(context['sponsor'], self.sponsor)
        self.assertEqual(
            context['status_choices'],
            [('overdue', 'Overdue'), ('reported', 'Reported')])
        self.assertEqual(context['fine'], 11569)
        self.assertIn(self.sponsor.name, context['title'])

    def test_trials(self):
        client = Client()
        response = client.get('/trials/')
        context = response.context
        self.assertEqual(
            context['status_choices'],
            [('overdue', 'Overdue'), ('reported', 'Reported')])

    def test_trial(self):
        client = Client()
        response = client.get("/trial/{}/".format(self.due_trial.registry_id))
        context = response.context
        self.assertEqual(context['trial'], self.due_trial)
        self.assertEqual(context['title'], "id_1: An overdue trial by Sponsor 1")
        self.assertEqual(str(context['due_date']), "2016-12-31 00:00:00")
        self.assertEqual(context['annotation_html'], "")

    @patch('frontend.views._get_full_markdown_path')
    def test_trial_annotation(self, mock_path):
        test_page = os.path.join(
            settings.BASE_DIR,
            'frontend/tests/fixtures/static_page.md')
        mock_path.return_value = test_page
        client = Client()
        response = client.get("/trial/{}/".format(self.due_trial.registry_id))
        context = response.context
        self.assertIn("<em>toots</em>", context['annotation_html'])
        self.assertIn("Read more", context['annotation_html'])
        self.assertNotIn("below the fold", context['annotation_html'])

    def test_static_markdown_404(self):
        client = Client()
        response = client.get("/pages/a/b/c")
        self.assertEqual(response.status_code, 404)

    @patch('frontend.views._get_full_markdown_path')
    def test_static_markdown(self, mock_path):
        test_page = os.path.join(
            settings.BASE_DIR,
            'frontend/tests/fixtures/static_page.md')
        mock_path.return_value = test_page
        client = Client()
        content = client.get("/pages/a/b/c").content
        self.assertIn(b"<em>toots</em>", content)
        self.assertIn(b"<title>Static Page</title>", content)


    def test_sitemap(self):
        client = Client()
        response = client.get('/sitemap.xml')
        content = response.content
        self.assertIn(b'http://testserver/sponsor/sponsor-1/', content)


class ApiResultsTestCase(TestCase):
    maxDiff = 6000
    @patch('frontend.trial_computer.date')
    def setUp(self, datetime_mock):
        self.mock_today = date(2017, 1, 31)
        datetime_mock.today = Mock(return_value=self.mock_today)
        self.sponsor = Sponsor.objects.create(
            name="Sponsor 1",
            updated_date=self.mock_today)
        self.due_trial = makeTrial(
            self.sponsor,
            results_due=True,
            has_results=False,
            updated_date=self.mock_today)
        self.reported_trial = makeTrial(
            self.sponsor,
            results_due=True,
            has_results=True,
            # The following has the effect of setting
            # `previous_status` to `overdue` and status to `reported`
            status=Trial.STATUS_OVERDUE,
            reported_date=date(2016, 12, 1),
            updated_date=self.mock_today)
        self.due_but_no_longer_act_trial = makeTrial(
            self.sponsor,
            results_due=True,
            has_results=False,
            previous_status=Trial.STATUS_OVERDUE,
            status=Trial.STATUS_NO_LONGER_ACT,
            updated_date=self.mock_today)
        self.old_no_longer_act_trial = makeTrial(
            self.sponsor,
            results_due=True,
            has_results=False,
            previous_status=Trial.STATUS_OVERDUE,
            status=Trial.STATUS_NO_LONGER_ACT,
            updated_date=date(2016, 1, 1))
        set_current_rankings()

    def test_trial_csv(self):
        client = APIClient()
        response = client.get('/api/trials.csv')
        results = list(csv.DictReader(io.StringIO(response.content.decode('utf-8'))))
        self.assertEqual(results[0]['sponsor_slug'], 'sponsor-1')

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

        response = client.get('/api/trials/', {'status': 'overdue-cancelled'}, format='json').json()
        self.assertEqual(response['recordsFiltered'], 0)

        response = client.get('/api/trials/', {'search[value]': 'overdue-cancelled'}, format='json').json()
        self.assertEqual(response['recordsFiltered'], 0)

        response = client.get('/api/trials/', {'search[value]': 'Trial'}, format='json').json()
        self.assertEqual(response['recordsFiltered'], 2)

    def test_trial_today_filters(self):
        client = APIClient()
        response = client.get('/api/trials/', {'is_overdue_today': '2'}, format='json').json()
        self.assertEqual(response['recordsFiltered'], 1)
        self.assertEqual(response['results'][0]['title'], self.due_trial.title)

        response = client.get('/api/trials/', {'is_no_longer_overdue_today': '2'}, format='json').json()
        self.assertEqual(response['recordsFiltered'], 1)
        self.assertEqual(response['results'][0]['title'], self.reported_trial.title)


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
             'updated_date': self.mock_today.strftime('%Y-%m-%d')}
        )

    def test_sponsor_filter(self):
        client = APIClient()
        response = client.get('/api/sponsors/', {'num_trials_min': 0}, format='json').json()
        self.assertEqual(response['recordsFiltered'], 1)
        self.assertEqual(response['results'][0]['slug'], self.sponsor.slug)

        response = client.get('/api/sponsors/', {'num_trials_min': 4}, format='json').json()
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
            {'date': self.mock_today.strftime('%Y-%m-%d'),
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

def _make_sponsor_with_date(num, updated_date):
    sponsor, _ = Sponsor.objects.get_or_create(name="Sponsor {}".format(num))
    sponsor.updated_date = updated_date
    sponsor.save()
    return sponsor

class ApiPerformanceResultsTestCase(TestCase):
    maxDiff = 6000
    def _makeRankingsForDate(self, target_date):
        with patch('frontend.trial_computer.date') as datetime_mock:
            self.mock_today = target_date
            datetime_mock.today = Mock(return_value=self.mock_today)
            self.sponsor1 = _make_sponsor_with_date(1, self.mock_today)
            self.sponsor2 = _make_sponsor_with_date(2, self.mock_today)
            self.due_trial = makeTrial(
                self.sponsor1,
                registry_id='due trial',
                results_due=True,
                has_results=False,
                updated_date=self.mock_today)
            self.reported_trial = makeTrial(
                self.sponsor2,
                registry_id='reported trial',
                results_due=True,
                has_results=True,
                reported_date=date(2016,12,1),
                updated_date=self.mock_today)
            set_current_rankings()

    def setUp(self):
        self._makeRankingsForDate(date(2017, 1, 31))

    def test_performance_results(self):
        client = APIClient()
        response = client.get('/api/performance/', format='json').json()
        self.assertEqual(
            response,
            {
                'due': 2,
                'reported': 1,
                'days_late': 1,
                'overdue_today': 1,
                'late_today': 0,
                'on_time_today': 1,
                'fines_str': '$11,569'}
        )

    def test_performance_single_sponsor(self):
        client = APIClient()
        response = client.get(
            "/api/performance/?sponsor={}".format(self.sponsor1.slug), format='json').json()
        self.assertEqual(
            response,
            {
                'due': 1,
                'reported': 0,
                'days_late': 1,
                'overdue_today': 1,
                'late_today': 0,
                'on_time_today': 0,
                'fines_str': '$11,569'}
        )

    def test_performance_no_results(self):
        Sponsor.objects.create(
            name="xyz",
            slug="xyz")
        set_current_rankings()
        client = APIClient()
        response = client.get('/api/performance/', {'sponsor': 'xyz'}, format='json').json()
        self.assertEqual(
            response,
            {
                'due': 0,
                'reported': 0,
                'overdue_today': 0,
                'late_today': 0,
                'days_late': None,
                'on_time_today': 0,
                'fines_str': '$0'}
        )

    @patch('frontend.models.date')
    def test_performance_results_overdue_counts(self, mock_date):
        mock_date.today.return_value = self.mock_today
        mock_date.today = self.mock_today
        client = APIClient()
        # default status is `ongoing`, so making new trials which are
        # (e.g.) overdue will be counted as overdue today.
        response = client.get('/api/performance/', format='json').json()
        self.assertEqual(response['due'], 2)
        self.assertEqual(response['overdue_today'], 1)
        self.assertEqual(response['on_time_today'], 1)

        # Now simulate an import of the same data on the next day
        self._makeRankingsForDate(date(2017,2,1))
        response = client.get('/api/performance/', format='json').json()
        self.assertEqual(response['due'], 2)
        self.assertEqual(response['overdue_today'], 0)
        self.assertEqual(response['on_time_today'], 0)

    @patch('frontend.models.date')
    def test_performance_results_overdue_counts_reverting(self, mock_date):
        mock_date.today.return_value = self.mock_today
        mock_date.today = self.mock_today
        client = APIClient()

        self.due_trial.previous_status = Trial.STATUS_OVERDUE
        self.due_trial.save()
        response = client.get('/api/performance/', format='json').json()
        self.assertEqual(response['due'], 2)
        self.assertEqual(response['overdue_today'], 0)
