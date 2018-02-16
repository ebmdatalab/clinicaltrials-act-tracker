from datetime import date
from datetime import timedelta
from dateutil.relativedelta import relativedelta

from django.db import connection
from django.db import models
from django.db import transaction
from django.db.models import F
from django.db.models import Q
from django.utils.text import slugify
from django.utils.dateparse import parse_date
from django.urls import reverse


GRACE_PERIOD = 30

class TrialManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(
            no_longer_on_website=False).prefetch_related('trialqa_set')

    def due(self):
        return self.filter(status__in=['overdue', 'reported', 'reported-late'])

    def not_due(self):
        return self.filter(status='ongoing')

    def unreported(self):
        return self.filter(status__in=['overdue', 'ongoing'])

    def reported(self):
        return self.filter(status__in=['reported', 'reported-late'])

    def reported_late(self):
        return self.filter(status='reported-late')

    def overdue(self):
        return self.filter(status='overdue')

    def reported_early(self):
        return self.reported().filter(reported_date__lt=F('completion_date'))

    def status_choices_with_counts(self):
        return (
            ('overdue', 'Due', self.overdue().count()),
            ('ongoing', 'Ongoing', self.not_due().count()),
            ('reported', 'Reported', self.reported().count()),
            ('reported-late', 'Reported late', self.reported_late().count())
        )


class Sponsor(models.Model):
    slug = models.SlugField(max_length=200, primary_key=True)
    name = models.CharField(max_length=200)
    is_industry_sponsor = models.NullBooleanField(default=None)
    updated_date = models.DateField(default=date.today)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('views.sponsor', args=[self.slug])

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super(Sponsor, self).save(*args, **kwargs)

    def current_rank(self):
        return self.rankings.get(date=self.updated_date)

    def trials(self):
        # XXX redundant
        return self.trial_set



class Trial(models.Model):
    FINES_GRACE_PERIOD = 30
    STATUS_CHOICES = (
        ('overdue', 'Overdue'),
        ('ongoing', 'Ongoing'),
        ('reported', 'Reported'),
        ('reported-late', 'Reported (late)'),
    )
    sponsor = models.ForeignKey(
        Sponsor,
        on_delete=models.CASCADE)
    registry_id = models.CharField(max_length=100, unique=True, db_index=True)
    publication_url = models.URLField()
    title = models.TextField()
    has_exemption = models.BooleanField(default=False)
    # `pact` means "probable ACT"
    is_pact = models.BooleanField(default=False)
    start_date = models.DateField()
    results_due = models.BooleanField(default=False, db_index=True)
    has_results = models.BooleanField(default=False, db_index=True)
    days_late = models.IntegerField(default=None, null=True, blank=True)
    finable_days_late = models.IntegerField(default=None, null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='ongoing')
    completion_date = models.DateField(null=True, blank=True)
    no_longer_on_website = models.BooleanField(default=False)

    first_seen_date = models.DateField(default=date.today)
    updated_date = models.DateField(default=date.today)
    reported_date = models.DateField(null=True, blank=True)
    objects = TrialManager()

    def __str__(self):
        return "{}: {}".format(self.registry_id, self.title)

    def compute_metadata(self):
        self.days_late = self.get_days_late()
        if self.days_late:
            self.finable_days_late = max([
                self.days_late - Trial.FINES_GRACE_PERIOD,
                0])
        self.status = self.get_status()
        self.save()

    def _datify(self):
        """We sometimes maninpulate data before the model has been saved, and
        therefore before any date strings have been converted to date
        objects.

        """
        for field in ['reported_date',
                      'completion_date']:
            _field = getattr(self, field)
            if isinstance(_field, str):
                val = parse_date(_field)
                setattr(self, field, val)


    def qa_start_date(self):
        first_event = self.trialqa_set.first()
        if first_event:
            return first_event.submitted_to_regulator
        else:
            return None

    def get_days_late(self):
        # See https://github.com/ebmdatalab/clinicaltrials-act-tracker/issues/38
        overdue_delta = relativedelta(days=365)
        days_late = None
        if self.results_due:
            self._datify()
            if self.has_results:
                assert self.reported_date, \
                    "{} has_results but no reported date".format(self)
                days_late = max([
                    (self.reported_date
                     - self.completion_date
                     - overdue_delta).days,
                    0])
            else:
                # still not reported.
                qa_start_date = self.qa_start_date()
                if qa_start_date:
                    days_late = max([(qa_start_date - self.completion_date - overdue_delta).days, 0])
                else:
                    days_late = max([
                        (date.today()
                         - self.completion_date
                         - overdue_delta).days,
                        0])
                    if (days_late - GRACE_PERIOD) <= 0:
                        days_late = 0

        return days_late

    def get_status(self):
        # days_late() must have been called first
        overdue = self.days_late and self.days_late > 0
        if self.results_due:
            if self.has_results:
                if overdue:
                    status = 'reported-late'
                else:
                    status = 'reported'
            else:
                if self.qa_start_date():
                    if self.days_late:
                        status = 'reported-late'
                    else:
                        status = 'reported'
                else:
                    if self.days_late:
                        status = 'overdue'
                    else:
                        # We're in the grace period
                        status = 'ongoing'
        else:
            if self.has_results:
                # Reported early! Might want to track separately in
                # the future
                status = 'reported'
            else:
                status = 'ongoing'
        return status

    class Meta:
        ordering = ('completion_date',)


