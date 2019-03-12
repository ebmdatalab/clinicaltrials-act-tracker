from datetime import date
from lxml.etree import tostring
import csv
import datetime
import logging
import re

from django.db import transaction
from django.db.models import Sum
from django.db import connection
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from frontend.models import Trial
from frontend.models import TrialQA
from frontend.models import Sponsor
from frontend.models import Ranking
from frontend.models import date
import requests
from lxml import html
import dateparser


logger = logging.getLogger(__name__)

# The date cc.gov first started recording cancellations
EARLIEST_CANCELLATION_DATE = date(2018, 7, 5)

def set_qa_metadata(trial):
    """Scrape `Results Submitted` tab on website for interim reporting
    (this means results have been submitted at some point, and are
    under QA).

    Store this data in a TrialQA table

    """
    registry_id = trial.registry_id
    url = "https://clinicaltrials.gov/ct2/show/results/{}".format(registry_id)
    content = html.fromstring(requests.get(url).text)
    table = content.xpath("//table[.//th//text()[contains(., 'Submission Cycle')]]")
    if table:
        for row in table[0].xpath(".//tr"):
            if len(row.xpath(".//td")) == 0:
                continue
            else:
                # if Cancelled, loop over submitted dates. See #146
                # for a description of cancellations
                cancelled = re.findall(
                    r"\n\s+([^<>]*)<br/>.*?cancell?ed.*? (?:-|on) (.*?)\)<br/>",
                    tostring(row).decode('utf8').replace("&#13;", ""), # carriage return
                    re.I|re.DOTALL)
                # Oh god, sometimes it's returned and cancelled on the
                # same day or something
                for submitted_date, cancelled_date in cancelled:
                    submitted_date = dateparser.parse(submitted_date)
                    if "unknown" in cancelled_date.lower():
                        cancelled_date = EARLIEST_CANCELLATION_DATE
                        cancellation_date_inferred = True
                    else:
                        cancelled_date = dateparser.parse(cancelled_date)
                        cancellation_date_inferred = False
                    logger.info(
                        "Setting cancellation info for %s: %s -> %s",
                        trial,
                        submitted_date,
                        cancelled_date)
                    # Assumes you can't submit twice on same day
                    qa, _ = TrialQA.objects.get_or_create(
                        submitted_to_regulator=submitted_date,
                        trial=trial)
                    qa.cancelled_by_sponsor = cancelled_date
                    qa.cancellation_date_inferred = cancellation_date_inferred
                    qa.save()

                # Take the date on the last line, to cater for cases
                # where there are many dates (specifically,
                # cancellation; but given this was added to the output
                # unexpectedly, and similar additions may come in the
                # future, defaulting to the most recent date is the
                # most conservative approach)
                submitted = [
                    x.strip()
                    for x in row.xpath(".//td[1]")[0].text_content().split("\n")
                    if x.strip()][-1]
                if re.findall(r"cancell?ed", submitted, re.I):
                    # The last event was a cancellation; no further submissions
                    continue
                submitted = submitted and dateparser.parse(submitted) or None
                returned = row.xpath(".//td[2]")[0].text.strip()
                returned = returned and dateparser.parse(returned) or None
                qa, created = TrialQA.objects.get_or_create(
                    submitted_to_regulator=submitted,
                    trial=trial)
                if returned:
                    qa.returned_to_sponsor = returned
                    qa.save()
    else:
        trial.trialqa_set.all().delete()


def _compute_ranks():
    sql = ("WITH ranked AS (SELECT date, ranking.id, RANK() OVER ("
           "  PARTITION BY date "
           "ORDER BY percentage DESC"
           ") AS computed_rank "
           "FROM frontend_ranking ranking WHERE percentage IS NOT NULL "
           "AND date = %s"
           ") ")

    sql += ("UPDATE "
            " frontend_ranking "
            "SET "
            " rank = ranked.computed_rank "
            "FROM ranked "
            "WHERE ranked.id = frontend_ranking.id AND ranked.date = frontend_ranking.date")
    on_date = Sponsor.objects.latest('updated_date').updated_date
    with connection.cursor() as c:
            c.execute(sql, [on_date])


