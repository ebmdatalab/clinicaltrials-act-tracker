from datetime import date

from django.db import models
from django.utils.text import slugify


class SponsorQuerySet(models.QuerySet):
    def annotated(self):
        return self.annotate(num_trials=models.Count('trials'))

    def with_trials_due(self):
        return self.filter(
            trials__due_date__lte=date.today()
        ).annotated()

    def with_trials_unreported(self):
        return self.filter(
            trials__completion_date__isnull=True,
            trials__isnull=False
        ).annotated()

    def with_trials_reported(self):
        return self.filter(
            trials__completion_date__lte=date.today()
        ).annotated()

    def with_trials_overdue(self):
        return self.filter(
            trials__due_date__lte=date.today(),
            trials__completion_date__isnull=True,
            trials__isnull=False
        ).annotated()

    def with_trials_reported_early(self):
        return self.filter(
            trials__completion_date__lte=date.today(),
            trials__due_date__gt=date.today()
        ).annotated()


class TrialQuerySet(models.QuerySet):
    def due(self):
        return self.filter(due_date__lte=date.today())

    def unreported(self):
        return self.filter(completion_date__isnull=True)

    def reported(self):
        return self.filter(completion_date__lte=date.today())

    def overdue(self):
        return self.due().unreported()

    def reported_early(self):
        return self.reported().filter(due_date__gt=date.today())



class Sponsor(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField()
    objects = SponsorQuerySet.as_manager()

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super(Sponsor, self).save(*args, **kwargs)


class Trial(models.Model):
    sponsor = models.ForeignKey(Sponsor, related_name='trials')
    registry_id = models.CharField(max_length=50, unique=True)
    publication_url = models.URLField()
    title = models.TextField()
    has_exemption = models.BooleanField(default=False)
    start_date = models.DateField()
    due_date = models.DateField()
    completion_date = models.DateField(null=True, blank=True)
    objects = TrialQuerySet.as_manager()
