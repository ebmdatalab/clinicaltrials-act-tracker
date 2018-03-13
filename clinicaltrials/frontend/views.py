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


def current_and_prev(field_name, date, prev_date):
    current = Ranking.objects.filter(date=date).aggregate(Sum(field_name))[field_name + '__sum']
    if prev_date:
        prev = Ranking.objects.filter(date=prev_date).aggregate(Sum(field_name))[field_name + '__sum']
    else:
        prev = 0
    return (current, prev)


def get_performance(sponsor_slug=None, date=None):
    """Get a dictionary of top-line performance metrics.
    """
    if sponsor_slug is None:
        queryset = Ranking.objects.all()
    else:
        queryset = Ranking.objects.filter(sponsor__slug=sponsor_slug)
    if date is None:
        date = queryset.latest('date').date
    prev_ranking = queryset.order_by('-date')\
                               .filter(date__lt=date)\
                               .distinct('date')\
                               .only('date')\
                               .first()
    if prev_ranking:
        prev_date = prev_ranking.date
    else:
        prev_date = None
    due, _ = current_and_prev('due', date, prev_date)
    reported, _ = current_and_prev('reported', date, prev_date)
    days_late, _ = current_and_prev('finable_days_late', date, prev_date)
    late, late_prev = current_and_prev('reported_late', date, prev_date)
    overdue, overdue_prev = current_and_prev('overdue', date, prev_date)
    on_time, on_time_prev = current_and_prev('reported_on_time', date, prev_date)
    fines_str = '$0'
    if days_late:
        fines_str = "${:,}".format(days_late * settings.FINE_PER_DAY)
    return {
        'due': due,
        'reported': reported,
        'days_late': days_late,
        'fines_str': fines_str,
        'overdue_today': overdue - overdue_prev,
        'late_today': late - late_prev,
        'on_time_today': on_time - on_time_prev
    }


@api_view()
@permission_classes((permissions.AllowAny,))
def performance(request):
    queryset = Ranking.objects.all()
    d = get_performance(request.GET.get('sponsor', None))
    return Response(d)


def latest_overdue(request):
    context = {
        'title': 'Who’s sharing their clinical trial results?',
        'status_choices': Trial.objects.status_choices()
    }
    return render(request, "latest.html", context=context)

#############################################################################
# Rankings page

def rankings(request):
    context = {
        'title': "Who’s sharing their clinical trial results?"
    }
    return render(request, "rankings.html", context=context)


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
               'title': "All individual trials at {}".format(sponsor),
               'status_choices': status_choices,
               'fine': fine
    }
    return render(request, 'sponsor.html', context=context)


def trials(request):
    trials = Trial.objects.visible()
    #f = TrialStatusFilter(request.GET, queryset=sponsor.trials())
    context = {'sponsor': trials,
               'title': "All individual Trials",
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
    due_date = trial.calculated_due_date()
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
