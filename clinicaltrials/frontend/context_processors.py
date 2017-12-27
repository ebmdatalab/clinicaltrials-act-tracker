import logging

from django.conf import settings

from common import utils

logger = logging.getLogger(__name__)


def google_tracking_id(request):
    google_tracking_id = None
    if hasattr(settings, 'GOOGLE_TRACKING_ID'):
        google_tracking_id = settings.GOOGLE_TRACKING_ID
    else:
        logger.warn("No GOOGLE_TRACKING_ID set")
    return {'GOOGLE_TRACKING_ID': google_tracking_id}
