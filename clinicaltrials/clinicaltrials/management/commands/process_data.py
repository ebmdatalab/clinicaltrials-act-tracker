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
                has_act_flag = (int(row['act_flag']) > 0 or int(row['included_pact_flag']) > 0)

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
                    d = {
                        'registry_id': row['nct_id'],
                        'publication_url': row['url'],
                        'title': row['title'],
                        'has_exemption': bool(int(row['has_certificate'])),
                        'has_results': bool(int(row['has_results'])),
                        'results_due': bool(int(row['results_due'])),
                        'is_pact': bool(int(row['included_pact_flag'])),
                        'sponsor_id': sponsor.pk,
                        'start_date': row['start_date'],
                        'reported_date': row['results_submitted_date'] or None,
                    }
                    if row['available_completion_date']:
                        d['completion_date'] = row['available_completion_date']
                    trial_set = Trial.objects.filter(registry_id=row['nct_id'])
                    trial = trial_set.first()
                    if trial:
                        d['updated_date'] = today
                        trial_set.update(**d)
                    else:
                        Trial.objects.create(**d)

            print("Setting current rankings")
            Ranking.objects.set_current()
# clinical_study.clinical_results non-null and
