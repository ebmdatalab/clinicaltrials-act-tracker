import logging
from django.core.management.base import BaseCommand
from django.conf import settings

from ctconvert import create_instance
from ctconvert.convert_data import get_csv_path

from frontend.management_views import stop_instance


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """Trigger building a CSV based on downloaded XML, using a Google
    Compute Engine.

    On completion, the job stores the CSV in Google Cloud Storage, and
    calls the supplied web hook.
    """

    def add_arguments(self, parser):
        parser.add_argument("callback_host", type=str)

    def handle(self, *args, **options):
        callback = "https://{}/management/process_data/?secret={}&input_csv={}".format(
            options["callback_host"],
            settings.HTTP_MANAGEMENT_SECRET,
            "https://storage.googleapis.com/" + get_csv_path(),
        )
        result = create_instance.main(
            "ebmdatalab", "europe-west2-a", "ctgov-converter", callback, wait=False
        )
        print(result)
