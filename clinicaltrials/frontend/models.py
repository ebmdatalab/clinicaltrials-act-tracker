from datetime import date
from datetime import timedelta

from django.db import connection
from django.db import models
from django.db import transaction
from django.utils.text import slugify
from django.utils.dateparse import parse_date


class SponsorQuerySet(models.QuerySet):
    def annotated(self):
        return self.annotate(num_trials=models.Count('trial'))

    def with_trials_due(self):
        return self.filter(
            trial__due_date__lte=date.today()
        ).annotated()

    def with_trials_unreported(self):
        return self.filter(
            trial__completion_date__isnull=True,
            trial__isnull=False
        ).annotated()

    def with_trials_reported(self):
        return self.filter(
            trial__completion_date__lte=date.today()
        ).annotated()

    def with_trials_overdue(self):
        return self.filter(
            trial__due_date__lte=date.today(),
            trial__completion_date__isnull=True,
            trial__isnull=False
        ).annotated()

    def with_trials_reported_early(self):
        return self.filter(
            trial__completion_date__lte=date.today(),
            trial__due_date__gt=date.today()
        ).annotated()


class TrialQuerySet(models.QuerySet):
    def due(self):
        return self.filter(due_date__lte=date.today())

    def not_due(self):
        return self.filter(due_date__gt=date.today())

    def unreported(self):
        return self.filter(completion_date__isnull=True)

    def reported(self):
        return self.filter(completion_date__isnull=False)

    def overdue(self):
        return self.due().unreported()

    def reported_early(self):
        return self.reported().filter(due_date__gt=date.today())


class Sponsor(models.Model):
    slug = models.SlugField(max_length=200, primary_key=True)
    name = models.CharField(max_length=200)
    major = models.BooleanField(default=False)
    updated_date = models.DateField(default=date.today)
    objects = SponsorQuerySet.as_manager()

    def __str__(self):
        return self.name


    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super(Sponsor, self).save(*args, **kwargs)

    def current_rank(self):
        return self.rankings.get(date=self.updated_date)

    def trials(self):
        return TrialQuerySet(Trial).filter(sponsor=self)

def compute_due_date(start_date):
    if isinstance(start_date, str):
        start_date = parse_date(start_date)
    return start_date + timedelta(days=365)


class Trial(models.Model):
    sponsor = models.ForeignKey(
        Sponsor,
        on_delete=models.CASCADE)
    registry_id = models.CharField(max_length=100, unique=True)
    publication_url = models.URLField()
    title = models.TextField()
    has_exemption = models.BooleanField(default=False)
    start_date = models.DateField()
    due_date = models.DateField()
    completion_date = models.DateField(null=True, blank=True)
    objects = TrialQuerySet.as_manager()

    def __str__(self):
        return "{}: {}".format(self.registry_id, self.title)

    def save(self, *args, **kwargs):
        if self.due_date is None:
            self.due_date = compute_due_date(self.start_date)
        super(Trial, self).save(*args, **kwargs)

    @property
    def status(self):
        if Trial.objects.overdue().filter(pk=self.pk).first():
            return "overdue"
        elif Trial.objects.not_due().filter(pk=self.pk).first():
            return "not due"
        elif Trial.objects.reported().filter(pk=self.pk).first():
            return "reported"
        elif Trial.objects.reported_early().filter(pk=self.pk).first():
            return "reported early"


class RankingManager(models.Manager):
    def _compute_ranks(self):
        sql = ("WITH ranked AS (SELECT ranking.id, RANK() OVER ("
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
                "WHERE ranked.id = frontend_ranking.id")
        with connection.cursor() as c:
                c.execute(sql)

    def set_current(self):
        with transaction.atomic():
            for sponsor in Sponsor.objects.all():
                due = Trial.objects.due().filter(
                    sponsor=sponsor).count()
                reported = Trial.objects.reported().filter(
                        sponsor=sponsor).count()
                try:
                    ranking = sponsor.rankings.get(
                        date=sponsor.updated_date)
                    ranking.due = due
                    ranking.reported = reported
                    ranking.save()
                except Ranking.DoesNotExist:
                    ranking = sponsor.rankings.create(
                        date=sponsor.updated_date,
                        due=due,
                        reported=reported
                    )
            self._compute_ranks()

    def current_ranks(self):
        # XXX not optimal performance-wise
        latest = self.latest('date')
        return self.filter(
            date=latest.date,
            percentage__isnull=False).select_related('sponsor')


class Ranking(models.Model):
    sponsor = models.ForeignKey(
        Sponsor, related_name='rankings',
        on_delete=models.CASCADE)
    date = models.DateField(db_index=True)
    rank = models.IntegerField(null=True)
    due = models.IntegerField()
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
