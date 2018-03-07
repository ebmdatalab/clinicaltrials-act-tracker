import logging
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
import os

import mistune

from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.db.models import Sum
from django.db.models import F
from django.http import HttpResponse
from django.http import Http404
from django.template import Template, Context

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
    due = queryset.due().count()
    reported = queryset.reported().count()
    days_late = queryset.aggregate(
        days_late=Sum('finable_days_late'))['days_late']
    fines_str = '$0'
    if days_late:
        fines_str = "${:,}".format(days_late * settings.FINE_PER_DAY)
    latest_date = Ranking.objects.latest('date').date
    due_today = queryset.due().filter(
        updated_date=latest_date).count()
    late_today = queryset.reported_late().filter(
        updated_date=latest_date).count()
    return Response({
        'due': due,
        'reported': reported,
        'days_late': days_late,
        'fines_str': fines_str,
        'due_today': due_today,
        'late_today': late_today
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
    days_late = sponsor.trial_set.aggregate(
        days_late=Sum('finable_days_late'))['days_late']
    if days_late:
        fine = days_late * settings.FINE_PER_DAY
    else:
        fine = None
    status_choices = sponsor.status_choices()
    if len(status_choices) == 1:
        status_choices = []  # don't show options where there's only one choice
    context = {'sponsor': sponsor,
               'title': "All Applicable Clinical Trials at {}".format(sponsor),
               'status_choices': status_choices,
               'fine': fine
    }
    return render(request, 'sponsor.html', context=context)


def trials(request):
    trials = Trial.objects.visible()
    #f = TrialStatusFilter(request.GET, queryset=sponsor.trials())
    context = {'sponsor': trials,
               'title': "All Applicable Clinical Trials",
               'status_choices': Trial.objects.status_choices()}
    return render(request, 'trials.html', context=context)


def trial(request, registry_id=None):
    trial = get_object_or_404(Trial, registry_id=registry_id)
    if trial.status == Trial.STATUS_OVERDUE:
        status_desc ='An overdue trial'
    elif trial.status == Trial.STATUS_ONGOING:
        status_desc = 'An ongoing trial'
    elif trial.status == Trial.STATUS_REPORTED:
        status_desc = 'A reported trial'
    else:
        status_desc = 'A trial that was reported late'
    due_date = trial.completion_date + relativedelta(days=365)
    annotation = _get_full_markdown_path("trials/{}".format(registry_id))
    if os.path.exists(annotation):
        with open(annotation, 'r') as f:
            annotation_html = mistune.markdown(f.read()).split('<hr>')[0]
            annotation_html += "<p><a href='/page/trials/{}'>Read more...</a></p>".format(registry_id)
    else:
        annotation_html = ""
    context = {'trial': trial,
               'title': "{}: {} by {}".format(trial.registry_id, status_desc, trial.sponsor),
               'due_date': datetime.combine(due_date, datetime.min.time()),
               'annotation_html': annotation_html}
    return render(request, 'trial.html', context=context)


def _get_full_markdown_path(path):
    return os.path.join(settings.PROJECT_ROOT, 'pages', path) + ".md"

def static_markdown(request, path):
    full_path = _get_full_markdown_path(path)
    title = full_path.split("/")[-1].replace(".md", "").replace("_", " ").title()
    try:
        with open(full_path, 'r') as f:
            content = "{% extends '_base.html' %}{% block content %}" \
                      + mistune.markdown(f.read()) \
                      + "{% endblock %}"
            t = Template(content)
            html = t.render(Context({'title': title}))
            return HttpResponse(html)
    except OSError:
        raise Http404
