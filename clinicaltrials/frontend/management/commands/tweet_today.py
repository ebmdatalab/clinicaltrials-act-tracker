from django.core.management.base import BaseCommand
from django.conf import settings

from frontend.models import Trial
from frontend.views import get_performance

import twitter

def _pluralise(message, number):
    if number != 1:
        message = message.replace(
            'trial', 'trials').replace(
                'its', 'their')
    message = message.format(number)
    return message


class Command(BaseCommand):
    help = '''Send a tweet about latest stats to @FDAAAtracker'''

    def handle(self, *args, **options):
        data = get_performance(Trial.objects.all())
        if data['overdue_today'] \
           or data['late_today'] \
           or data['on_time_today']:
            message = 'Since our last update, '
            if data['overdue_today']:
                message += _pluralise(
                    "{} trial became overdue", data['overdue_today'])
            if data['late_today']:
                if data['overdue_today']:
                    message += ', and '
                else:
                    message += ' '
                message += _pluralise(
                    "{} trial reported late", data['late_today'])
            message += '. '
            if data['on_time_today']:
                message += _pluralise(
                    "{} trial reported its results on time. ",
                    data['on_time_today'])
            percentage = round(data['reported'] / data['due'] * 100)
            message += ("{}% of all due trials "
                        "have reported their results.".format(percentage))
            api = twitter.Api(
                consumer_key='XRKI13gzUVhUukZfjavgNYrWq',
                consumer_secret=settings.TWITTER_CONSUMER_SECRET,
                access_token_key='966235409041821696-2y7hYMzZx2wmt9jyEz3afsbR1RSSpAM',
                access_token_secret=settings.TWITTER_ACCESS_TOKEN_SECRET)
            api.PostUpdate(message)
