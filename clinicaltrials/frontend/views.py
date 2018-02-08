import logging
import time

from django.shortcuts import render
from django.conf import settings
from django.db.models import Sum
from django.db.models import F
from django.http import HttpResponse

from rest_framework.decorators import api_view
from rest_framework.decorators import permission_classes
from rest_framework import permissions
from rest_framework.response import Response

from frontend.models import Ranking
from frontend.models import Sponsor
from frontend.models import Trial


@api_view()
@permission_classes((permissions.AllowAny,))
def performance(request):
    queryset = Trial.objects.all()
    if 'sponsor' in request.GET:
        queryset = queryset.filter(sponsor__slug=request.GET['sponsor'])
    due = queryset.overdue().count()
    reported = queryset.reported().count()
    days_late = queryset.aggregate(Sum(F('days_late')-30))['days_late__sum']
    fines_str = '$0'
    if days_late:
        fines_str = "${:,}".format(days_late * 10000)
    return Response({
        'due': due,
        'reported': reported,
        'days_late': days_late,
        'fines_str': fines_str
    })


#############################################################################
# Index page

def index(request):
    context = {
        'title': "Who’s sharing their clinical trial results?"
    }
    return render(request, "index.html", context=context)


#############################################################################
# Sponsor page

def sponsor(request, slug):
    sponsor = Sponsor.objects.get(slug=slug)
    days_late = sponsor.trial_set.aggregate(Sum(F('days_late')-30))['days_late__sum']
    if days_late:
        fine = days_late * 10000
    else:
        fine = None
    #f = TrialStatusFilter(request.GET, queryset=sponsor.trials())
    context = {'sponsor': sponsor,
               'title': "All of {}'s Applicable Clinical Trials".format(sponsor),
               'status_choices': Trial.objects.filter(
                   sponsor=sponsor).status_choices_with_counts(),
               'fine': fine
    }
    return render(request, 'sponsor.html', context=context)


def trials(request):
    trials = Trial.objects.all()
    #f = TrialStatusFilter(request.GET, queryset=sponsor.trials())
    context = {'sponsor': trials,
               'title': "All Applicable Clinical Trials",
               'status_choices': Trial.objects.status_choices_with_counts()}
    return render(request, 'trials.html', context=context)
