from datetime import date
from django.db.models import Count
from django.urls import include
from django.urls import path
from rest_framework import routers
from rest_framework import serializers
from rest_framework import viewsets
from django_filters import AllValuesFilter
from django_filters import MultipleChoiceFilter
from django_filters import BooleanFilter
from django_filters import RangeFilter
from django_filters import FilterSet
from django_filters import OrderingFilter
from django_filters.widgets import QueryArrayWidget
from django.contrib.sitemaps import GenericSitemap
from django.contrib.sitemaps import Sitemap
from django.contrib.sitemaps.views import sitemap
from django.urls import reverse

from frontend.models import Ranking
from frontend.models import Trial
from frontend.models import Sponsor
from frontend.models import SponsorQuerySet
from frontend import views


class IsIndustrySponsorField(serializers.RelatedField):
    def to_representation(self, value):
        return value.is_industry_sponsor


# Serializers define the API representation.
class RankingSerializer(serializers.HyperlinkedModelSerializer):
    sponsor_name = serializers.StringRelatedField(source='sponsor')
    sponsor_slug = serializers.SlugRelatedField(
        source='sponsor', read_only=True, slug_field='slug')
    is_industry_sponsor = IsIndustrySponsorField(read_only=True, source='sponsor')

    class Meta:
        model = Ranking
        fields = ('date', 'rank', 'due', 'reported', 'total', 'percentage',
                  'sponsor_slug', 'sponsor_name', 'is_industry_sponsor')


class TrialSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Trial
        fields = ('registry_id', 'publication_url', 'title', 'has_exemption',
                  'start_date', 'completion_date', 'has_results', 'results_due',
                  'sponsor', 'status')


class SponsorSerializer(serializers.HyperlinkedModelSerializer):
    num_trials = serializers.IntegerField()
    class Meta:
        model = Sponsor
        fields = ('slug', 'name', 'is_industry_sponsor', 'updated_date', 'num_trials')


class TrialStatusFilter(FilterSet):
    status = MultipleChoiceFilter(
        label='Trial status',
        choices=Trial.STATUS_CHOICES,
        widget=QueryArrayWidget)

    class Meta:
        model = Trial
        fields = ('has_exemption', 'has_results', 'results_due', 'sponsor', 'status',)


class SponsorFilter(FilterSet):
    num_trials = RangeFilter(
        label='With at least this many eligible trials')

    class Meta:
        model = Sponsor
        fields = ('is_industry_sponsor',)



class RankingFilter(FilterSet):
    with_trials_due = BooleanFilter(
        label='Sponsor has trials due',
        method='with_trials_due_filter'
    )


    def with_trials_due_filter(self, queryset, name, value):
        if value is True:
            # XXX isn't having a percentage equivalent?
            queryset = queryset.filter(sponsor__trial__results_due=True).distinct()
        return queryset


    class Meta:
        model = Ranking
        fields = {'percentage': ['gte', 'lte'],
                  'due': ['gte', 'lte'],
                  'sponsor__name': ['icontains'],
                  'sponsor__is_industry_sponsor': ['exact'],
                  'total': ['gte'],
        }

# ViewSets define the view behavior.
class RankingViewSet(viewsets.ModelViewSet):
    # Let's make this selectable too: date, and if excluding percentage.
    queryset = Ranking.objects.select_related('sponsor')
    serializer_class = RankingSerializer
    ordering_fields = '__all__'
    filter_class = RankingFilter
    search_fields = ('sponsor__name',)
    # See https://docs.djangoproject.com/en/dev/ref/models/lookups/#module-django.db.models.lookups


class TrialViewSet(viewsets.ModelViewSet):
    queryset = Trial.objects.all()
    serializer_class = TrialSerializer
    filter_class = TrialStatusFilter
    search_fields = ('title', 'sponsor__name',)


class SponsorViewSet(viewsets.ModelViewSet):
    queryset = Sponsor.objects.annotate(num_trials=Count('trial'))
    serializer_class = SponsorSerializer
    filter_class = SponsorFilter
    search_fields = ('name',)

# Routers provide an easy way of automatically determining the URL conf.
router = routers.DefaultRouter()
router.register(r'trials', TrialViewSet, base_name='trials')
router.register(r'rankings', RankingViewSet)
router.register(r'sponsors', SponsorViewSet)

class StaticViewSitemap(Sitemap):
    priority = 0.5
    changefreq = 'weekly'

    def items(self):
        return ['index',]

    def location(self, item):
        return reverse(item)

urlpatterns = [
    path('', views.index, name='index'),
    path('api/', include(router.urls)),
    path('trials/', views.trials, name='views.trials'),
    path('sponsor/<slug:slug>/', views.sponsor, name='views.sponsor'),
    path('api/', include('rest_framework.urls')),
    path('sitemap.xml', sitemap,
         {'sitemaps': {
             'static': StaticViewSitemap,
             'sponsor': GenericSitemap(
                 {'queryset': Sponsor.objects.all(),
                  'date_field': 'updated_date'}, priority=0.5),
         }},
         name='django.contrib.sitemaps.views.sitemap')
]
