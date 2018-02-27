from datetime import date
from datetime import timedelta

from frontend.models import Trial
from frontend.management.commands.process_data import set_current


def makeTrial(sponsor, **kw):
    trial_counter = Trial.objects.count() + 1
    tomorrow = date.today() + timedelta(days=1)
    defaults = {
        'sponsor': sponsor,
        'start_date': date(2015, 1, 1),
        'completion_date': date(2016, 1, 1),
        'registry_id': 'id_{}'.format(trial_counter),
        'publication_url': 'http://bar.com/{}'.format(trial_counter),
        'title': 'Trial {}'.format(trial_counter)
    }
    defaults.update(kw)
    trial = Trial.objects.create(**defaults)
    trial.compute_metadata()
    return trial


def simulateImport(test_trials):
    """Do the same as the import script, but for an array of tuples
    """
    last_date = None
    for updated_date, sponsor, due, reported in test_trials:
        if updated_date != last_date:
            # simulate a new import; this means deleting all
            # existing Trials and updating rankings (see below)
            set_current()
            Trial.objects.all().delete()
        sponsor.updated_date = updated_date
        sponsor.save()
        makeTrial(
            sponsor,
            results_due=due,
            has_results=reported,
            reported_date=updated_date
        )
        last_date = updated_date
    set_current()
