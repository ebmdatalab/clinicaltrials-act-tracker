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
    return render(request, "index.html")


#############################################################################
# Sponsor page

def sponsor(request, slug):
    sponsor = Sponsor.objects.get(slug=slug)
    #f = TrialStatusFilter(request.GET, queryset=sponsor.trials())
    context = {'sponsor': sponsor,
               'status_choices': Trial.objects.filter(sponsor=sponsor).status_choices_with_counts()}
    return render(request, 'sponsor.html', context=context)


def trials(request):
    trials = Trial.objects.all()
    #f = TrialStatusFilter(request.GET, queryset=sponsor.trials())
    context = {'sponsor': trials,
               'status_choices': Trial.objects.status_choices_with_counts()}
    return render(request, 'trials.html', context=context)
