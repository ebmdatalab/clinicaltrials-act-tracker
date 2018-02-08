import csv
import datetime

from django.db import transaction
from django.core.management.base import BaseCommand
from frontend.models import Trial
from frontend.models import TrialQA
from frontend.models import Sponsor
from frontend.models import Ranking
from frontend.models import date
import requests
from lxml import html
import dateparser


def set_qa_metadata(trial):
    registry_id = trial.registry_id
    url = "https://clinicaltrials.gov/ct2/show/results/{}".format(registry_id)
    content = html.fromstring(requests.get(url).text)
    table = content.xpath("//table[.//th//text()[contains(., 'Submission Cycle')]]")
    if table:
        for row in table[0].xpath(".//tr"):
            if len(row.xpath(".//td")) == 0:
                continue
            else:
                submitted = row.xpath(".//td[1]")[0].text.strip()
                submitted = submitted and dateparser.parse(submitted) or None
                returned = row.xpath(".//td[2]")[0].text.strip()
                returned = returned and dateparser.parse(returned) or None
                TrialQA.objects.get_or_create(
                    submitted_to_regulator=submitted,
                    returned_to_sponsor=returned,
                    trial=trial)


class Command(BaseCommand):
    help = 'XXX'
    # XXX the order matters here and could be better enforced in
    # code. First we get the data, then we scrape data, then we
    # compute status, then we compute ranking.
    def add_arguments(self, parser):
        parser.add_argument(
            '--input-csv',
            type=str)

    def handle(self, *args, **options):
        '''
        '''
        f = open(options['input_csv'])
        with transaction.atomic():
            today = date.today()
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
                        d['first_seen_date'] = today
                        Trial.objects.create(**d)

            # Mark zombie trials
            Trial.objects.filter(updated_date__lt=today).update(no_longer_on_website=True)

            # Now scrape trials that might be in QA (these would be
            # flagged as having no results, but if in QA we consider
            # them submitted until QA finishes)
            print("Fetching trial QA metadata")
            for trial in Trial.objects.filter(results_due=True, has_results=False):
                set_qa_metadata(trial)

            # Next, compute days_late and status for each trial
            print("Computing trial metadata")
            for trial in Trial.objects.all():
                trial.compute_metadata()

            # This should only happen after Trial statuses have been set
            print("Setting current rankings")
            Ranking.objects.set_current()
