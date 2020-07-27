import datetime
from collections import OrderedDict

from django.test import TestCase
from django.core.exceptions import ValidationError
from datetime import date
from datetime import timedelta

from frontend.models import Sponsor
from frontend.models import Trial
from frontend.models import TrialQA
from frontend.models import Ranking
from frontend.tests.common import simulateImport
from frontend.tests.common import makeTrial
from frontend.management.commands.process_data import set_current_rankings
from unittest.mock import patch, Mock


class RankingTestCase(TestCase):
    def setUp(self):
        self.date1 = date(2014, 1, 1)
        self.date2 = date(2014, 2, 1)
        self.date3 = date(2014, 3, 1)
        self.sponsor1 = Sponsor.objects.create(name="Sponsor 1")
        self.sponsor2 = Sponsor.objects.create(name="Sponsor 2")
        self.sponsor3 = Sponsor.objects.create(name="Sponsor 3")

        test_trials = OrderedDict(
            {
                self.date1: [
                    # sponsor, due, reported
                    (self.sponsor1, True, False),
                    (self.sponsor2, True, True),
                    (self.sponsor2, True, True),
                ],
                self.date2: [
                    # sponsor, due, reported
                    (self.sponsor1, True, False),
                    (self.sponsor1, True, True),
                    (self.sponsor2, True, False),
                    (self.sponsor2, True, False),
                ],
                self.date3: [
                    # sponsor, due, reported
                    (self.sponsor2, True, True),
                    (self.sponsor2, True, True),
                    (self.sponsor1, True, True),
                    (self.sponsor1, True, True),
                ],
            }
        )
        simulateImport(test_trials)

    def test_percentage_set(self):
        self.assertEqual(self.sponsor1.rankings.get(date=self.date1).percentage, 0.0)
        self.assertEqual(self.sponsor1.rankings.get(date=self.date2).percentage, 50.0)
        self.assertEqual(self.sponsor1.rankings.get(date=self.date3).percentage, 100.0)
        self.assertEqual(self.sponsor2.rankings.get(date=self.date1).percentage, 100.0)
        self.assertEqual(self.sponsor2.rankings.get(date=self.date2).percentage, 0.0)
        self.assertEqual(self.sponsor2.rankings.get(date=self.date3).percentage, 100.0)

    def test_compute_ranks(self):
        ranks = Ranking.objects.filter(date=self.date1).all()
        self.assertEqual(ranks[0].rank, 1)
        self.assertEqual(ranks[0].sponsor, self.sponsor2)
        self.assertEqual(ranks[1].rank, 2)
        self.assertEqual(ranks[1].sponsor, self.sponsor1)

        ranks = Ranking.objects.filter(date=self.date2).all()
        self.assertEqual(ranks[0].rank, 1)
        self.assertEqual(ranks[0].sponsor, self.sponsor1)
        self.assertEqual(ranks[1].rank, 2)
        self.assertEqual(ranks[1].sponsor, self.sponsor2)

        ranks = Ranking.objects.filter(date=self.date3).all()
        self.assertEqual(ranks[0].rank, 1)
        self.assertEqual(ranks[0].sponsor, self.sponsor1)
        self.assertEqual(ranks[1].rank, 1)
        self.assertEqual(ranks[1].sponsor, self.sponsor2)


