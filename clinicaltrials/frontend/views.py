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
    context = {'scores': Ranking.objects.current_ranks()}
    return render(request, "index.html", context=context)


#############################################################################
# Sponsor page

def sponsor(request, slug):
    context = {'sponsor': Sponsor.objects.get(slug=slug)}
    return render(request, 'sponsor.html', context=context)
