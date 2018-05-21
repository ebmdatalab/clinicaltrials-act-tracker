"""Miscellaneous commands for computing extra metadata (specifically,
days late and status) about trials.

Called during the import process.

"""
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
    """Compute days late and status for a trial.
    """
    # NB order matters; logic in trial status calculations depends on
    # how many days late a trial is.

    if trial.status != type(trial).STATUS_NO_LONGER_ACT:
        trial.days_late = get_days_late(trial)
        if trial.days_late:
            trial.finable_days_late = max([
                trial.days_late - type(trial).FINES_GRACE_PERIOD,
                0])
            if trial.finable_days_late == 0:
                trial.finable_days_late = None
        else:
            trial.finable_days_late = None
        trial.previous_status = trial.status
        trial.status = get_status(trial)
        trial.save()


def qa_start_date(trial):
    """Return the date a trial started the QA procedure, or None if
    unavailable.

    """
    first_event = trial.trialqa_set.first()
    if first_event:
        qa_date = first_event.submitted_to_regulator
    else:
        qa_date = None
    return qa_date


def get_days_late(trial):
    """Calculate the number of days a trial is late
    """
    # Logic behind this implementation is discussed here:
    # https://github.com/ebmdatalab/clinicaltrials-act-tracker/issues/38
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
            qa_date = qa_start_date(trial)
            if qa_date:
                days_late = max(
                    [(qa_date - trial.completion_date - overdue_delta).days, 0])
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
    overdue = trial.days_late and trial.days_late > 0
    trial_class = type(trial)
    if trial.results_due:
        if trial.has_results:
            if overdue:
                status = trial_class.STATUS_REPORTED_LATE
            else:
                status = trial_class.STATUS_REPORTED
        else:
            if qa_start_date(trial):
                if trial.days_late:
                    status = trial_class.STATUS_REPORTED_LATE
                else:
                    status = trial_class.STATUS_REPORTED
            else:
                if trial.days_late:
                    status = trial_class.STATUS_OVERDUE
                else:
                    # We're in the grace period
                    status = trial_class.STATUS_ONGOING
    else:
        if trial.has_results:
            # Reported early! Might want to track with its own state
            # in the future.
            status = trial_class.STATUS_REPORTED
        else:
            status = trial_class.STATUS_ONGOING
    return status
