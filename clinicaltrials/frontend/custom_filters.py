"""Custom django-filters.  Used by our custom django-rest-framework
views (q.v.)

"""
from django_filters import AllValuesFilter
from django_filters import MultipleChoiceFilter
from django_filters import BooleanFilter
from django_filters import ChoiceFilter
from django_filters import RangeFilter
from django_filters import FilterSet
from django_filters import OrderingFilter
from django_filters.widgets import QueryArrayWidget

from frontend.models import Ranking
from frontend.models import Sponsor
from frontend.models import Trial


class TrialStatusFilter(FilterSet):
    TODAY_CHOICES = (("2", "Yes"), ("", "Unknown"))
    status = MultipleChoiceFilter(
        label="Trial status", choices=Trial.STATUS_CHOICES, widget=QueryArrayWidget
    )
    is_overdue_today = ChoiceFilter(
        label="Is overdue today", method="filter_today", choices=TODAY_CHOICES
    )
    is_no_longer_overdue_today = ChoiceFilter(
        label="Is no longer overdue today", method="filter_today", choices=TODAY_CHOICES
    )

    def filter_today(self, queryset, name, value):
        if str(value) == "2":  # A truthy value per django-rest-api/django-filters
            if name == "is_overdue_today":
                queryset = queryset.overdue_today()
            elif name == "is_no_longer_overdue_today":
                queryset = queryset.no_longer_overdue_today()
        return queryset

    class Meta:
        model = Trial
        fields = (
            "has_exemption",
            "has_results",
            "results_due",
            "sponsor",
            "status",
            "is_pact",
            "is_overdue_today",
            "is_no_longer_overdue_today",
        )


class SponsorFilter(FilterSet):
    num_trials = RangeFilter(label="With at least this many eligible trials")

    class Meta:
        model = Sponsor
        fields = ("is_industry_sponsor",)


class RankingFilter(FilterSet):
    with_trials_due = BooleanFilter(
        label="Sponsor has trials due", method="with_trials_due_filter"
    )

    def with_trials_due_filter(self, queryset, name, value):
        if value is True:
            # XXX isn't having a percentage equivalent?
            queryset = queryset.filter(sponsor__trial__results_due=True).distinct()
        return queryset

    class Meta:
        model = Ranking
        # See https://docs.djangoproject.com/en/dev/ref/models/lookups/#module-django.db.models.lookups
        fields = {
            "percentage": ["gte", "lte"],
            "due": ["gte", "lte"],
            "date": ["exact"],
            "sponsor__name": ["icontains"],
            "sponsor__is_industry_sponsor": ["exact"],
            "total": ["gte"],
        }