def set_current_rankings():
    """Compute a ranking for each sponsor, which aggregates statistics
    about their trials and then puts them in ranked order.

    """
    with transaction.atomic():
        for sponsor in Sponsor.objects.all():
            due = Trial.objects.due().filter(
                sponsor=sponsor).count()
            reported = Trial.objects.reported().filter(
                sponsor=sponsor).count()
            reported_late = Trial.objects.reported_late().filter(
                sponsor=sponsor).count()
            reported_on_time = Trial.objects.reported_on_time().filter(
                sponsor=sponsor).count()
            overdue = Trial.objects.overdue().filter(
                sponsor=sponsor).count()
            total = sponsor.trial_set.visible().count()
            days_late = sponsor.trial_set.visible().aggregate(
                total_days_late=Sum('days_late'))['total_days_late']
            finable_days_late = sponsor.trial_set.visible().aggregate(
                total_finable_days_late=Sum('finable_days_late'))['total_finable_days_late']
            d = {
                'due': due,
                'reported': reported,
                'total': total,
                'date': sponsor.updated_date,
                'days_late': days_late,
                'overdue': overdue,
                'reported_late': reported_late,
                'reported_on_time': reported_on_time,
                'finable_days_late': finable_days_late
            }
            ranking = sponsor.rankings.filter(
                date=sponsor.updated_date)
            if len(ranking) == 0:
                ranking = sponsor.rankings.create(**d)
            else:
                assert len(ranking) == 1
                ranking.update(**d)
        _compute_ranks()


def truthy(val):
    """Turn a one or zero value into a boolean.
    """
    return bool(int(val))


class Command(BaseCommand):
    help = '''Import a CSV that has been generated by the `load_data.py` script.

    Each import updates existing Trials and Sponsors in-place with new data.
    '''
    def add_arguments(self, parser):
        parser.add_argument(
            '--input-csv',
            type=str)

    def handle(self, *args, **options):
        f = open(options['input_csv'])
        logger.info("Creating new trials and sponsors from %s", options['input_csv'])
        with transaction.atomic():
            # We don't use auto_now on models for `today`, purely so
            # we can mock this in tests.
            today = date.today()
            for row in csv.DictReader(f):
                # Create / update sponsor
                d = {
                    'name': row['sponsor'],
                    'is_industry_sponsor': row['sponsor_type'] == 'Industry',
                    'updated_date': today
                }
                sponsor, created = Sponsor.objects.get_or_create(
                    pk=slugify(row['sponsor']), defaults=d)
                if not created:
                    sponsor.updated_date = today
                    sponsor.is_industry_sponsor = d['is_industry_sponsor']
                    sponsor.save()

                # Create / update Trial
                d = {
                    'registry_id': row['nct_id'],
                    'publication_url': row['url'],
                    'title': row['title'],
                    'has_exemption': truthy(row['has_certificate']),
                    'has_results': truthy(row['has_results']),
                    'results_due': truthy(row['results_due']),
                    'is_pact': truthy(row['included_pact_flag']),
                    'sponsor_id': sponsor.pk,
                    'start_date': row['start_date'],
                    'first_seen_date': today,
                    'updated_date': today,
                    'reported_date': row['results_submitted_date'] or None,
                }
                if row['available_completion_date']:
                    d['completion_date'] = row['available_completion_date']
                instance, created = Trial.objects.get_or_create(
                    registry_id=row['nct_id'], defaults=d)
                if not created:
                    for attr, value in d.items():
                        if attr != 'first_seen_date':
                            setattr(instance, attr, value)
                    instance.updated_date = today
                    instance.save()


        # Now scrape trials that might be in QA (these would be
        # flagged as having no results, but if in QA we consider
        # them submitted until QA finishes)
        possible_results = Trial.objects.filter(results_due=True, has_results=False)
        logger.info("Scraping %s trials for QA metadata", possible_results.count())
        for trial in possible_results:
            set_qa_metadata(trial)

        # Update the status of trials that no longer appear in the dataset
        zombies = Trial.objects.filter(
            updated_date__lt=today).exclude(status=Trial.STATUS_NO_LONGER_ACT)
        logger.info("Marking %s zombie trials", zombies.count())
        zombies.update(
            status=Trial.STATUS_NO_LONGER_ACT, updated_date=today)

        # This should only happen after Trial statuses have been set
        logger.info("Setting current rankings")
        set_current_rankings()
