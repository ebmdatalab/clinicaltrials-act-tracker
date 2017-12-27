from django.db import models

import json
import collections

headings_data = None
all_sponsors_data = None
major_sponsors_data = None
all_trials_data = None

sponsor_by_slug = None
trials_by_sponsor_slug = None


def get_headlines():
    global headings_data
    if not headings_data:
        headings_data = json.load(open('../../euctr-tracker-data/headline.json'))
    return headings_data


def get_all_sponsors():
    global all_sponsors_data
    if not all_sponsors_data:
        all_sponsors_data = json.load(open('../../euctr-tracker-data/all_sponsors.json'))
        all_sponsors_data.sort(key=lambda s: s['total_due'], reverse=True)
    return all_sponsors_data

def get_major_sponsors():
    global major_sponsors_data

    if not major_sponsors_data:
        all_sponsors = get_all_sponsors()
        major_sponsors_data = [ x for x in all_sponsors if x['major'] == 1 ]
        major_sponsors_data.sort(key=lambda s: s['total_trials'], reverse=True)

    return major_sponsors_data



def get_all_trials():
    global all_trials_data
    if not all_trials_data:
        all_trials_data = json.load(open('../../euctr-tracker-data/all_trials.json'))
    return all_trials_data


def get_sponsor(slug):
    global sponsor_by_slug
    if not sponsor_by_slug:
        all_sponsors_data = get_all_sponsors()
        sponsor_by_slug = { x["slug"]: x for x in all_sponsors_data }
    return sponsor_by_slug[slug]

def get_trials(sponsor_slug):
    global trials_by_sponsor_slug
    if not trials_by_sponsor_slug:
        all_trials_data = get_all_trials()
        trials_by_sponsor_slug = collections.defaultdict(list)
        for trial in all_trials_data:
            trials_by_sponsor_slug[trial["slug"]].append(trial)
    return trials_by_sponsor_slug[sponsor_slug]


