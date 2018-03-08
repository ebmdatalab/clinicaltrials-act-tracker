"""The bot modules are listed in slackbot_settings.py

For bot commands that execute fabric commands which assume sudo, this
script should be run by a user in the `fabric` group

"""
from slackbot.bot import Bot
from slackbot.bot import respond_to
from slackbot.bot import listen_to
import re


def main():
    bot = Bot()
    bot.run()

if __name__ == "__main__":
    main()
