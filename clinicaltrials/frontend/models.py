from datetime import date
from datetime import timedelta

from django.db import connection
from django.db import models
from django.db import transaction
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
        return self.with_trials_due().with_trials_unreported()

    def with_trials_reported_early(self):
        return self.with_trials_reported().filter(
            trial__completion_date__gt=date.today())


class TrialQuerySet(models.QuerySet):
    def due(self):
        return self.filter(results_due=True)

    def not_due(self):
        return self.filter(results_due=False)

    def unreported(self):
        return self.filter(has_results=False)

    def reported(self):
        return self.filter(has_results=True)

    def overdue(self):
        return self.due().unreported()

    def reported_early(self):
        return self.reported().filter(completion_date__gt=date.today())


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
    sponsor = models.ForeignKey(
        Sponsor,
        on_delete=models.CASCADE)
    registry_id = models.CharField(max_length=100, unique=True)
    publication_url = models.URLField()
    title = models.TextField()
    has_exemption = models.BooleanField(default=False)
    start_date = models.DateField()
    results_due = models.BooleanField(default=False, db_index=True)
    has_results = models.BooleanField(default=False, db_index=True)
    completion_date = models.DateField(null=True, blank=True)
    objects = TrialQuerySet.as_manager()

    def __str__(self):
        return "{}: {}".format(self.registry_id, self.title)


    @property
    def status(self):
        if Trial.objects.overdue().filter(pk=self.pk).first():
            return "overdue"
        elif Trial.objects.not_due().filter(pk=self.pk).first():
            # XXX doesn't work
            return "not due"
        elif Trial.objects.reported().filter(pk=self.pk).first():
            return "reported"
        elif Trial.objects.reported_early().filter(pk=self.pk).first():
            return "reported early"


class RankingManager(models.Manager):
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
