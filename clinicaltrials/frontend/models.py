from datetime import date
from datetime import timedelta
from dateutil.relativedelta import relativedelta

from django.db import connection
from django.db import models
from django.db import transaction
from django.db.models import F
from django.db.models import Q
from django.db.models import Sum
from django.utils.text import slugify
from django.utils.dateparse import parse_date
from django.urls import reverse

from frontend.trial_computer import compute_metadata



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

    def status_choices(self):
        """A list of tuples representing valid choices for trial statuses
        """
        statuses = [x[0] for x in
                    self.trial_set.visible().order_by(
                        'status').values_list(
                            'status').distinct(
                                'status')]
        return [x for x in Trial.STATUS_CHOICES if x[0] in statuses]

    class Meta:
        ordering = ('name',)


class TrialManager(models.Manager):
    def status_choices(self):
        """A list of tuples representing valid choices for trial statuses
        """
        statuses = [x[0] for x in
                    Trial.objects.visible().order_by(
                        'status').values_list(
                            'status').distinct(
                                'status')]
        return [x for x in Trial.STATUS_CHOICES if x[0] in statuses]


class TrialQuerySet(models.QuerySet):
    def visible(self):
        return self.filter(
            no_longer_on_website=False).prefetch_related('trialqa_set')

    def due(self):
        return self.visible().filter(status__in=['overdue', 'reported', 'reported-late'])

    def not_due(self):
        return self.visible().filter(status='ongoing')

    def unreported(self):
        return self.visible().filter(status__in=['overdue', 'ongoing'])

    def reported(self):
        return self.visible().filter(status__in=['reported', 'reported-late'])

    def reported_on_time(self):
        return self.visible().filter(status='reported')

    def reported_late(self):
        return self.visible().filter(status='reported-late')

    def overdue(self):
        return self.visible().filter(status='overdue')

    def reported_early(self):
        return self.reported().filter(reported_date__lt=F('completion_date'))


class Trial(models.Model):
    FINES_GRACE_PERIOD = 30
    STATUS_OVERDUE = 'overdue'
    STATUS_ONGOING = 'ongoing'
    STATUS_REPORTED = 'reported'
    STATUS_REPORTED_LATE = 'reported-late'
    STATUS_CHOICES = (
        (STATUS_OVERDUE, 'Overdue'),
        (STATUS_ONGOING, 'Ongoing'),
        (STATUS_REPORTED, 'Reported'),
        (STATUS_REPORTED_LATE, 'Reported (late)'),
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
        max_length=20, choices=STATUS_CHOICES, default=STATUS_ONGOING)
    completion_date = models.DateField(null=True, blank=True)
    no_longer_on_website = models.BooleanField(default=False)
    first_seen_date = models.DateField(default=date.today)
    updated_date = models.DateField(default=date.today)
    reported_date = models.DateField(null=True, blank=True)
    objects = TrialManager.from_queryset(TrialQuerySet)()

    def __str__(self):
        return "{}: {}".format(self.registry_id, self.title)

    def get_absolute_url(self):
        return reverse('views.trial', args=[self.registry_id])

    def calculated_reported_date(self):
        if self.reported_date:
            return self.reported_date
        qa = self.trialqa_set.first()
        if qa:
            return qa.submitted_to_regulator
        return None

    class Meta:
        ordering = ('completion_date', 'start_date', 'id')

    def compute_metadata(self):
        return compute_metadata(self)


class TrialQA(models.Model):
    """Represents a QA event for a Trial.

    When a trial is submitted to ClinicalTrials.gov, it immediately
    enters a QA process which can take several months.  However, when
    it leaves the QA process, it's submission date is considered the
    date it entered the QA process.

    The QA process involves a ping-pong between sponsor and
    regulator. Each time the regulator returns a trial to the sponsor
    for alterations, the sponsor gets 30 days to respond.

    """
    trial = models.ForeignKey(Trial, on_delete=models.CASCADE)
    submitted_to_regulator = models.DateField()
    returned_to_sponsor = models.DateField(null=True, blank=True)


class Ranking(models.Model):
    sponsor = models.ForeignKey(
        Sponsor, related_name='rankings',
        on_delete=models.CASCADE)
    date = models.DateField(db_index=True)
    rank = models.IntegerField(null=True)
    due = models.IntegerField()
    days_late = models.IntegerField(null=True, blank=True)
    finable_days_late = models.IntegerField(null=True, blank=True)
    total = models.IntegerField()
    overdue = models.IntegerField()
    reported = models.IntegerField()
    reported_late = models.IntegerField()
    reported_on_time = models.IntegerField()
    percentage = models.IntegerField(null=True)

    def __str__(self):
        return "{}: {} at {}% on {}".format(self.rank, self.sponsor, self.percentage, self.date)

    def save(self, *args, **kwargs):
        if self.due:
            self.percentage = float(self.reported)/self.due * 100
        super(Ranking, self).save(*args, **kwargs)

    class Meta:
        unique_together = ('sponsor', 'date',)
        ordering = ('date', 'rank', 'sponsor__name',)
