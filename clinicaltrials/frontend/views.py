import logging
import time

from django.shortcuts import render
from django.conf import settings
from django.http import HttpResponse

from . import models

#############################################################################
# Index page

def index(request):
    context = {'scores': models.Ranking.objects.current_ranks()}
    return render(request, "index.html", context=context)


#############################################################################
# Sponsor page

def sponsor(request, slug):
    sponsor = models.get_sponsor(slug).copy()
    sponsor['unreported_trials'] = models.get_trials_for_sponsor(slug, 'unreported')
    sponsor['reported_trials'] = models.get_trials_for_sponsor(slug, 'reported')
    return render(request, 'sponsor.html', context=sponsor)
