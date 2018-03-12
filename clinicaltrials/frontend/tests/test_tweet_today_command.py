from datetime import date
from io import StringIO

from unittest.mock import patch
from unittest.mock import MagicMock
from unittest.mock import Mock

from django.core.management import call_command
from django.test import TestCase

from frontend.management.commands.process_data import set_current_rankings
from frontend.models import Sponsor
from frontend.tests.common import makeTrial

import twitter


class TweetTodayTestCase(TestCase):
    maxDiff = 6000
    @patch('frontend.trial_computer.date')
    def setUp(self, datetime_mock):
        self.mock_today = date(2017, 1, 31)
        datetime_mock.today = Mock(return_value=self.mock_today)
        self.sponsor = Sponsor.objects.create(
            name="Sponsor 1",
            updated_date=self.mock_today)
        set_current_rankings()

    @patch('frontend.management.commands.tweet_today.twitter')
    def test_all_variables(self, twitter_mock):
        self.due_trial = makeTrial(
            self.sponsor,
            results_due=True,
            has_results=False,
            updated_date=self.mock_today)
        self.invisible_trial = makeTrial(
            self.sponsor,
            results_due=True,
            has_results=False,
            no_longer_on_website=True,
            updated_date=self.mock_today)
        self.reported_trial = makeTrial(
            self.sponsor,
            results_due=True,
            has_results=True,
            reported_date=date(2016, 12, 1),
            updated_date=self.mock_today)
        for _ in range(3):
            self.late_trial = makeTrial(
                self.sponsor,
                results_due=True,
                has_results=True,
                reported_date=date(2017, 12, 1),
                updated_date=self.mock_today)
        set_current_rankings()
        api = MagicMock(twitter.api.Api, name='api')
        twitter_mock.Api.return_value = api
        out = StringIO()
        call_command('tweet_today', stdout=out)
        api.PostUpdate.assert_called_with(
            'Since our last update, 1 trial became overdue, and 3 trials '
            'reported late. 1 trial reported its results on time. 80% of '
            'all due trials have reported their results.  '
            'https://fdaaa.trialstracker.net/')

    @patch('frontend.management.commands.tweet_today.twitter')
    def test_single_variable(self, twitter_mock):
        self.due_trial = makeTrial(
            self.sponsor,
            results_due=True,
            has_results=False,
            updated_date=self.mock_today)
        set_current_rankings()
        api = MagicMock(twitter.api.Api, name='api')
        twitter_mock.Api.return_value = api
        out = StringIO()
        call_command('tweet_today', stdout=out)
        api.PostUpdate.assert_called_with(
            'Since our last update, 1 trial became overdue. 0% of all due '
            'trials have reported their results.  '
            'https://fdaaa.trialstracker.net/')

    @patch('frontend.management.commands.tweet_today.twitter')
    @patch('frontend.views.current_and_prev')
    def test_noop(self, ranking_mock, twitter_mock):
        api = MagicMock(twitter.api.Api, name='api')
        ranking_mock.return_value = (0, 0)
        twitter_mock.Api.return_value = api
        out = StringIO()
        call_command('tweet_today', stdout=out)
        api.PostUpdate.assert_not_called()
