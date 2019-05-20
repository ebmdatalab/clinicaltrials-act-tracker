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
        return self.exclude(
            status=Trial.STATUS_NO_LONGER_ACT).prefetch_related('trialqa_set')

    def due(self):
        return self.visible().filter(status__in=[
            'overdue', 'reported', 'reported-late', 'overdue-cancelled'])

    def not_due(self):
        return self.visible().filter(status='ongoing')

    def unreported(self):
        return self.visible().filter(status__in=[
            'overdue', 'ongoing', 'overdue-cancelled'])

    def reported(self):
        return self.visible().filter(status__in=['reported', 'reported-late'])

    def reported_on_time(self):
        return self.visible().filter(status='reported')

    def reported_late(self):
        return self.visible().filter(status='reported-late')

    def overdue(self):
        return self.visible().filter(status__in=[
            'overdue', 'overdue-cancelled'])

    def reported_early(self):
        return self.reported().filter(reported_date__lt=F('completion_date'))

    def overdue_today(self):
        return self.visible() \
                   .filter(status__in=[
                       Trial.STATUS_OVERDUE, Trial.STATUS_OVERDUE_CANCELLED]) \
                   .exclude(previous_status__in=[
                       Trial.STATUS_OVERDUE, Trial.STATUS_OVERDUE_CANCELLED])

    def no_longer_overdue_today(self):
        # All trials except no-longer-overdue trials are updated every
        # import run, so comparing previous and current states to
        # detect current changes Just Works.  However, once a trial
        # becomes no-longer-overdue, we stop updating it. Therefore,
        # this query has to search non-current trials and filter by
        # date, explicitly.
        today = Ranking.objects.latest('date').date
        return self.filter(previous_status__in=[
                       Trial.STATUS_OVERDUE, Trial.STATUS_OVERDUE_CANCELLED]) \
                   .filter(updated_date=today) \
                   .exclude(status__in=[
                       Trial.STATUS_OVERDUE, Trial.STATUS_OVERDUE_CANCELLED])

    def late_today(self):
        return self.visible() \
                   .filter(status=Trial.STATUS_REPORTED_LATE) \
                   .exclude(previous_status=Trial.STATUS_REPORTED_LATE)

    def on_time_today(self):
        return self.visible() \
                   .filter(status=Trial.STATUS_REPORTED) \
                   .exclude(previous_status=Trial.STATUS_REPORTED)


class Trial(models.Model):
    FINES_GRACE_PERIOD = 30
    STATUS_OVERDUE = 'overdue'
    STATUS_ONGOING = 'ongoing'
    STATUS_REPORTED = 'reported'
    STATUS_NO_LONGER_ACT = 'no-longer-act'
    STATUS_REPORTED_LATE = 'reported-late'

    STATUS_OVERDUE_CANCELLED = 'overdue-cancelled'
    STATUS_CHOICES = (
        (STATUS_OVERDUE, 'Overdue'),
        (STATUS_OVERDUE_CANCELLED, 'Overdue (cancelled results)'),
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
    previous_status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_ONGOING,
        null=True, blank=True)
    completion_date = models.DateField(null=True, blank=True)
    #no_longer_on_website = models.BooleanField(default=False)  # XXX delete following migration 0029
    first_seen_date = models.DateField(default=date.today)
    updated_date = models.DateField(default=date.today)
    reported_date = models.DateField(null=True, blank=True)
    objects = TrialManager.from_queryset(TrialQuerySet)()

    class Meta:
        ordering = ('completion_date', 'start_date', 'id')

    def __str__(self):
        return "{}: {}".format(self.registry_id, self.title)

    def get_absolute_url(self):
        return reverse('views.trial', args=[self.registry_id])

    def calculated_due_date(self):
        if self.has_exemption:
            return self.completion_date + relativedelta(years=3)
        return self.completion_date + relativedelta(days=365)

    def calculated_reported_date(self):
        if self.reported_date:
            return self.reported_date
        qa = self.trialqa_set.first()
        if qa:
            return qa.submitted_to_regulator
        return None

    def save(self, *args, **kwargs):
        compute_metadata(self)
        super(Trial, self).save(*args, **kwargs)


class TrialQA(models.Model):
    """Represents a QA event for a Trial.

    When a trial is submitted to ClinicalTrials.gov, it immediately
    enters a QA process which can take several months.  However, when
    it leaves the QA process, its submission date is considered the
    date it entered the QA process.

    The QA process involves a ping-pong between sponsor and
    regulator. Each time the regulator returns a trial to the sponsor
    for alterations, the sponsor gets 30 days to respond.

    """
    trial = models.ForeignKey(Trial, on_delete=models.CASCADE)
    submitted_to_regulator = models.DateField()
    cancelled_by_sponsor = models.DateField(null=True, blank=True)
    cancellation_date_inferred = models.NullBooleanField()
    returned_to_sponsor = models.DateField(null=True, blank=True)
    first_seen_date = models.DateField(default=date.today, null=True)

    class Meta:
        ordering = ('submitted_to_regulator','id',)

    def save(self, *args, **kwargs):
        super(TrialQA, self).save(*args, **kwargs)
        # In the case where a trial has been seen to be overdue for
        # the first time, on the very same day that we've first seen
        # this QA that might cancel the overdue status, then reset the
        # `status` to `ongoing`.
        #
        # This is because we use `previous_status` to mean "status
        # that could have been seen on previous days"; when two state
        # changes originate from two different sources (the
        # ClincialTrials download, and scraping the QA tabs) on the
        # same day, it is (in our current workflow) impossible for the
        # first state change to have been seen.
        #
        # This unpleasant hack is a consequence of the fact our data
        # model really needs refactoring - see the README for context
        # and issue #155 for explanation of this particular wart
        newly_overdue = (self.first_seen_date == self.trial.updated_date
                         and self.trial.previous_status == 'ongoing'
                         and self.trial.status == 'overdue')
        if newly_overdue:
            self.trial.status = self.trial.previous_status
        self.trial.save()   # recomputes metadata


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
    percentage = models.DecimalField(null=True, max_digits=6, decimal_places=2)

    def __str__(self):
        return "{}: {} at {}% on {}".format(self.rank, self.sponsor, self.percentage, self.date)

    def save(self, *args, **kwargs):
        if self.due:
            self.percentage = self.reported * 100.0 / self.due
        else:
            self.percentage = None
        super(Ranking, self).save(*args, **kwargs)

    class Meta:
        unique_together = ('sponsor', 'date',)
        ordering = ('date', 'rank', 'sponsor__name',)
