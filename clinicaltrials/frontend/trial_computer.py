from datetime import date
from dateutil.relativedelta import relativedelta

from django.apps import apps
from django.utils.dateparse import parse_date


GRACE_PERIOD = 30


def _datify(trial):
    """We sometimes maninpulate data before the model has been saved, and
    therefore before any date strings have been converted to date
    objects.

    """
    for field in ['reported_date',
                  'completion_date']:
        _field = getattr(trial, field)
        if isinstance(_field, str):
            val = parse_date(_field)
            setattr(trial, field, val)


class TrialComputer(object):
    def __init__(self, trial):
        self.trial = trial
        self.trial_class = apps.get_model('frontend', 'Trial')

    def compute_metadata(self):
        self.trial.days_late = self.get_days_late()
        self.trial.finable_days_late = None
        if self.trial.days_late:
            self.trial.finable_days_late = max([
                self.trial.days_late - self.trial_class.FINES_GRACE_PERIOD,
                0])
            if self.trial.finable_days_late == 0:
                self.trial.finable_days_late = None
        self.trial.status = self.get_status()
        self.trial.save()

    def qa_start_date(self):
        first_event = self.trial.trialqa_set.first()
        if first_event:
            qa_start_date = first_event.submitted_to_regulator
        else:
            qa_start_date = None
        return qa_start_date

    def get_days_late(self):
        # See https://github.com/ebmdatalab/clinicaltrials-act-tracker/issues/38
        overdue_delta = relativedelta(days=365)
        days_late = None
        if self.trial.results_due:
            _datify(self.trial)
            if self.trial.has_results:
                assert self.trial.reported_date, \
                    "{} has_results but no reported date".format(self)
                days_late = max([
                    (self.trial.reported_date
                     - self.trial.completion_date
                     - overdue_delta).days,
                    0])
            else:
                # still not reported.
                qa_start_date = self.qa_start_date()
                if qa_start_date:
                    days_late = max([(qa_start_date - self.trial.completion_date - overdue_delta).days, 0])
                else:
                    days_late = max([
                        (date.today()
                         - self.trial.completion_date
                         - overdue_delta).days,
                        0])
                    if (days_late - GRACE_PERIOD) <= 0:
                        days_late = 0
            if days_late == 0:
                days_late = None

        return days_late

    def get_status(self):
        # days_late() must have been called first
        overdue = self.trial.days_late and self.trial.days_late > 0
        if self.trial.results_due:
            if self.trial.has_results:
                if overdue:
                    status = self.trial_class.STATUS_REPORTED_LATE
                else:
                    status = self.trial_class.STATUS_REPORTED
            else:
                if self.qa_start_date():
                    if self.trial.days_late:
                        status = self.trial_class.STATUS_REPORTED_LATE
                    else:
                        status = self.trial_class.STATUS_REPORTED
                else:
                    if self.trial.days_late:
                        status = self.trial_class.STATUS_OVERDUE
                    else:
                        # We're in the grace period
                        status = self.trial_class.STATUS_ONGOING
        else:
            if self.trial.has_results:
                # Reported early! Might want to track separately in
                # the future
                status = self.trial_class.STATUS_REPORTED
            else:
                status = self.trial_class.STATUS_ONGOING
        return status
