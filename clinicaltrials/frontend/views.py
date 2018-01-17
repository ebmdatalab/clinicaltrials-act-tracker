import logging
import time

from django.shortcuts import render
from django.conf import settings
from django.http import HttpResponse

from frontend.models import Ranking
from frontend.models import Sponsor
from frontend.models import Trial


#############################################################################
# Index page

def index(request):
    context = {
        'latest_date': Ranking.objects.latest('date').date
    }
    return render(request, "index.html", context=context)


#############################################################################
# Sponsor page

def sponsor(request, slug):
    sponsor = Sponsor.objects.get(slug=slug)
    #f = TrialStatusFilter(request.GET, queryset=sponsor.trials())
    context = {'sponsor': sponsor,
               'status_choices': Trial.STATUS_CHOICES}
    return render(request, 'sponsor.html', context=context)


def trials(request):
    trials = Trial.objects.all()
    #f = TrialStatusFilter(request.GET, queryset=sponsor.trials())
    context = {'sponsor': trials,
               'status_choices': Trial.STATUS_CHOICES}
    return render(request, 'trials.html', context=context)