class SponsorTrialsTestCase(TestCase):
    def setUp(self):
        self.sponsor = Sponsor.objects.create(name="Sponsor 1")
        self.sponsor2 = Sponsor.objects.create(name="Sponsor 2")
        self.due_trial = makeTrial(
            self.sponsor, registry_id="due_trial", results_due=True, has_results=False
        )
        self.reported_trial = makeTrial(
            self.sponsor,
            registry_id="reported_trial",
            results_due=True,
            has_results=True,
            reported_date=date(2014, 12, 1),
        )
        self.qa_submitted_trial = makeTrial(
            self.sponsor, registry_id="qa_submitted_trial", results_due=True
        )
        self.qa_submitted_trial.trialqa_set.create(
            submitted_to_regulator=date(2014, 12, 1)
        )
        self.cancelled_trial = makeTrial(
            self.sponsor, registry_id="cancelled_trial", results_due=True
        )
        self.cancelled_trial.trialqa_set.create(
            submitted_to_regulator=date(2014, 12, 1),
            cancelled_by_sponsor=date(2014, 12, 1),
        )
        self.not_due_trial = makeTrial(
            self.sponsor,
            registry_id="not_due_trial",
            results_due=False,
            has_results=False,
        )

    def test_slug(self):
        self.assertEqual(self.sponsor.slug, "sponsor-1")

    def test_zombie_sponsor(self):
        self.assertEqual(len(self.sponsor.trial_set.visible()), 5)
        filtered_due = Trial.objects.filter(registry_id=self.due_trial.registry_id)
        # Updating via querset means we don't trigger `save()`
        # callbacks, which recompute status based on dates etc.
        filtered_due.update(status=Trial.STATUS_NO_LONGER_ACT)
        self.assertEqual(len(self.sponsor.trial_set.visible()), 4)  # still 5 failure

    def test_trials_due(self):
        self.assertCountEqual(
            list(self.sponsor.trial_set.due()),
            [
                self.due_trial,
                self.reported_trial,
                self.cancelled_trial,
                self.qa_submitted_trial,
            ],
        )

    def test_trials_unreported(self):
        self.assertCountEqual(
            list(self.sponsor.trial_set.unreported()),
            [self.due_trial, self.not_due_trial, self.cancelled_trial],
        )
        self.assertEqual(self.not_due_trial.status, "ongoing")

    def test_trials_reported(self):
        self.assertCountEqual(
            list(self.sponsor.trial_set.reported()),
            [self.reported_trial, self.qa_submitted_trial],
        )

    def test_trials_overdue(self):
        self.assertEqual(self.due_trial.status, "overdue")
        self.assertCountEqual(
            list(self.sponsor.trial_set.overdue()),
            [self.due_trial, self.cancelled_trial],
        )

    def test_trials_reported_early(self):
        self.assertCountEqual(list(self.sponsor.trial_set.reported_early()), [])

    def test_today_counts(self):
        # save all the Trials with a new date to simulate an import run
        new_date = date.today() + datetime.timedelta(days=1)
        for trial in Trial.objects.all():
            trial.updated_date = new_date
            trial.sponsor.updated_date = new_date
            trial.save()
            trial.sponsor.save()
        # now alter a couple so we have new "today" state changes
        TrialQA.objects.create(
            submitted_to_regulator=date(2015, 1, 2), trial_id=self.cancelled_trial.id
        )
        TrialQA.objects.create(
            submitted_to_regulator=date(2014, 1, 2), trial_id=self.due_trial.id
        )
        set_current_rankings()

        self.assertCountEqual(
            Trial.objects.no_longer_overdue_today(),
            [self.due_trial, self.cancelled_trial],
        )
        self.assertCountEqual(Trial.objects.late_today(), [self.cancelled_trial])
        self.assertCountEqual(Trial.objects.on_time_today(), [self.due_trial])


