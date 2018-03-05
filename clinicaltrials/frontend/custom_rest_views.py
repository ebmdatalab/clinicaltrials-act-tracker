"""Custom django-rest-framework views to support API representation of
our data.

The names of the ordering and search fields are coupled to names
expected to be used by the DataTables javascript library (see
`site.js`).

See also custom_rest_backends.py

"""
from django.db.models import Count


from rest_framework import serializers
from rest_framework import viewsets
from rest_framework.urlpatterns import format_suffix_patterns

from .custom_filters import RankingFilter
from .custom_filters import TrialStatusFilter
from .custom_filters import SponsorFilter

from frontend.models import Ranking
from frontend.models import Sponsor
from frontend.models import Trial



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
                  'sponsor_name', 'is_industry_sponsor', 'sponsor_slug')


class TrialSerializer(serializers.HyperlinkedModelSerializer):
    sponsor_name = serializers.StringRelatedField(source='sponsor')
    sponsor_slug = serializers.SlugRelatedField(
        source='sponsor', read_only=True, slug_field='slug')

    class Meta:
        model = Trial
        fields = ('registry_id', 'publication_url', 'title', 'has_exemption',
                  'start_date', 'completion_date', 'has_results', 'results_due',
                  'sponsor_name', 'sponsor_slug', 'status', 'is_pact', 'days_late',)


class SponsorSerializer(serializers.HyperlinkedModelSerializer):
    num_trials = serializers.IntegerField()
    class Meta:
        model = Sponsor
        fields = ('slug', 'name', 'is_industry_sponsor', 'updated_date', 'num_trials')



class CSVNonPagingViewSet(viewsets.ModelViewSet):
    """A viewset that allows downloading a CSV in its entirety, rather
    than in pages.

    """
    @property
    def paginator(self):
        """Overrides paginator lookup in base class
        """
        if getattr(self, '_skip_paginator', False):
            p = None
        else:
            p = super(CSVNonPagingViewSet, self).paginator
        return p


    def list(self, request, format=None):
        """Overrides method in base class
        """
        if request.accepted_renderer.media_type == 'text/csv':
            self._skip_paginator = True
            result = super(CSVNonPagingViewSet, self).list(request, format=format)
            self._skip_paginator = False
        else:
            result = super(CSVNonPagingViewSet, self).list(request, format=format)
        return result


class RankingViewSet(CSVNonPagingViewSet):
    queryset = Ranking.objects.select_related('sponsor')
    serializer_class = RankingSerializer
    ordering_fields = ['sponsor__name', 'due', 'reported', 'percentage']
    filter_class = RankingFilter
    search_fields = ('sponsor__name',)


class TrialViewSet(CSVNonPagingViewSet):
    queryset = Trial.objects.visible().select_related('sponsor').all()
    serializer_class = TrialSerializer
    ordering_fields = ['status', 'sponsor__name', 'registry_id',
                       'title', 'completion_date', 'days_late']
    filter_class = TrialStatusFilter
    search_fields = ('title', 'sponsor__name',)


class SponsorViewSet(CSVNonPagingViewSet):
    queryset = Sponsor.objects.annotate(num_trials=Count('trial'))
    serializer_class = SponsorSerializer
    filter_class = SponsorFilter
    search_fields = ('name',)
