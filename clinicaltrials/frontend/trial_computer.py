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
    # Logic in trial status calculations depends on how many days late
    # a trial is, so this must be called before `get_status`
    min_days_late, max_days_late = get_days_late(trial)
    trial.days_late = max_days_late
    if trial.days_late:
        trial.finable_days_late = max([
            (min_days_late or 0) - type(trial).FINES_GRACE_PERIOD,
            0])
        if trial.finable_days_late == 0:
            trial.finable_days_late = None
    else:
        trial.finable_days_late = None
    trial.previous_status = trial.status
    trial.status = get_status(trial)


def qa_start_dates(trial):
    """The dates a trial started the QA procedure, or None if
    unavailable.

    Args:
        trial: the trial we're interested in

    Returns:
        (original_start_date, cancelled, restart_date) triple

    """
    # We assume that the first QA submission date will, when QA is
    # complete, be treated as the date the results were first
    # submitted

    # However, if a submission is cancelled, then we use the first
    # submission date following that.  This may or may not be what
    # cc.gov do, so we don't treat these as overdue for the purposes
    # of estimating fines. See #146 for background.
    restart_date = None
    original_start_date = None
    cancelled = False
    first_event = trial.trialqa_set.first()

    if first_event:
        original_start_date = first_event.submitted_to_regulator

    for event in trial.trialqa_set.order_by('-submitted_to_regulator').all():
        if event.cancelled_by_sponsor:
            cancelled = True
            break
        else:
            restart_date = event.submitted_to_regulator

    return original_start_date, cancelled, restart_date


def _days_delta(effective_reporting_date, completion_date, with_grace_period=False):
    overdue_delta = relativedelta(days=365)
    days_late = max([
        (effective_reporting_date - completion_date - overdue_delta).days,
        0])
    if with_grace_period and (days_late - GRACE_PERIOD) <= 0:
        days_late = 0
    if days_late == 0:
        days_late = None
    return days_late


def get_days_late(trial):
    """Return the (min, max) number of days a trial is late.

    `min` takes into account the earliest submission of results for
    QA, i.e. is is the most generous possible interpretation of lateness

    `max` disallows early submissions if they are followed by
    cancellation, i.e. it is the least generous interpretation which
    still takes into account submission to the QA process.

    """
    # Logic behind this implementation is discussed in #38 (and #146)
    min_days_late = max_days_late = None
    if trial.results_due:
        _datify(trial)
        if trial.has_results:
            assert trial.reported_date, \
                "{} has_results but no reported date".format(trial)
            min_days_late = max_days_late = _days_delta(
                trial.reported_date, trial.completion_date)
        else:
            original_start_date, cancelled, restart_date = qa_start_dates(trial)
            if original_start_date:
                min_days_late = max_days_late = _days_delta(
                    original_start_date, trial.completion_date)
            if restart_date:
                max_days_late = _days_delta(restart_date, trial.completion_date)
            else:
                if cancelled:
                    max_days_late = _days_delta(
                        date.today(),
                        trial.completion_date,
                        with_grace_period=True)
            no_qa = not original_start_date
            if no_qa:
                min_days_late = max_days_late = _days_delta(
                    date.today(),
                    trial.completion_date,
                    with_grace_period=True)
    return min_days_late, max_days_late


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
            # results are due, but none have been published
            original_start_date, cancelled, restart_date = qa_start_dates(trial)
            if original_start_date:
                # although no results have been published, they have
                # been submitted
                if trial.days_late:
                    if cancelled and not restart_date:
                        # The submission has been cancelled, so it's still overdue
                        status = trial_class.STATUS_OVERDUE_CANCELLED
                    else:
                        # We count uncancelled submissions as reported
                        status = trial_class.STATUS_REPORTED_LATE
                else:
                    status = trial_class.STATUS_REPORTED
            else:
                # Results have been neither published nor submitted
                if trial.days_late:
                    status = trial_class.STATUS_OVERDUE
                else:
                    # We're in the grace period, so temporarily let them off
                    status = trial_class.STATUS_ONGOING
    else:
        if trial.has_results:
            # Reported early! Might want to track with its own state
            # in the future.
            status = trial_class.STATUS_REPORTED
        else:
            status = trial_class.STATUS_ONGOING
    return status
