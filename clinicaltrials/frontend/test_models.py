from django.test import TestCase
from django.core.exceptions import ValidationError
from datetime import date
from datetime import timedelta

from frontend.models import Sponsor
from frontend.models import Trial
from frontend.models import Ranking


trial_counter = 0
def _makeTrial(sponsor, results_due, has_results):
    global trial_counter
    tomorrow = date.today() + timedelta(days=1)
    trial_counter += 1
    start_date = date(2015, 1, 1)
    if has_results:
        completion_date = date(2016, 1, 1)
    else:
        completion_date = None
    return Trial.objects.create(
        sponsor=sponsor,
        registry_id='id_{}'.format(trial_counter),
        publication_url='http://bar.com/{}'.format(trial_counter),
        title='Trial {}'.format(trial_counter),
        has_results=has_results,
        results_due=results_due,
        start_date=start_date,
        completion_date=completion_date)

def _simulateImport(test_trials):
    """Do the same as the import script, but for an array of tuples
    """
    last_date = None
    for updated_date, sponsor, due, reported in test_trials:
        if updated_date != last_date:
            # simulate a new import; this means deleting all
            # existing Trials and updating rankings (see below)
            Ranking.objects.set_current()
            Trial.objects.all().delete()
        sponsor.updated_date = updated_date
        sponsor.save()
        _makeTrial(
            sponsor,
            results_due=due,
            has_results=reported
        )
        last_date = updated_date
    Ranking.objects.set_current()


class RankingTestCase(TestCase):
    def setUp(self):
        self.date1 = date(2016, 1, 1)
        self.date2 = date(2016, 2, 1)
        self.date3 = date(2016, 3, 1)
        self.sponsor1 = Sponsor.objects.create(name="Sponsor 1")
        self.sponsor2 = Sponsor.objects.create(name="Sponsor 2")
        self.sponsor3 = Sponsor.objects.create(name="Sponsor 3")

        test_trials = [
            # date,  sponsor, due, reported
            (self.date1, self.sponsor1, True, False),
            (self.date1, self.sponsor2, True, True),
            (self.date1, self.sponsor2, True, True),

            (self.date2, self.sponsor1, True, False),
            (self.date2, self.sponsor1, True, True),
            (self.date2, self.sponsor2, True, False),
            (self.date2, self.sponsor2, True, False),

            (self.date3, self.sponsor2, True, True),
            (self.date3, self.sponsor2, True, True),
            (self.date3, self.sponsor1, True, True),
            (self.date3, self.sponsor1, True, True),
        ]
        _simulateImport(test_trials)

    def test_percentage_set(self):
        self.assertEqual(self.sponsor1.rankings.get(date=self.date1).percentage, 0.0)
        self.assertEqual(self.sponsor1.rankings.get(date=self.date2).percentage, 50.0)
        self.assertEqual(self.sponsor1.rankings.get(date=self.date3).percentage, 100.0)
        self.assertEqual(self.sponsor2.rankings.get(date=self.date1).percentage, 100.0)
        self.assertEqual(self.sponsor2.rankings.get(date=self.date2).percentage, 0.0)
        self.assertEqual(self.sponsor2.rankings.get(date=self.date3).percentage, 100.0)

    def test_compute_ranks(self):
        ranks = Ranking.objects.with_rank().filter(date=self.date1).all()
        self.assertEqual(ranks[0].rank, 1)
        self.assertEqual(ranks[0].sponsor, self.sponsor2)
        self.assertEqual(ranks[1].rank, 2)
        self.assertEqual(ranks[1].sponsor, self.sponsor1)

        ranks = Ranking.objects.with_rank().filter(date=self.date2).all()
        self.assertEqual(ranks[0].rank, 1)
        self.assertEqual(ranks[0].sponsor, self.sponsor1)
        self.assertEqual(ranks[1].rank, 2)
        self.assertEqual(ranks[1].sponsor, self.sponsor2)

        ranks = Ranking.objects.with_rank().filter(date=self.date3).all()
        self.assertEqual(ranks[0].rank, 1)
        self.assertEqual(ranks[0].sponsor, self.sponsor1)
        self.assertEqual(ranks[1].rank, 1)
        self.assertEqual(ranks[1].sponsor, self.sponsor2)


class SponsorTrialsTestCase(TestCase):

    def setUp(self):
        self.sponsor = Sponsor.objects.create(name="Sponsor 1")
        self.sponsor2 = Sponsor.objects.create(name="Sponsor 2")
        self.due_trial = _makeTrial(self.sponsor, True, False)
        self.reported_trial = _makeTrial(self.sponsor, True, True)
        self.not_due_trial = _makeTrial(self.sponsor, False, False)

    def test_slug(self):
        self.assertEqual(self.sponsor.slug, 'sponsor-1')

    def test_sponsor_annotation(self):
        self.assertEqual(Sponsor.objects.annotated().first().num_trials, 3)

    def test_sponsor_due(self):
        with_due = Sponsor.objects.with_trials_due()
        self.assertEqual(len(with_due), 1)
        self.assertEqual(with_due.first().num_trials, 2)

    def test_sponsor_unreported(self):
        with_unreported = Sponsor.objects.with_trials_unreported()
        self.assertEqual(len(with_unreported), 1)
        self.assertEqual(with_unreported.first().num_trials, 2)

    def test_sponsor_reported(self):
        with_reported = Sponsor.objects.with_trials_reported()
        self.assertEqual(len(with_reported), 1)
        self.assertEqual(with_reported.first().num_trials, 1)

    def test_sponsor_overdue(self):
        with_overdue = Sponsor.objects.with_trials_overdue()
        self.assertEqual(len(with_overdue), 1)
        self.assertEqual(with_overdue.first().num_trials, 1)

    def test_sponsor_reported_early(self):
        with_reported_early = Sponsor.objects.with_trials_reported_late()
        self.assertEqual(len(with_reported_early), 0)

    def test_trials_due(self):
        self.assertCountEqual(
            self.sponsor.trials().due(),
            [self.due_trial, self.reported_trial])

    def test_trials_unreported(self):
        self.assertCountEqual(
            self.sponsor.trials().unreported(),
            [self.due_trial, self.not_due_trial])
        self.assertEqual(self.not_due_trial.status, 'ongoing')

    def test_trials_reported(self):
        self.assertCountEqual(
            self.sponsor.trials().reported(),
            [self.reported_trial])

    def test_trials_overdue(self):
        self.assertCountEqual(
            self.sponsor.trials().overdue(),
            [self.due_trial])
        self.assertEqual(self.due_trial.status, 'overdue')

    def test_trials_reported_early(self):
        self.assertCountEqual(
            self.sponsor.trials().reported_early(),
            [])

    def test_trials_reported_late_not_late(self):
        trial = self.sponsor.trials()[0]
        trial.has_results = True
        trial.completion_date = '2016-01-01'
        trial.reported_date = '2016-01-11'
        trial.save()
        self.assertEqual(trial.status, 'reported')
        self.assertCountEqual(
            self.sponsor.trials().reported_late(),
            [])

    def test_trials_reported_late_is_late(self):
        trial = self.sponsor.trials()[0]
        trial.has_results = True
        trial.completion_date = '2016-01-01'
        trial.reported_date = '2017-01-01'
        trial.save()
        self.assertEqual(trial.status, 'reported-late')
        self.assertCountEqual(
            self.sponsor.trials().reported_late(),
            [trial])
