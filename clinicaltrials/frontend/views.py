import logging
import time

from django.shortcuts import render
from django.conf import settings
from django.http import HttpResponse

from frontend.models import Ranking
from frontend.models import Sponsor


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
    context = {'sponsor': Sponsor.objects.get(slug=slug)}
    return render(request, 'sponsor.html', context=context)
