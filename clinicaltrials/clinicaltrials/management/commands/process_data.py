import csv
import datetime


from django.db import transaction
from django.core.management.base import BaseCommand
from frontend.models import Trial
from frontend.models import Sponsor
from frontend.models import Ranking


class Command(BaseCommand):
    help = 'Converts CSV to useful JSON formats'

    def add_arguments(self, parser):
        parser.add_argument(
            '--input-csv',
            type=str)

    def handle(self, *args, **options):
        '''
        '''
        f = open(options['input_csv'])
        with transaction.atomic():
            today = datetime.datetime.today()
            Trial.objects.all().delete()
            for row in csv.DictReader(f):
                has_act_flag = int(row['act_flag']) > 0

                if has_act_flag:
                    sponsor, created = Sponsor.objects.get_or_create(
                        name=row['sponsor'])
                    sponsor.updated_date = today
                    sponsor.save()
                    d = {
                        'registry_id': row['nct_id'],
                        'publication_url': row['url'],
                        'title': row['title'],
                        'has_exemption': bool(row['has_certificate']),
                        'sponsor': sponsor,
                        'start_date': row['start_date'],
                        'completion_date': row['available_completion_date']
                    }
                    Trial.objects.create(**d)
            print("Setting current rankings")
            Ranking.objects.set_current()
