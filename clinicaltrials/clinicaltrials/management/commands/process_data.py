import csv
import json
from collections import Counter
from collections import OrderedDict
from collections import defaultdict
from datetime import datetime

from django.utils.text import slugify
from django.core.management.base import BaseCommand


def add_ranking(scores):
    for slug, score in scores.items():
        score['percent'] = round(float(score['reported']) / score['due'] * 100)
    scores = OrderedDict(sorted(scores.items(), key=lambda x: (0-x[1]['percent'], x[0])))
    unique_percent_vals = list(reversed(list(Counter([x['percent'] for x in scores.values()]))))
    for slug, score in scores.items():
        score['rank'] = unique_percent_vals.index(score['percent']) + 1
    return scores


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
        sponsors = {}

        scores = OrderedDict()
        reported_trials = defaultdict(list)
        unreported_trials = defaultdict(list)
        for row in csv.DictReader(f):
            slug = slugify(row['sponsor'])
            has_act_flag = int(row['act_flag']) > 0

            if has_act_flag:
                sponsors[slug] = {
                    'sponsor': row['sponsor'],
                    'sponsor_slug': slug
                }
                if slug in scores:
                    scores[slug]['due'] += 1
                else:
                    scores[slug] = {}
                    scores[slug]['due'] = 1
                    scores[slug]['reported'] = 0
                d = {
                    'nct_id': row['nct_id'],
                    'trial_url': row['url'],
                    'trial_title': row['title'],
                    'has_certificate': row['has_certificate'],
                    'sponsor': row['sponsor'],
                    'sponsor_slug': slug,
                    'start_date': row['start_date'],
                    'completion_date': row['available_completion_date']
                }
                dt = row['available_completion_date']
                completion_date = dt and datetime.strptime(dt, "%Y-%m-%d")
                if completion_date and completion_date <= datetime.today():
                    scores[slug]['reported'] += 1
                    reported_trials[slug].append(d)
                else:
                    unreported_trials[slug].append(d)
        scores = add_ranking(scores)
        with open('../scores.json', 'w') as fp:
            json.dump(scores, fp, indent=2)
        with open('../reported_trials.json', 'w') as fp:
            json.dump(reported_trials, fp, indent=2)
        with open('../unreported_trials.json', 'w') as fp:
            json.dump(unreported_trials, fp, indent=2)
        with open('../sponsors.json', 'w') as fp:
            json.dump(sponsors, fp, indent=2)
1
