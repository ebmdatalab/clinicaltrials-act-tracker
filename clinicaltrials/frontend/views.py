import logging
import time

from django.shortcuts import render
from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponse

from . import models

#############################################################################
# Index page

def index(request):
    scores = models.get_scores()
    scores_array = []
    for k, v in scores.items():
        scores_array.append({
            'slug': k,
            'name': models.get_sponsor(k)['sponsor'],
            "percent": v['percent'],
            "due": v['due'],
            "reported": v['reported'],
            "rank": v['rank']
        })
    context = {'scores': scores_array}
    return render(request, "index.html", context=context)


#############################################################################
# Sponsor page

def sponsor(request, slug):
    sponsor = models.get_sponsor(slug).copy()
    sponsor['unreported_trials'] = models.get_trials_for_sponsor(slug, 'unreported')
    sponsor['reported_trials'] = models.get_trials_for_sponsor(slug, 'reported')
    return render(request, 'sponsor.html', context=sponsor)
