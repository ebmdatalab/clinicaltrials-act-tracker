import logging

from django.conf import settings
from django.utils.dateparse import parse_date

from common import utils

from frontend.models import Ranking


logger = logging.getLogger(__name__)


def google_tracking_id(request):
    google_tracking_id = None
    if hasattr(settings, 'GOOGLE_TRACKING_ID'):
        google_tracking_id = settings.GOOGLE_TRACKING_ID
    else:
        logger.warn("No GOOGLE_TRACKING_ID set")
    return {'GOOGLE_TRACKING_ID': google_tracking_id}


def next_planned_update(request):
    return {'NEXT_PLANNED_UPDATE': parse_date(settings.NEXT_PLANNED_UPDATE)}
