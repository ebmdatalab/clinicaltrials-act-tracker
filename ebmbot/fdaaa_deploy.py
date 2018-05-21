from slackbot.bot import respond_to
from slackbot.bot import listen_to
import re
from fabric.tasks import execute

from fabfile import update
from fabfile import send_tweet


@respond_to('deploy fdaaa', re.IGNORECASE)
def deploy_fdaaa(message):
    message.reply("Copying staging data to live site...")
    execute(update, environment='live')
    message.reply("Done.")


@respond_to('update fdaaa staging', re.IGNORECASE)
def update_fdaaa_staging(message):
    message.reply("Updating staging site with data. Takes approx 2 hours.")
    execute(update, environment='staging')


@respond_to('tweet fdaaa', re.IGNORECASE)
def send_tweet(message):
    execute(send_tweet, environment='live')
    message.reply("Tweet sent: https://twitter.com/FDAAAtracker")