class TrialQA(models.Model):
    trial = models.ForeignKey(Trial, on_delete=models.CASCADE)
    submitted_to_regulator = models.DateField()
    returned_to_sponsor = models.DateField(null=True, blank=True)


class RankingManager(models.Manager):
    def with_rank(self):
        return self.filter(rank__isnull=False)

    def _compute_ranks(self):
        # XXX should only bother computing ranks for *current* date;
        # this does it for all of them.
        sql = ("WITH ranked AS (SELECT date, ranking.id, RANK() OVER ("
               "  PARTITION BY date "
               "ORDER BY percentage DESC"
               ") AS computed_rank "
               "FROM frontend_ranking ranking WHERE percentage IS NOT NULL "
               ")")

        sql += ("UPDATE "
                " frontend_ranking "
                "SET "
                " rank = ranked.computed_rank "
                "FROM ranked "
                "WHERE ranked.id = frontend_ranking.id AND ranked.date = frontend_ranking.date")
        with connection.cursor() as c:
                c.execute(sql)

    def set_current(self):
        with transaction.atomic():
            for sponsor in Sponsor.objects.all():
                due = Trial.objects.due().filter(
                    sponsor=sponsor).count()
                reported = Trial.objects.reported().filter(
                        sponsor=sponsor).count()
                total = sponsor.trial_set.count()
                try:
                    ranking = sponsor.rankings.get(
                        date=sponsor.updated_date)
                    ranking.due = due
                    ranking.reported = reported
                    ranking.total = total
                    ranking.save()
                except Ranking.DoesNotExist:
                    ranking = sponsor.rankings.create(
                        date=sponsor.updated_date,
                        due=due,
                        reported=reported,
                        total=total
                    )
            self._compute_ranks()


class Ranking(models.Model):
    sponsor = models.ForeignKey(
        Sponsor, related_name='rankings',
        on_delete=models.CASCADE)
    date = models.DateField(db_index=True)
    rank = models.IntegerField(null=True)
    due = models.IntegerField()
    total = models.IntegerField()
    reported = models.IntegerField()
    percentage = models.IntegerField(null=True)

    objects = RankingManager()

    def __str__(self):
        return "{}: {} at {}% on {}".format(self.rank, self.sponsor, self.percentage, self.date)

    def save(self, *args, **kwargs):
        if self.due:
            self.percentage = float(self.reported)/self.due * 100
        super(Ranking, self).save(*args, **kwargs)

    class Meta:
        unique_together = ('sponsor', 'date',)
        ordering = ('date', 'rank', 'sponsor__name',)
