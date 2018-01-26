from datetime import date
from datetime import timedelta

from django.db import connection
from django.db import models
from django.db import transaction
from django.db.models import F
from django.utils.text import slugify
from django.utils.dateparse import parse_date
from django.urls import reverse


class SponsorQuerySet(models.QuerySet):
    def annotated(self):
        return self.annotate(num_trials=models.Count('trial'))

    def with_trials_due(self):
        return self.filter(
            trial__results_due=True
        ).annotated()

    def with_trials_unreported(self):
        return self.filter(
            trial__has_results=False
        ).annotated()

    def with_trials_reported(self):
        return self.filter(
            trial__has_results=True
        ).annotated()

    def with_trials_overdue(self):
        return self.filter(
            trial__results_due=True,
            trial__has_results=False
        ).annotated()

    def with_trials_reported_late(self):
        return self.with_trials_reported().filter(
            trial__reported_date__gt=F('trial__completion_date') + timedelta(days=30))


class TrialQuerySet(models.QuerySet):
    def due(self):
        return self.filter(results_due=True)

    def not_due(self):
        return self.filter(results_due=False)

    def unreported(self):
        return self.filter(has_results=False)

    def reported(self):
        return self.filter(status='reported')

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
    objects = SponsorQuerySet.as_manager()

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
        return TrialQuerySet(Trial).filter(sponsor=self)


class Trial(models.Model):
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
    # "probable" ACT
    is_pact = models.BooleanField(default=False)
    start_date = models.DateField()
    results_due = models.BooleanField(default=False, db_index=True)
    has_results = models.BooleanField(default=False, db_index=True)
    days_late = models.IntegerField(default=None, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ongoing')
    completion_date = models.DateField(null=True, blank=True)

    first_seen_date = models.DateField(default=date.today)
    updated_date = models.DateField(default=date.today)
    reported_date = models.DateField(null=True, blank=True)
    objects = TrialQuerySet.as_manager()

    def __str__(self):
        return "{}: {}".format(self.registry_id, self.title)

    def save(self, *args, **kwargs):
        self.days_late = self.get_days_late()
        self.status = self.get_status()
        super(Trial, self).save(*args, **kwargs)

    def get_days_late(self):
        days_late = None
        if self.results_due:
            if self.has_results:
                if self.reported_date and self.completion_date:
                    # Normalise from strings, as this method may be called
                    # before the object has been saved to the databasse
                    if isinstance(self.reported_date, str):
                        self.reported_date = parse_date(self.reported_date)
                    if isinstance(self.completion_date, str):
                        self.completion_date = parse_date(self.completion_date)
                    days_late = max([
                        (self.reported_date
                         - self.completion_date
                         - timedelta(days=30)).days,
                        0])
            elif self.completion_date:
                days_late = max([
                    (date.today()
                     - parse_date(self.completion_date)
                     - timedelta(days=30)).days,
                    0])
        return days_late


    def get_status(self):
        if self.results_due and not self.has_results:
            status = 'overdue'
        elif not self.results_due and not self.has_results:
            status = 'ongoing'
        elif self.has_results \
             and self.reported_date \
             and self.days_late \
             and self.days_late > 0:
            status = 'reported-late'
        elif self.has_results and self.results_due:
            status = 'reported'
        elif self.has_results and not self.results_due:
            status = 'reported-early'
        return status

    class Meta:
        ordering = ('completion_date',)



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
