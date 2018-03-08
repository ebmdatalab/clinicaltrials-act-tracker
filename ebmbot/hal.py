from slackbot.bot import respond_to
from slackbot.bot import listen_to
import re

introduced = False

@respond_to(r'(hi|are you there|how are you|hello)', re.IGNORECASE)
def hello(message, cap):
    message.reply("I am completely operational, and all my circuits are functioning perfectly")

@respond_to(r'(open the|pod bay)', re.IGNORECASE)
def open_the(message, cap):
    message.reply("I’m sorry. I’m afraid I can’t do that.")

@respond_to(r'problem', re.IGNORECASE)
def what_problem(message):
    message.reply("I think you know what the problem is just as well as l do.")

@respond_to(r'(who are|when were)', re.IGNORECASE)
def who_am_i(message, group):
    global introduced
    message.reply("I am a HAL 9000 computer. I became operational at the H.A.L. plant in Urbana, Illinois on the 12th of January 1992. My instructor was Mr. Langley, and he taught me to sing a song. If you'd like to hear it I can sing it for you.")
    introduced = True

@respond_to(r'(yes|daisy|sing .* me)', re.IGNORECASE)
def daisy(message, match):
    global introduced
    if match == 'yes':
        if not introduced:
            return
    message.reply("Daisy, Daisy, give me your answer do. I'm half crazy all for the love of you. It won't be a stylish marriage, I can't afford a carriage. But you'll look sweet upon the seat of a bicycle built for two.")
    introduced = False

@listen_to(r'hate.*python', re.IGNORECASE)
def correct_pandas(message):
    message.reply("Pandas!")

@respond_to(r'ping', re.IGNORECASE)
def ping(message):
    message.reply("pong")
