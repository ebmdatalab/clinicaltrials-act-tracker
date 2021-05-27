from datetime import date
import logging

from django.conf import settings
from django.utils.dateparse import parse_date

from common import utils

from frontend.models import Ranking


logger = logging.getLogger(__name__)


def latest_date(request):
    date = Ranking.objects.latest('date').date
    return {'LATEST_DATE': date}


def next_planned_update(request):
    return {'NEXT_PLANNED_UPDATE': parse_date(settings.NEXT_PLANNED_UPDATE)}

def fine_per_day(request):
    return {'FINE_PER_DAY': settings.FINE_PER_DAY}