class SponsorTrialsStatusTestCase(TestCase):
    def setUp(self):
        self.sponsor = Sponsor.objects.create(name="Sponsor 1")

    def test_status_choices(self):
        makeTrial(
            self.sponsor,
            has_results=False,
            results_due=True,
            completion_date="2014-01-01",
        )
        self.assertEqual(self.sponsor.status_choices(), [("overdue", "Overdue")])
        self.assertEqual(Trial.objects.status_choices(), [("overdue", "Overdue")])
        makeTrial(
            self.sponsor,
            has_results=False,
            results_due=False,
            completion_date="2014-01-01",
        )
        self.assertEqual(
            self.sponsor.status_choices(),
            [("overdue", "Overdue"), ("ongoing", "Ongoing"),],
        )
        self.assertEqual(
            Trial.objects.status_choices(),
            [("overdue", "Overdue"), ("ongoing", "Ongoing"),],
        )

    def test_trial_overdue(self):
        trial = makeTrial(
            self.sponsor,
            has_results=False,
            results_due=True,
            completion_date="2014-01-01",
        )
        self.assertEqual(trial.status, "overdue")
        self.assertEqual(list(self.sponsor.trial_set.overdue()), [trial])

    def test_trial_ongoing(self):
        trial = makeTrial(
            self.sponsor,
            has_results=False,
            results_due=False,
            completion_date="2014-01-01",
        )
        self.assertEqual(trial.status, "ongoing")
        self.assertEqual(trial.calculated_due_date(), date(2015, 1, 1))

    def test_trial_with_certificate_ongoing(self):
        trial = makeTrial(
            self.sponsor,
            has_results=False,
            results_due=False,
            has_exemption=True,
            completion_date="2014-01-01",
        )
        self.assertEqual(trial.status, "ongoing")
        self.assertEqual(trial.calculated_due_date(), date(2017, 1, 1))

    def test_trial_not_reported_late(self):
        trial = makeTrial(
            self.sponsor,
            has_results=True,
            results_due=True,
            completion_date="2014-01-01",
            reported_date="2014-12-01",
        )
        self.assertEqual(trial.status, "reported")
        self.assertEqual(list(self.sponsor.trial_set.reported_on_time()), [trial])
        self.assertEqual(list(self.sponsor.trial_set.reported_late()), [])

    def test_trial_reported_late(self):
        trial = makeTrial(
            self.sponsor,
            has_results=True,
            results_due=True,
            completion_date="2014-01-01",
            reported_date="2015-12-01",
        )
        self.assertEqual(trial.status, "reported-late")
        self.assertEqual(list(self.sponsor.trial_set.reported_on_time()), [])
        self.assertEqual(list(self.sponsor.trial_set.reported_late()), [trial])

    def test_reported_trial_under_qa(self):
        trial = makeTrial(
            self.sponsor,
            has_results=False,
            results_due=True,
            completion_date="2014-01-01",
        )
        TrialQA.objects.create(
            submitted_to_regulator="2014-02-01", returned_to_sponsor=None, trial=trial
        )
        self.assertEqual(trial.status, "reported")
        self.assertEqual(str(trial.calculated_reported_date()), "2014-02-01")

    def test_overdue_trial_under_qa(self):
        trial = makeTrial(
            self.sponsor,
            has_results=False,
            results_due=True,
            completion_date="2014-01-01",
        )
        TrialQA.objects.create(
            submitted_to_regulator="2015-02-01", returned_to_sponsor=None, trial=trial
        )
        self.assertEqual(trial.status, "reported-late")

    def test_trials_reported_late_is_late(self):
        trial = makeTrial(
            self.sponsor,
            has_results=True,
            results_due=True,
            completion_date="2014-01-01",
            reported_date="2015-01-02",
        )
        self.assertEqual(trial.status, "reported-late")
        self.assertEqual(list(self.sponsor.trial_set.reported_late()), [trial])


