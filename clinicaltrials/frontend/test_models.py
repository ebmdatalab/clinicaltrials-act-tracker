from django.test import TestCase
from django.core.exceptions import ValidationError
from datetime import date
from datetime import timedelta

from frontend.models import Sponsor
from frontend.models import Trial
from frontend.models import Ranking


class RankingTestCase(TestCase):
    def setUp(self):
        self.date1 = date(2016, 1, 1)
        self.date2 = date(2016, 2, 1)
        self.date3 = date(2016, 3, 1)
        self.sponsor1 = Sponsor.objects.create(name="Sponsor 1")
        self.sponsor2 = Sponsor.objects.create(name="Sponsor 2")
        self.sponsor1_ranking1 = Ranking.objects.create(
            sponsor=self.sponsor1,
            date=self.date1,
            due=1,
            reported=0
        )
        self.sponsor1_ranking2 = Ranking.objects.create(
            sponsor=self.sponsor1,
            date=self.date2,
            due=2,
            reported=1
        )
        self.sponsor2_ranking1 = Ranking.objects.create(
            sponsor=self.sponsor2,
            date=self.date1,
            due=2,
            reported=2
        )
        self.sponsor2_ranking2 = Ranking.objects.create(
            sponsor=self.sponsor2,
            date=self.date2,
            due=2,
            reported=0
        )
        self.sponsor2_ranking3 = Ranking.objects.create(
            sponsor=self.sponsor2,
            date=self.date3,
            due=2,
            reported=2
        )
        self.sponsor1_ranking3 = Ranking.objects.create(
            sponsor=self.sponsor1,
            date=self.date3,
            due=2,
            reported=2
        )

    def test_percentage_set(self):
        self.assertEqual(self.sponsor1_ranking1.percentage, 0.0)
        self.assertEqual(self.sponsor1_ranking2.percentage, 50.0)
        self.assertEqual(self.sponsor1_ranking3.percentage, 100.0)
        self.assertEqual(self.sponsor2_ranking1.percentage, 100.0)
        self.assertEqual(self.sponsor2_ranking2.percentage, 0.0)
        self.assertEqual(self.sponsor2_ranking3.percentage, 100.0)

    def test_compute_ranks(self):
        Ranking.objects.set_current()
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


counter = 0
def _makeTrial(sponsor, is_due, is_reported):
    global counter
    tomorrow = date.today() + timedelta(days=1)
    counter += 1
    start_date = date(2015, 1, 1)
    if is_due:
        due_date = date(2016, 1, 1)
    else:
        due_date = tomorrow
    if is_reported:
        completion_date = date(2016, 1, 1)
    else:
        completion_date = None
    return Trial.objects.create(
        sponsor=sponsor,
        registry_id='id_{}'.format(counter),
        publication_url='http://bar.com/{}'.format(counter),
        title='Trial {}'.format(counter),
        start_date=start_date,
        due_date=due_date,
        completion_date=completion_date)


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
        with_reported_early = Sponsor.objects.with_trials_reported_early()
        self.assertEqual(len(with_reported_early), 0)

    def test_trials_due(self):
        self.assertCountEqual(
            self.sponsor.trials().due(),
            [self.due_trial, self.reported_trial])

    def test_trials_unreported(self):
        self.assertCountEqual(
            self.sponsor.trials().unreported(),
            [self.due_trial, self.not_due_trial])

    def test_trials_reported(self):
        self.assertCountEqual(
            self.sponsor.trials().reported(),
            [self.reported_trial])

    def test_trials_overdue(self):
        self.assertCountEqual(
            self.sponsor.trials().overdue(),
            [self.due_trial])

    def test_trials_reported_early(self):
        self.assertCountEqual(
            self.sponsor.trials().reported_early(),
            [])
