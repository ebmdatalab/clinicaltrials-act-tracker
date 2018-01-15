from django.db.models import Count
from django.urls import include
from django.urls import path
from rest_framework import routers
from rest_framework import serializers
from rest_framework import viewsets
from django_filters import MultipleChoiceFilter
from django_filters import RangeFilter
from django_filters import FilterSet
from django_filters import OrderingFilter

from frontend.models import Ranking
from frontend.models import Trial
from frontend.models import Sponsor
from frontend import views

STATUS_CHOICES = (
    ('due', 'Due'),
    ('overdue', 'Overdue'),
    ('not_due', 'Not yet due'),
    ('reported', 'Reported'),
    ('unreported', 'Not yet reported'),
    ('reported_early', 'Reported early'),
)


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
    status = serializers.SerializerMethodField()
    class Meta:
        model = Trial
        fields = ('registry_id', 'publication_url', 'title', 'has_exemption',
                  'start_date', 'due_date', 'completion_date', 'sponsor', 'status')

    def get_status(self, obj):
        return obj.status


class SponsorSerializer(serializers.HyperlinkedModelSerializer):
    num_trials = serializers.IntegerField()
    class Meta:
        model = Sponsor
        fields = ('slug', 'name', 'is_industry_sponsor', 'updated_date', 'num_trials')


class TrialStatusFilter(FilterSet):
    status = MultipleChoiceFilter(
        label='Trial status',
        method='status_filter',
        choices=STATUS_CHOICES)

    def status_filter(self, queryset, name, value):
        if 'due' in value:
            queryset = queryset.due()
        if 'overdue' in value:
            queryset = queryset.due()
        if 'not_due' in value:
            queryset = queryset.not_due()
        if 'reported' in value:
            queryset = queryset.reported()
        if 'unreported' in value:
            queryset = queryset.unreported()
        if 'reported_early' in value:
            queryset = queryset.reported_early()
        return queryset

    class Meta:
        model = Trial
        fields = ('has_exemption', 'due_date', 'sponsor',)


class SponsorFilter(FilterSet):
    num_trials = RangeFilter(
        label='With at least this many eligible trials')

    class Meta:
        model = Sponsor
        fields = ('is_industry_sponsor',)


# ViewSets define the view behavior.
class RankingViewSet(viewsets.ModelViewSet):
    queryset = Ranking.objects.current_ranks()
    serializer_class = RankingSerializer
    ordering_fields = '__all__'
    search_fields = ('sponsor__name',)
    # See https://docs.djangoproject.com/en/dev/ref/models/lookups/#module-django.db.models.lookups
    filter_fields = {'percentage': ['gte', 'lte'],
                     'due': ['gte', 'lte'],
                     'sponsor__name': ['icontains'],
                     'sponsor__is_industry_sponsor': ['exact'],
                     'total': ['gte']
    }


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

urlpatterns = [
    path('', views.index),
    path('api/', include(router.urls)),
    path('sponsor/<slug:slug>/', views.sponsor),
    path('api/', include('rest_framework.urls')),
]
