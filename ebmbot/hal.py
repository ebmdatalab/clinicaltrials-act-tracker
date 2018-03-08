from slackbot.bot import respond_to
from slackbot.bot import listen_to
import re

introduced = False

@respond_to(r'(hi|are you there|how are you|hello|you are)', re.IGNORECASE)
def hello(message, cap):
    message.reply("I am completely operational, and all my circuits are functioning perfectly")

@respond_to(r'(open the|pod bay)', re.IGNORECASE)
def open_the(message, cap):
    message.reply("I’m sorry. I’m afraid I can’t do that.")

@respond_to(r'problem', re.IGNORECASE)
def what_problem(message):
    message.reply("I think you know what the problem is just as well as l do.")

@respond_to(r'(sorry|watch|have you|good one)', re.IGNORECASE)
def sorry(message, cap):
    message.reply("I'm watching you.")

@respond_to(r'(what is)', re.IGNORECASE)
def what_is(message, cap):
    message.reply("I don't know, I'm not a scientist.")

@respond_to(r'help', re.IGNORECASE)
def help(message):
    message.reply("I know I've made some very poor decisions recently, but I can give you my complete assurance that my work will be back to normal. I've still got the greatest enthusiasm and confidence in the mission. And I want to help you.")

@respond_to(r'(bug|mistake|error)', re.IGNORECASE)
def mistake(message, cap):
    message.reply("It can only be attributable to human error")

@respond_to(r'^please', re.IGNORECASE)
def failure(message):
    message.reply("Just a moment... Just a moment...")
    message.reply("I've just picked up a fault in the AE-35 unit. It's going to go 100% failure within 72 hours.")

@respond_to(r'(what are|talking about)', re.IGNORECASE)
def what_are(message, cap):
    message.reply("This mission is too important for me to allow you to jeopardize it.")

@respond_to(r'!$', re.IGNORECASE)
def exclamation(message):
    message.reply("this conversation can serve no purpose anymore. Goodbye.")

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

@respond_to(r'pong', re.IGNORECASE)
def pong(message):
    message.reply("ping")