class SponsorTrialsLatenessTestCase(TestCase):
    def setUp(self):
        self.sponsor = Sponsor.objects.create(name="Sponsor 1")

    def test_reported_trial_late(self):
        trial = makeTrial(
            self.sponsor,
            has_results=True,
            results_due=True,
            completion_date="2014-01-01",
            reported_date="2015-01-02",
        )
        self.assertEqual(trial.days_late, 1)
        self.assertEqual(trial.finable_days_late, None)

    def test_reported_trial_finably_late(self):
        trial = makeTrial(
            self.sponsor,
            has_results=True,
            results_due=True,
            completion_date="2014-01-01",
            reported_date="2016-01-01",
        )
        self.assertEqual(trial.days_late, 365)
        self.assertEqual(trial.finable_days_late, 365 - Trial.FINES_GRACE_PERIOD)

    def test_reported_trial_no_longer_late(self):
        trial = makeTrial(
            self.sponsor,
            has_results=True,
            results_due=True,
            completion_date="2015-01-01",
            reported_date="2015-01-01",
        )
        trial.results_due = False
        trial.save()
        self.assertEqual(trial.finable_days_late, None)

    def test_reported_trial_not_late(self):
        trial = makeTrial(
            self.sponsor,
            has_results=True,
            results_due=True,
            completion_date="2014-01-01",
            reported_date="2014-12-01",
        )
        self.assertEqual(trial.days_late, None)

    def test_trial_under_qa_not_late(self):
        trial = makeTrial(
            self.sponsor,
            has_results=False,
            results_due=True,
            completion_date="2014-01-01",
        )
        TrialQA.objects.create(
            submitted_to_regulator="2014-02-01", returned_to_sponsor=None, trial=trial
        )
        self.assertEqual(trial.days_late, None)

    def test_trial_under_qa_late(self):
        trial = makeTrial(
            self.sponsor,
            has_results=False,
            results_due=True,
            completion_date="2014-01-01",
        )
        TrialQA.objects.create(
            submitted_to_regulator="2015-01-02", returned_to_sponsor=None, trial=trial
        )
        self.assertEqual(trial.days_late, 1)

    def test_trial_under_qa_finably_late(self):
        trial = makeTrial(
            self.sponsor,
            has_results=False,
            results_due=True,
            completion_date="2013-01-01",
        )
        TrialQA.objects.create(
            submitted_to_regulator="2015-01-01", returned_to_sponsor=None, trial=trial
        )
        self.assertEqual(trial.days_late, 365)
        self.assertEqual(trial.finable_days_late, 335)

    @patch("frontend.trial_computer.date")
    def test_trial_under_qa_finably_late_cancelled(self, datetime_mock):
        datetime_mock.today = Mock(return_value=date(2016, 3, 1))
        trial = makeTrial(
            self.sponsor,
            has_results=False,
            results_due=True,
            completion_date="2013-01-01",
        )
        TrialQA.objects.create(
            submitted_to_regulator="2015-01-01",
            cancelled_by_sponsor="2016-01-01",
            trial=trial,
        )
        self.assertEqual(trial.days_late, 790)
        self.assertEqual(trial.finable_days_late, 335)

    @patch("frontend.trial_computer.date")
    def test_trial_under_qa_late_with_cancellation(self, datetime_mock):
        datetime_mock.today = Mock(return_value=date(2015, 3, 1))
        trial = makeTrial(
            self.sponsor,
            has_results=False,
            results_due=True,
            completion_date="2014-01-01",
        )
        TrialQA.objects.create(
            submitted_to_regulator="2014-02-01",
            cancelled_by_sponsor="2014-02-01",
            trial=trial,
        )
        self.assertEqual(trial.days_late, 59)
        self.assertEqual(trial.finable_days_late, None)

    def test_trial_under_qa_late_with_much_correspondence(self):
        trial = makeTrial(
            self.sponsor,
            has_results=False,
            results_due=True,
            completion_date="2014-01-01",
        )
        TrialQA.objects.create(
            submitted_to_regulator="2014-02-01",
            returned_to_sponsor="2014-02-02",
            trial=trial,
        )
        TrialQA.objects.create(
            submitted_to_regulator="2014-02-03",
            cancelled_by_sponsor="2014-02-04",
            trial=trial,
        )
        TrialQA.objects.create(submitted_to_regulator="2015-03-01", trial=trial)
        self.assertEqual(trial.days_late, 59)
        self.assertEqual(trial.finable_days_late, None)

    @patch("frontend.trial_computer.date")
    def test_unreported_trial_late_within_grace(self, datetime_mock):
        datetime_mock.today = Mock(return_value=date(2015, 1, 31))
        trial = makeTrial(
            self.sponsor,
            has_results=False,
            results_due=True,
            completion_date="2014-01-01",
        )
        self.assertEqual(trial.days_late, None)

    @patch("frontend.trial_computer.date")
    def test_unreported_trial_late_outside_grace(self, datetime_mock):
        datetime_mock.today = Mock(return_value=date(2015, 2, 1))
        trial = makeTrial(
            self.sponsor,
            has_results=False,
            results_due=True,
            completion_date="2014-01-01",
        )
        self.assertEqual(trial.days_late, 31)
