from django.db import models

import json
import collections

headings_data = None
sponsor_by_slug = None
unreported_trials = None
reported_trials = None

def get_scores():
    global headings_data
    if not headings_data:
        headings_data = json.load(open('../scores.json'))
    return headings_data


def get_sponsor(slug):
    global sponsor_by_slug
    if not sponsor_by_slug:
        sponsor_by_slug = json.load(open('../sponsors.json'))
    return sponsor_by_slug[slug]


def get_trials_for_sponsor(slug, _type):
    global reported_trials
    global unreported_trials
    if not reported_trials:
        reported_trials = json.load(open('../reported_trials.json'))
    if not unreported_trials:
        unreported_trials = json.load(open('../reported_trials.json'))
    if _type == 'reported':
        return reported_trials[slug]
    elif _type == 'unreported':
        return unreported_trials[slug]
