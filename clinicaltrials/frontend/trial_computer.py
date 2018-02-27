from datetime import date
from dateutil.relativedelta import relativedelta

from django.apps import apps
from django.utils.dateparse import parse_date


GRACE_PERIOD = 30


def _datify(trial):
    """We sometimes maninpulate data before the model has been saved, and
    therefore before any date strings have been converted to date
    objects by Django.

    So: do exactly what Django does, but sooner.

    """
    for field in ['reported_date',
                  'completion_date']:
        _field = getattr(trial, field)
        if isinstance(_field, str):
            val = parse_date(_field)
            setattr(trial, field, val)


def compute_metadata(trial):
    trial.days_late = get_days_late(trial)
    if trial.days_late:
        trial.finable_days_late = max([
            trial.days_late - type(trial).FINES_GRACE_PERIOD,
            0])
        if trial.finable_days_late == 0:
            trial.finable_days_late = None
    else:
        trial.finable_days_late = None

    trial.status = get_status(trial)
    trial.save()

def qa_start_date(trial):
    first_event = trial.trialqa_set.first()
    if first_event:
        date = first_event.submitted_to_regulator
    else:
        date = None
    return date

def get_days_late(trial):
    # See https://github.com/ebmdatalab/clinicaltrials-act-tracker/issues/38
    overdue_delta = relativedelta(days=365)
    days_late = None
    if trial.results_due:
        _datify(trial)
        if trial.has_results:
            assert trial.reported_date, \
                "{} has_results but no reported date".format(trial)
            days_late = max([
                (trial.reported_date
                 - trial.completion_date
                 - overdue_delta).days,
                0])
        else:
            # still not reported.
            qa_date = qa_start_date(trial)
            if qa_date:
                days_late = max([(qa_date - trial.completion_date - overdue_delta).days, 0])
            else:
                days_late = max([
                    (date.today()
                     - trial.completion_date
                     - overdue_delta).days,
                    0])
                if (days_late - GRACE_PERIOD) <= 0:
                    days_late = 0
        if days_late == 0:
            days_late = None

    return days_late

def get_status(trial):
    # days_late() must have been called first
    overdue = trial.days_late and trial.days_late > 0
    Trial = type(trial)
    if trial.results_due:
        if trial.has_results:
            if overdue:
                status = Trial.STATUS_REPORTED_LATE
            else:
                status = Trial.STATUS_REPORTED
        else:
            if qa_start_date(trial):
                if trial.days_late:
                    status = Trial.STATUS_REPORTED_LATE
                else:
                    status = Trial.STATUS_REPORTED
            else:
                if trial.days_late:
                    status = Trial.STATUS_OVERDUE
                else:
                    # We're in the grace period
                    status = Trial.STATUS_ONGOING
    else:
        if trial.has_results:
            # Reported early! Might want to track separately in
            # the future
            status = Trial.STATUS_REPORTED
        else:
            status = Trial.STATUS_ONGOING
    return status
