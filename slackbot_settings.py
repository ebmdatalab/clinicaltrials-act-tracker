import os
# "Bot User OAuth Access Token" from https://api.slack.com/apps/A6B85C8KC/oauth
API_TOKEN = os.environ['SLACK_BOT_ACCESS_TOKEN']
DEFAULT_REPLY = "I'm sorry, but I didn't understand you"
ERRORS_TO = 'tech'

PLUGINS = [
    'ebmbot.fdaaa_deploy',
    'ebmbot.hal',
]


import logging
logging.basicConfig(handlers=[logging.StreamHandler()],level=logging.WARN)
