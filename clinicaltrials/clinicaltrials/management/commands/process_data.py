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
            for row in csv.DictReader(f):
                has_act_flag = int(row['act_flag']) > 0

                if has_act_flag:
                    sponsor, created = Sponsor.objects.get_or_create(
                        name=row['sponsor'])
                    sponsor.updated_date = today
                    existing_sponsor = sponsor.is_industry_sponsor
                    is_industry_sponsor = row['sponsor_type'] == 'Industry'
                    if existing_sponsor is None:
                        sponsor.is_industry_sponsor = is_industry_sponsor
                    else:
                        assert (is_industry_sponsor == existing_sponsor), \
                            "Inconsistent sponsor types for {}".format(sponsor)
                    sponsor.save()
                    trial, created = Trial.objects.get_or_create(
                        registry_id=row['nct_id'])
                    trial.updated_date = today
                    if not created:
                        if bool(row['has_results']) and not trial.has_results:
                            trial.reported_date = today
                    d = {
                        'publication_url': row['url'],
                        'title': row['title'],
                        'has_exemption': bool(row['has_certificate']),
                        'has_results': bool(row['has_results']),
                        'results_due': bool(row['results_due']),
                        'sponsor': sponsor,
                        'start_date': row['start_date'],
                        'completion_date': row['available_completion_date']
                    }
                    trial.update(**d)
            print("Setting current rankings")
            Ranking.objects.set_current()
