from datetime import date
from datetime import timedelta

from frontend.models import Sponsor
from frontend.models import Trial
from frontend.management.commands.process_data import set_current_rankings


def makeTrial(sponsor, **kw):
    trial_counter = Trial.objects.count() + 1
    defaults = {
        'sponsor': sponsor,
        'start_date': date(2015, 1, 1),
        'completion_date': date(2016, 1, 1),
        'registry_id': 'id_{}'.format(trial_counter),
        'publication_url': 'http://bar.com/{}'.format(trial_counter),
        'title': 'Trial {}'.format(trial_counter)
    }
    defaults.update(kw)
    trial = Trial.objects.filter(registry_id=defaults['registry_id'])
    if trial.count():
        trial.update(**defaults)
        trial = trial.first()
    else:
        trial = Trial.objects.create(**defaults)
    if trial.status != Trial.STATUS_NO_LONGER_ACT:
        trial.compute_metadata()
    trial.refresh_from_db()
    return trial


def simulateImport(test_trials):
    """Do the same as the import script, but for an array of tuples
    """
    for update_date, trial in test_trials.items():
        Sponsor.objects.all().update(
            updated_date = update_date)
        for sponsor, due, reported in trial:
            makeTrial(
                sponsor,
                results_due=due,
                has_results=reported,
                reported_date=update_date
            )
        set_current_rankings()
        Trial.objects.all().delete()  # this is what the import process does
